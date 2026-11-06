#!/usr/bin/env python3
"""
风电塔灾损测算软件 — Gradio 前端

功能：
  - 单图/批量图片上传 → 模型推理 → 结构化报告展示
  - 高风险自动告警（浅底色条横幅，文字+颜色双通道）
  - 结论摘要卡 + 折叠式分组报告 + 完整 JSON 折叠查看
  - 报告导出（Markdown / JSON）
  - 检测历史记录（SQLite 存储，下拉选择回看，删除需确认）
  - 统计面板
  - 中 / 英双语界面（--lang en 或 UI_LANG=en 切换英文）

启动: python app.py            （中文界面）
      python app.py --lang en  （英文界面）
访问: http://localhost:7860
"""

import os
import sys
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import MODEL_PATH, IMAGE_DIR
import i18n
if "--lang" in sys.argv or os.environ.get("UI_LANG"):
    i18n.set_lang(i18n.detect_lang())  # 需在导入展示模块前确定语言
# 未显式指定语言时保持 i18n 已有设置（便于外部 import app 前预设语言）

import gradio as gr
from inference import WindDamageModel
from parser import parse_json_pred, validate_report, get_field
from formatter import format_report, format_summary, get_risk_badge, is_high_risk
from history import (init_db, save_record, query_records, get_record, clear_all,
                     clear_user_records, get_stats, can_access, update_note,
                     delete_record)
from auth import user_for_request
from exporter import save_export
from charts import charts_html
from i18n import t as tr, tr_value
import ui_components as uc

# ─── 全局模型实例 ─────────────────────────────────────────
_model = None

# ─── 空状态图标 ───────────────────────────────────────────
_UPLOAD_ICON_SVG = (
    "<svg width='52' height='52' viewBox='0 0 24 24' fill='none' stroke='#9AA5B1' "
    "stroke-width='1.4' stroke-linecap='round' stroke-linejoin='round'>"
    "<path d='M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'/>"
    "<polyline points='17 8 12 3 7 8'/>"
    "<line x1='12' y1='3' x2='12' y2='15'/>"
    "</svg>"
)


def _empty_result_html():
    """结果区空状态：图标 + 标题 + 格式说明。"""
    return uc.empty_state(tr("empty_upload"), tr("empty_format"), _UPLOAD_ICON_SVG)


EMPTY_RESULT_HTML = _empty_result_html()


def get_model():
    global _model
    if _model is None:
        _model = WindDamageModel()
        _model.load()
    return _model


# ══════════════════════════════════════════════════════════
#  核心推理函数
# ══════════════════════════════════════════════════════════

def get_image_info(image_path):
    """提取图片元信息（尺寸、大小、格式）。"""
    try:
        from PIL import Image
        with Image.open(image_path) as im:
            w, h = im.size
            fmt = im.format or ""
        size_kb = os.path.getsize(image_path) / 1024
        return f"{w} × {h} px | {fmt} | {size_kb:.0f} KB"
    except Exception:
        return ""


def _do_inference(image_path):
    """对单张图片执行推理，返回 (parsed, raw, infer_time) 或 raise。"""
    model = get_model()
    parsed, raw, infer_time = model.infer(image_path)
    return parsed, raw, infer_time


def _summary_card_html(parsed, meta=None):
    """结果页第一层：结论摘要卡（风险等级/损伤类型/优先级 + 元信息）。"""
    meta = meta or {}
    priority_raw = get_field(parsed, i18n.SECTION_CONCLUSION, "巡检优先级") or "—"
    damage_raw = get_field(parsed, i18n.SECTION_DAMAGE, "损伤类型") or "—"
    has_damage_raw = get_field(parsed, i18n.SECTION_DAMAGE, "是否存在损伤")
    high = is_high_risk(parsed)
    if high:
        tone = "danger"
        risk_disp = f'<span class="wd-badge wd-badge-danger">{esc_risk(priority_raw)}</span>'
    else:
        tone = "success" if (has_damage_raw or "").strip() != "是" else "warn"
        risk_disp = esc_risk(tr_value(priority_raw))

    items = [
        (tr("card_risk"), risk_disp),
        (tr("card_damage"), uc.risk_badge(tr_value(damage_raw))),
        (tr("card_priority"), esc_risk(tr_value(priority_raw))),
    ]
    if meta.get("timestamp"):
        items.append((tr("card_time"), uc.esc(meta["timestamp"])))
    if meta.get("infer_time") is not None:
        items.append((tr("card_cost"), f"{meta['infer_time']:.1f}s"))
    if meta.get("record_id"):
        items.append((tr("card_no"), f"#{meta['record_id']}"))
    return uc.summary_card(items, tone=tone)


def esc_risk(text) -> str:
    """风险值着色徽章（无法映射时原样转义）。"""
    from ui_components import tone_for_value
    text = str(text or "—")
    return uc.risk_badge(text, tone_for_value(text))


def _build_result_html(parsed, meta=None):
    """将解析后的 JSON 构建为四层结构的 HTML 展示。

    第一层：结论摘要卡；高风险横幅（浅底色条）；
    第二~三层：折叠式分组报告板块（损伤判定与结论默认展开）；
    （JSON 技术信息由外层 Accordion 承载。）
    """
    formatted = format_report(parsed)
    html_parts = []

    # 第一层：结论摘要卡
    html_parts.append(_summary_card_html(parsed, meta))

    # 高风险横幅：浅底 + 左色条 + 图标 + 明确文字
    if formatted["high_risk"]:
        html_parts.append(uc.risk_banner(tr("msg_high_risk_banner")))

    # 折叠板块：损伤判定、风险判断、结论建议默认展开
    open_keys = {i18n.SECTION_DAMAGE, i18n.SECTION_RISK, i18n.SECTION_CONCLUSION}
    for sec in formatted["sections"]:
        fields = []
        for f in sec["fields"]:
            value_html = f["value"]
            if f["is_risk"] and f["value"] in get_risk_badge_values():
                value_html = get_risk_badge(f["value"], f["raw_field"])
            fields.append((f["label"], value_html, f["is_risk"]))
        body = uc.kv_rows(fields)
        open_ = sec["title"] in open_keys or any(
            k in str(sec["title"]) for k in ("损伤", "Damage", "风险", "Risk", "结论", "Conclusion")
        )
        html_parts.append(uc.sec_details(sec["icon"], sec["title"], body, open_))

    return "".join(html_parts), formatted


def get_risk_badge_values():
    """当前语言下需要渲染成彩色 badge 的取值集合。"""
    if i18n.LANG == "en":
        return ("Yes", "No", "None", "High", "Medium", "Low")
    return ("是", "高", "中", "否", "低", "无")


# ══════════════════════════════════════════════════════════
#  Tab 1: 单图检测
# ══════════════════════════════════════════════════════════

def analyze_single(image, request: gr.Request = None):
    """单图分析，返回 (summary, detail_html, json_out, status, img_info, md_path, json_path)。"""
    if image is None:
        return tr("msg_please_upload"), _empty_result_html(), "", tr("msg_upload_first"), "", None, None

    image_path = image if isinstance(image, str) else getattr(image, 'name', str(image))

    if not os.path.exists(image_path):
        return (
            tr("msg_file_not_exist"),
            uc.status_banner(f'{uc.esc(tr("msg_file_not_exist"))}: {uc.esc(image_path)}', "error"),
            "", tr("msg_file_not_exist"), "", None, None,
        )

    img_info = get_image_info(image_path)

    try:
        t0 = time.time()
        parsed, raw, infer_time = _do_inference(image_path)
        total_time = time.time() - t0

        if parsed is None:
            return (
                tr("msg_parse_fail"),
                uc.status_banner(tr("msg_infer_parse_fail", t=infer_time), "error")
                + f"<pre style='overflow-x:auto;background:#F0F3F7;padding:12px;border-radius:8px;font-size:12px;'>{uc.esc(raw[:2000])}</pre>",
                raw, tr("msg_infer_parse_fail", t=infer_time), img_info, None, None,
            )

        # 保存历史记录（先拿到记录 ID，用于摘要卡报告编号；归属当前登录用户）
        owner_id, created_by = _scope_owner(request)
        record_id = save_record(os.path.basename(image_path), parsed, infer_time,
                                image_path, source="ui", persist_image=True,
                                owner_user_id=owner_id, created_by=created_by)

        detail_html, formatted = _build_result_html(parsed, meta={
            "record_id": record_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "infer_time": infer_time,
        })
        summary = format_summary(parsed)
        json_str = formatted["json_str"]
        val = formatted["validation"]
        image_name = os.path.basename(image_path)
        comp = "✅" if val["valid"] else f"⚠️ {val['message']}"
        status = (f'✅ {tr("msg_infer_done", t=infer_time)} | '
                  f'{tr("msg_json_ok")} | '
                  f'{tr("msg_completeness")}: {comp}')

        # 导出文件
        md_path = save_export(parsed, image_name, infer_time, fmt="md")
        json_path = save_export(parsed, image_name, infer_time, fmt="json")

        return summary, detail_html, json_str, status, img_info, md_path, json_path

    except Exception as e:
        import traceback
        traceback.print_exc()
        return (
            tr("msg_infer_fail"),
            uc.status_banner(f'{uc.esc(tr("msg_error", e=e))}', "error")
            + f"<pre style='overflow-x:auto;background:#F0F3F7;padding:12px;border-radius:8px;font-size:12px;'>{uc.esc(traceback.format_exc()[:1500])}</pre>",
            "", tr("msg_error", e=e), img_info, None, None,
        )


# ══════════════════════════════════════════════════════════
#  Tab 2: 批量检测（生成器：边分析边刷新进度）
# ══════════════════════════════════════════════════════════

def analyze_batch(files, request: gr.Request = None):
    """批量分析多张图片。生成器逐张产出 (summary, table_html, status)，实时刷新进度。"""
    if not files:
        yield "", _empty_result_html(), tr("msg_upload_first")
        return

    owner_id, created_by = _scope_owner(request)

    results = []
    high_flags = []  # 与 results 行一一对应，用于整行风险着色
    status_parts = []
    total = len(files)
    ok_count = 0
    fail_count = 0

    header = [tr("hdr_image"), tr("hdr_risk"), tr("hdr_damage"), tr("hdr_damage_type"),
              tr("hdr_component"), tr("hdr_priority"), tr("hdr_time_cost")]

    def render_table():
        """已完成的行 → 样式化表格。"""
        rows = []
        for idx, row in enumerate(results):
            row_cls = ' class="wd-row-danger"' if high_flags[idx] else ""
            tds = "".join(
                f'<td class="wd-num">{c}</td>' if j == 6 else f'<td>{c}</td>'
                for j, c in enumerate(row)
            )
            rows.append(f"<tr{row_cls}>{tds}</tr>")
        return uc.data_table(header, "".join(rows))

    yield "", uc.status_banner(tr("msg_progress", i=0, total=total, name="…"), "info"), ""

    for i, f in enumerate(files):
        image_path = f if isinstance(f, str) else f.name
        image_name = os.path.basename(image_path)

        yield "", uc.status_banner(tr("msg_progress", i=i + 1, total=total, name=uc.esc(image_name)), "info"), \
              uc.esc("\n".join(status_parts))

        try:
            parsed, raw, infer_time = _do_inference(image_path)

            if parsed is None:
                fail_count += 1
                results.append([uc.esc(image_name), "❌", "—", "—", "—", "—", f"{infer_time:.1f}s"])
                high_flags.append(False)
                status_parts.append(f'[{i+1}/{total}] {image_name}: ❌ {tr("msg_parse_fail")}')
                yield tr("batch_partial", ok=ok_count, total=total, failed=fail_count), render_table(), \
                      uc.esc("\n".join(status_parts))
                continue

            ok_count += 1
            has_damage = tr_value(get_field(parsed, i18n.SECTION_DAMAGE, "是否存在损伤"))
            damage_type = tr_value(get_field(parsed, i18n.SECTION_DAMAGE, "损伤类型"))
            component = tr_value(get_field(parsed, i18n.SECTION_COMPONENT, "构件名称"))
            priority = tr_value(get_field(parsed, i18n.SECTION_CONCLUSION, "巡检优先级"))

            high = is_high_risk(parsed)
            risk_cell = f'<span class="wd-badge wd-badge-{"danger" if high else "success"}">' \
                        f'{tr("badge_high_risk") if high else tr("badge_normal")}</span>'
            results.append([
                uc.esc(image_name), risk_cell,
                uc.risk_badge(has_damage) if has_damage else "—",
                uc.esc(damage_type) if damage_type else "—",
                uc.esc(component) if component else "—",
                uc.risk_badge(priority) if priority else "—",
                f"{infer_time:.1f}s",
            ])
            high_flags.append(high)

            # 保存历史（归属当前登录用户）
            save_record(image_name, parsed, infer_time, image_path,
                        source="batch", persist_image=True,
                        owner_user_id=owner_id, created_by=created_by)

            status_parts.append(f"[{i+1}/{total}] {image_name}: ✅ {damage_type} | {priority}")

        except Exception as e:
            fail_count += 1
            results.append([uc.esc(image_name), "❌", "—", "—", "—", "—", uc.esc(str(e)[:50])])
            high_flags.append(False)
            status_parts.append(f"[{i+1}/{total}] {image_name}: ❌ {e}")

        yield tr("batch_partial", ok=ok_count, total=total, failed=fail_count) if fail_count \
              else tr("batch_done", ok=ok_count, total=total), \
              render_table(), uc.esc("\n".join(status_parts))

    final_summary = tr("batch_partial", ok=ok_count, total=total, failed=fail_count) if fail_count \
        else tr("batch_done", ok=ok_count, total=total)
    yield final_summary, render_table(), uc.esc("\n".join(status_parts))


# ══════════════════════════════════════════════════════════
#  Tab 3: 历史记录（筛选 / 排序 / 分页 / 分级删除 / 移动卡片）
# ══════════════════════════════════════════════════════════

def _current_scope(request=None):
    """当前会话的数据范围 (user_id, is_admin)。

    - request 带 gr.Request 注解时由 gradio 注入真实请求 → 从会话 Cookie 解析用户；
    - request=None（单元测试 / 直接函数调用）：保持 (None, True) 兼容旧离线行为，
      生产路由全部经过登录中间件，不会出现 None 请求。
    """
    if request is None:
        return None, True
    user = user_for_request(request)
    if not user:
        return None, False
    return user["id"], user.get("role") == "admin"


def _scope_owner(request=None):
    """(owner_user_id, username)：用于 save_record 归属。"""
    if request is None:
        return None, None
    user = user_for_request(request)
    if not user:
        return None, None
    return user["id"], user.get("username")


def _valid_date(s: str) -> bool:
    try:
        time.strptime(s.strip(), "%Y-%m-%d")
        return True
    except (ValueError, AttributeError):
        return False


def _risk_badge_cell(high_risk) -> str:
    cls = "danger" if high_risk else "success"
    txt = tr("badge_high_risk") if high_risk else tr("badge_normal")
    return f'<span class="wd-badge wd-badge-{cls}">{txt}</span>'


def _history_list_html(records, total, filtered):
    """历史列表：桌面表格 + 移动卡片双渲染（CSS 切换）。"""
    if not records:
        if filtered:
            empty = uc.empty_state(tr("empty_filtered"), tr("empty_filtered_desc"))
        else:
            empty = (uc.empty_state(tr("empty_no_data"), tr("empty_no_data_desc"),
                                    _UPLOAD_ICON_SVG))
        return empty

    header = [tr("hdr_id"), tr("hdr_timestamp"), tr("hdr_image"), tr("hdr_risk"),
              tr("hdr_damage"), tr("hdr_damage_type"), tr("hdr_component"),
              tr("hdr_priority"), tr("hdr_confidence"), tr("hdr_infer_time")]
    rows, cards = [], []
    for r in records:
        rid = r["id"]
        high = bool(r["high_risk"])
        row_cls = ' class="wd-row-danger"' if high else ""
        src_tag = (f' <span class="wd-badge wd-badge-muted">{tr("badge_migrated")}</span>'
                   if r.get("source") == "migration" else "")
        cells = [
            f'<td class="wd-num">{rid}</td>',
            f'<td class="wd-num">{uc.esc(r["timestamp"])}</td>',
            f"<td>{uc.esc(r['image_name'])}{src_tag}</td>",
            f"<td>{_risk_badge_cell(high)}</td>",
            f"<td>{uc.risk_badge(tr_value(r['has_damage'])) if r['has_damage'] else '—'}</td>",
            f"<td>{uc.esc(tr_value(r['damage_type'])) if r['damage_type'] else '—'}</td>",
            f"<td>{uc.esc(tr_value(r['component'])) if r['component'] else '—'}</td>",
            f"<td>{uc.risk_badge(tr_value(r['priority'])) if r['priority'] else '—'}</td>",
            f"<td>{uc.esc(tr_value(r['confidence'])) if r['confidence'] else '—'}</td>",
            f'<td class="wd-num">{r["infer_time"] or "—"}s</td>',
        ]
        rows.append(f"<tr{row_cls}>{''.join(cells)}</tr>")

        meta = (f'{tr("card_time")}: {uc.esc(r["timestamp"])} · '
                f'{tr("summary_priority")}: {uc.esc(tr_value(r["priority"]) or "—")} · '
                f'{r["infer_time"] or "—"}s')
        cards.append(uc.mobile_history_card(
            _risk_badge_cell(high), r["image_name"], meta,
            f"/history/{rid}", tr("btn_view_detail"), danger=high))

    return (
        f'<div class="wd-total-count" style="margin:0 0 10px;">'
        f'{tr("filter_total", n=total)}</div>'
        f'<div class="wd-desktop-only">{uc.data_table(header, "".join(rows))}</div>'
        f'<div class="wd-mobile-only">{"".join(cards)}</div>'
    )


def query_history(search, risk, date_from, date_to, sort, page_size, page,
                  request: gr.Request = None):
    """按筛选/排序/分页查询历史。返回 (stats_html, list_html, page_info, dd_update, status)。"""
    search = (search or "").strip()
    date_from = (date_from or "").strip()
    date_to = (date_to or "").strip()
    if (date_from and not _valid_date(date_from)) or (date_to and not _valid_date(date_to)):
        return "", tr("msg_invalid_date"), tr("page_info", page=1, pages=1, total=0), gr.update(), ""

    user_id, is_admin = _current_scope(request)
    if user_id is None and not is_admin:
        # 未登录：绝不返回全量数据（scope=None 会被当作 admin 视角）
        return "", uc.empty_state(tr("auth_need_login"), ""), \
               tr("page_info", page=1, pages=1, total=0), gr.update(), ""
    scope = None if is_admin else user_id
    try:
        page_size = int(page_size)
    except (TypeError, ValueError):
        page_size = 20
    page = max(1, int(page or 1))

    rows, total = query_records(
        limit=page_size, offset=(page - 1) * page_size, owner_user_id=scope,
        search=search, risk=risk or "", date_from=date_from, date_to=date_to,
        sort=sort or "time_desc")
    pages = max(1, -(-total // page_size))
    if page > pages:
        page = pages
        rows, total = query_records(
            limit=page_size, offset=(page - 1) * page_size, owner_user_id=scope,
            search=search, risk=risk or "", date_from=date_from, date_to=date_to,
            sort=sort or "time_desc")

    stats = get_stats(scope)
    stats_html = (
        '<div class="wd-stats">'
        + uc.stat_card(stats["total"], tr("stat_total"))
        + uc.stat_card(stats["high_risk"], tr("stat_high_risk"), tone="danger")
        + uc.stat_card(stats["damaged"], tr("stat_damaged"), tone="warn")
        + uc.stat_card(stats["normal"], tr("stat_normal"), tone="success")
        + "</div>"
    )
    filtered = bool(search or risk or date_from or date_to)
    list_html = _history_list_html(rows, total, filtered)
    page_info = tr("page_info", page=page, pages=pages, total=total)

    choices = []
    for r in rows:
        prio = tr_value(r["priority"]) if r["priority"] else "—"
        label = f'#{r["id"]} | {r["image_name"]} | {tr("badge_high_risk") if r["high_risk"] else tr("badge_normal")} | {prio}'
        choices.append((label, str(r["id"])))
    dd_update = gr.update(choices=choices, value=None)

    return stats_html, list_html, page_info, dd_update, ""


def _quick_range(days):
    """快捷日期范围 → (from, to)。"""
    today = time.strftime("%Y-%m-%d")
    if days <= 0:
        return today, today
    d = time.strftime("%Y-%m-%d", time.localtime(time.time() - days * 86400))
    return d, today


def refresh_history():
    """刷新（保持与旧接口兼容的包装）：全量第一页。"""
    stats_html, list_html, page_info, dd, _ = query_history("", "", "", "", "time_desc", 20, 1)
    chart_html = charts_html()
    return stats_html, list_html, page_info, dd, chart_html


def view_history_detail(record_id_str, request: gr.Request = None):
    """查看单条历史记录详情（含独立页链接、备注回填）。"""
    empty_json = ""
    if not record_id_str or not str(record_id_str).strip().isdigit():
        return uc.status_banner(tr("msg_invalid_id"), "warn"), empty_json, ""

    user_id, is_admin = _current_scope(request)
    record = get_record(int(str(record_id_str).strip()))
    if not record:
        return uc.status_banner(tr("msg_record_not_found", id=record_id_str), "error"), empty_json, ""
    if not can_access(record, user_id, is_admin):
        return uc.status_banner(tr("msg_record_no_access"), "error"), empty_json, ""

    report = json.loads(record["json_report"])
    detail_html, formatted = _build_result_html(report, meta={
        "record_id": record["id"],
        "timestamp": record["timestamp"],
        "infer_time": record["infer_time"] or 0,
    })
    link = (f'<div style="margin-bottom:10px;">'
            f'<a class="wd-backlink" href="/history/{record["id"]}" target="_blank">'
            f'{tr("open_full_page")}</a></div>')
    return link + detail_html, formatted["json_str"], record.get("note") or ""


def save_note(record_id_str, note, request: gr.Request = None):
    """保存所选记录的备注（校验归属权限）。"""
    if not record_id_str or not str(record_id_str).strip().isdigit():
        return tr("msg_invalid_id")
    user_id, is_admin = _current_scope(request)
    record = get_record(int(str(record_id_str).strip()))
    if not record or not can_access(record, user_id, is_admin):
        return tr("msg_record_no_access")
    update_note(record["id"], note or "")
    return tr("msg_note_saved")


def copy_json(json_str):
    """复制 JSON 到剪贴板（返回提示文字）。"""
    if json_str:
        return tr("msg_copied")
    return tr("msg_no_json")


def ask_delete_record(record_id_str, request: gr.Request = None):
    """单条删除第一步：显示确认条（分级确认：单条不需勾选，但需二次点击）。"""
    if not record_id_str or not str(record_id_str).strip().isdigit():
        return tr("msg_invalid_id"), gr.update(visible=False)
    rid = int(str(record_id_str).strip())
    rec = get_record(rid)
    user_id, is_admin = _current_scope(request)
    if not rec or not can_access(rec, user_id, is_admin):
        return tr("msg_record_no_access"), gr.update(visible=False)
    name = rec["image_name"]
    msg = f"⚠️ {tr('msg_delete_confirm_one', id=rid, name=uc.esc(name))}"
    return (f'<div class="wd-banner" style="margin-bottom:0;">'
            f'<span class="wd-banner-text">{msg}</span></div>'), gr.update(visible=True)


def do_delete_record(record_id_str, request: gr.Request = None):
    """单条删除第二步：确认后执行删除并刷新。"""
    if record_id_str and str(record_id_str).strip().isdigit():
        rid = int(str(record_id_str).strip())
        user_id, is_admin = _current_scope(request)
        rec = get_record(rid)
        if rec and can_access(rec, user_id, is_admin):
            delete_record(rid)
            status = tr("msg_deleted_one", id=rid)
        else:
            status = tr("msg_record_no_access")
    else:
        status = tr("msg_invalid_id")
    stats_html, list_html, page_info, dd, _ = query_history(
        "", "", "", "", "time_desc", 20, 1, request=request)
    return stats_html, list_html, page_info, dd, gr.update(visible=False), status


def do_clear_history(typed, request: gr.Request = None):
    """清空记录：需输入「确认清空」文字（分级删除最高档）。

    权限模型：admin 清空全库；普通用户只清空自己的记录。
    """
    typed = (typed or "").strip()
    user_id, is_admin = _current_scope(request)
    if user_id is None and not is_admin:
        return "", "", "", gr.update(), "", tr("auth_need_login")
    scope = None if is_admin else user_id
    total = get_stats(scope)["total"]
    if total == 0:
        stats_html, list_html, page_info, dd, _ = query_history(
            "", "", "", "", "time_desc", 20, 1, request=request)
        return stats_html, list_html, page_info, dd, "", tr("msg_confirm_first")
    if typed != tr("clear_typed_word"):
        return "", "", "", gr.update(), "", tr("msg_clear_typed_wrong")
    n = total
    if is_admin:
        clear_all()
    else:
        clear_user_records(user_id)
    stats_html, list_html, page_info, dd, _ = query_history(
        "", "", "", "", "time_desc", 20, 1, request=request)
    return stats_html, list_html, page_info, dd, "", tr("msg_deleted_n", n=n)


# ══════════════════════════════════════════════════════════
#  Gradio 界面
# ══════════════════════════════════════════════════════════

# 顶栏用户徽章：页面加载后从 /api/me 拉取当前会话用户（server.py 提供）
_BADGE_JS = """
() => {
  fetch('/api/me').then(r => r.ok ? r.json() : null).then(u => {
    const el = document.getElementById('wd-user-badge');
    if (!el || !u || !u.username) return;
    const role = u.role === 'admin' ? '__ROLE_ADMIN__' : '__ROLE_USER__';
    el.innerHTML =
      '<span class="wd-ub-name" title="' + u.username + '">' + u.username + '</span>'
      + '<span class="wd-badge wd-badge-muted">' + role + '</span>'
      + (u.role === 'admin' ? '<a href="/users">__USERS_LINK__</a>' : '')
      + '<a href="/change-password">__PW_LINK__</a>'
      + '<a href="/logout">__LOGOUT_LINK__</a>';
  }).catch(() => {});
}
"""


def build_ui():
    badge_js = (_BADGE_JS
                .replace("__ROLE_ADMIN__", tr("users_role_admin"))
                .replace("__ROLE_USER__", tr("users_role_user"))
                .replace("__USERS_LINK__", tr("users_link"))
                .replace("__PW_LINK__", tr("pw_link"))
                .replace("__LOGOUT_LINK__", tr("btn_logout")))
    with gr.Blocks(title=tr("app_title")) as app:
        # 顶栏用户徽章（内容由上面的 JS 注入）
        gr.HTML('<div id="wd-user-badge" class="wd-user-badge"></div>')
        # 标题（含 SVG 风电机组图标）
        gr.Markdown(
            "<div class='main-title'>"
            "<h1><span class='title-icon'>"
            "<svg width='38' height='38' viewBox='0 0 64 64' xmlns='http://www.w3.org/2000/svg'>"
            "<circle cx='32' cy='32' r='30' fill='#EBF5FB' stroke='#125191' stroke-width='1.5'/>"
            "<rect x='29.5' y='36' width='5' height='22' fill='#7F8C8D'/>"
            "<rect x='23' y='30' width='18' height='8' rx='2' fill='#5DADE2'/>"
            "<circle cx='32' cy='28' r='3.5' fill='#34495E'/>"
            "<g fill='#F1F8FD' stroke='#5DADE2' stroke-width='0.8'>"
            "<path d='M32 28 L38 10 A5 5 0 0 1 44 8 L46 16 Z'/>"
            "<path d='M32 28 L14 18 A5 5 0 0 1 10 12 L20 9 Z'/>"
            "<path d='M32 28 L42 42 A5 5 0 0 1 41 48 L32 44 Z'/>"
            "</g>"
            "</svg></span>" + tr("app_title") + "</h1>"
            "</div>"
        )

        with gr.Tabs():
            # ─── Tab 1: 单图检测 ────────────────────────────
            with gr.TabItem(tr("tab_single")):
                with gr.Row(equal_height=False):
                    with gr.Column(scale=1):
                        gr.Markdown(tr("upload_section"))
                        img_input = gr.Image(
                            label=tr("upload_label"),
                            type="filepath",
                            height=350,
                        )
                        img_info_text = gr.Textbox(
                            label=tr("img_info_label"), interactive=False,
                            value=tr("img_info_default")
                        )
                        with gr.Row():
                            btn_analyze = gr.Button(tr("btn_analyze"), variant="primary", size="lg")
                            btn_clear = gr.Button(tr("btn_clear"), size="lg")

                        gr.Markdown(tr("examples_section"))
                        examples = []
                        if os.path.exists(IMAGE_DIR):
                            for i in range(1, 21):
                                img = os.path.join(IMAGE_DIR, f"{i:06d}.jpg")
                                if os.path.exists(img):
                                    examples.append([img])
                        if examples:
                            gr.Examples(examples=examples, inputs=img_input, label=tr("examples_label") % len(examples))

                        status_text = gr.Textbox(label=tr("status_label"), interactive=False)

                        with gr.Row():
                            btn_export_md = gr.Button(tr("btn_export_md"))
                            btn_export_json = gr.Button(tr("btn_export_json"))
                            btn_copy_json = gr.Button(tr("btn_copy_json"))

                        export_md_file = gr.File(label=tr("md_report_label"), interactive=False)
                        export_json_file = gr.File(label=tr("json_report_label"), interactive=False)

                    with gr.Column(scale=2):
                        summary_md = gr.Markdown(tr("waiting_summary"))
                        detail_html = gr.HTML(value=EMPTY_RESULT_HTML)
                        with gr.Accordion(tr("json_accordion"), open=False):
                            json_out = gr.Code(language="json", label=tr("json_raw_label"), interactive=False)

            # ─── Tab 2: 批量检测 ────────────────────────────
            with gr.TabItem(tr("tab_batch")):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown(tr("batch_upload_section"))
                        batch_input = gr.Files(
                            label=tr("batch_label"),
                            file_count="multiple",
                        )
                        btn_batch = gr.Button(tr("btn_batch"), variant="primary", size="lg")
                        batch_status = gr.Textbox(label=tr("progress_label"), lines=8, interactive=False)

                    with gr.Column(scale=2):
                        batch_summary = gr.Markdown(tr("batch_waiting"))
                        batch_html = gr.HTML(value=EMPTY_RESULT_HTML)

            # ─── Tab 3: 历史记录 ────────────────────────────
            with gr.TabItem(tr("tab_history")):
                # 筛选区
                with gr.Row(equal_height=True):
                    search_tb = gr.Textbox(label=tr("filter_search_label"),
                                           placeholder=tr("filter_search_ph"), scale=2)
                    risk_dd = gr.Dropdown(
                        label=tr("filter_risk_label"), choices=[
                            (tr("filter_risk_all"), ""),
                            (tr("filter_risk_high"), "high"),
                            (tr("filter_risk_normal"), "normal"),
                        ], value="", scale=1)
                    sort_dd = gr.Dropdown(
                        label=tr("sort_label"), choices=[
                            (tr("sort_time_desc"), "time_desc"),
                            (tr("sort_time_asc"), "time_asc"),
                            (tr("sort_risk"), "risk_desc"),
                            (tr("sort_time_cost"), "infer_time_desc"),
                        ], value="time_desc", scale=1)
                    pagesize_dd = gr.Dropdown(
                        label=tr("pagesize_label"),
                        choices=[("20", "20"), ("50", "50")], value="20", scale=1)
                with gr.Row(equal_height=True):
                    date_from_tb = gr.Textbox(label=tr("filter_date_from"),
                                              placeholder=tr("date_ph"), scale=1)
                    date_to_tb = gr.Textbox(label=tr("filter_date_to"),
                                            placeholder=tr("date_ph"), scale=1)
                    btn_quick_today = gr.Button(tr("quick_today"), size="sm")
                    btn_quick_7d = gr.Button(tr("quick_7d"), size="sm")
                    btn_quick_30d = gr.Button(tr("quick_30d"), size="sm")
                    btn_apply = gr.Button(tr("btn_apply_filter"), variant="primary")
                    btn_refresh = gr.Button(tr("btn_refresh"))
                    btn_reset_filter = gr.Button(tr("btn_reset_filter"))

                filter_status = gr.HTML(value="")
                history_stats = gr.HTML(value=tr("history_hint"))
                history_list = gr.HTML(value="")
                with gr.Row(equal_height=True):
                    btn_prev_page = gr.Button(tr("btn_prev_page"), size="sm")
                    page_info_html = gr.HTML(value="")
                    btn_next_page = gr.Button(tr("btn_next_page"), size="sm")
                history_charts = gr.HTML(value=tr("charts_hint"))
                page_state = gr.State(value=1)

                # 详情 / 删除
                gr.Markdown(tr("detail_section"))
                with gr.Row(equal_height=True):
                    history_record_dd = gr.Dropdown(
                        label=tr("history_select_label"),
                        choices=[], interactive=True,
                        info=tr("history_select_hint"), scale=3)
                    btn_view_detail = gr.Button(tr("btn_view_detail"), variant="primary", scale=1)
                    btn_delete_one = gr.Button(tr("btn_delete_one"),
                                               elem_classes=["wd-btn-danger"], scale=1)
                confirm_row = gr.Row(visible=False)
                with confirm_row:
                    confirm_md = gr.HTML(value="")
                    btn_delete_confirm = gr.Button(tr("btn_delete_confirm"),
                                                   variant="stop",
                                                   elem_classes=["wd-btn-danger"])
                    btn_delete_cancel = gr.Button(tr("btn_delete_cancel"))

                history_detail = gr.HTML(value=tr("detail_hint"))
                with gr.Accordion(tr("json_accordion2"), open=False):
                    history_json = gr.Code(language="json", interactive=False)

                with gr.Row(equal_height=True):
                    note_tb = gr.Textbox(label=tr("note_label"), lines=2, scale=3)
                    btn_save_note = gr.Button(tr("btn_save_note"), scale=1)

                # 清空（分级删除最高档：输入确认文字）
                with gr.Accordion(tr("btn_clear_history"), open=False):
                    gr.Markdown(tr("clear_warning"))
                    with gr.Row(equal_height=True):
                        clear_typed_tb = gr.Textbox(
                            label=tr("clear_typed_label"),
                            placeholder=tr("clear_typed_ph"), scale=1)
                        btn_clear_history = gr.Button(
                            tr("btn_clear_n", n=0), variant="stop",
                            elem_classes=["wd-btn-danger"], scale=1)

        # ─── 事件绑定 ───
        # Tab 1
        btn_analyze.click(
            fn=analyze_single,
            inputs=[img_input],
            outputs=[summary_md, detail_html, json_out, status_text, img_info_text, export_md_file, export_json_file],
        )
        btn_clear.click(
            fn=lambda: ("", EMPTY_RESULT_HTML, "", "", tr("img_info_default"), None, None),
            outputs=[img_input, detail_html, json_out, status_text, img_info_text, export_md_file, export_json_file],
        )
        # 导出按钮触发重新分析（因为导出文件已在分析时生成）
        btn_export_md.click(
            fn=lambda md: md,
            inputs=[export_md_file],
            outputs=[export_md_file],
        )
        btn_copy_json.click(
            fn=copy_json,
            inputs=[json_out],
            outputs=[status_text],
        )

        # Tab 2
        btn_batch.click(
            fn=analyze_batch,
            inputs=[batch_input],
            outputs=[batch_summary, batch_html, batch_status],
        )

        # Tab 3 — 查询（任何筛选变化 → 回第一页）
        QUERY_INPUTS = [search_tb, risk_dd, date_from_tb, date_to_tb,
                        sort_dd, pagesize_dd, page_state]
        QUERY_OUTPUTS = [history_stats, history_list, page_info_html,
                         history_record_dd, filter_status]

        def _run_query(search, risk, df, dt, sort, psize, page,
                       request: gr.Request = None):
            return query_history(search, risk, df, dt, sort, psize, page,
                                 request=request)

        btn_apply.click(fn=_run_query, inputs=QUERY_INPUTS, outputs=QUERY_OUTPUTS)
        search_tb.submit(fn=_run_query, inputs=QUERY_INPUTS, outputs=QUERY_OUTPUTS)
        for comp in (risk_dd, sort_dd, pagesize_dd):
            comp.change(fn=lambda: 1, outputs=page_state).then(
                fn=_run_query, inputs=QUERY_INPUTS, outputs=QUERY_OUTPUTS)

        # 快捷日期范围（设置日期后回第一页查询）
        def _set_range(days):
            return (*_quick_range(days), 1)
        for btn, days in ((btn_quick_today, 0), (btn_quick_7d, 7), (btn_quick_30d, 30)):
            btn.click(fn=lambda d=days: _set_range(d),
                      inputs=[], outputs=[date_from_tb, date_to_tb, page_state]).then(
                fn=_run_query, inputs=QUERY_INPUTS, outputs=QUERY_OUTPUTS)

        btn_reset_filter.click(
            fn=lambda: ("", "", "", "", "time_desc", "20", 1),
            inputs=[], outputs=[search_tb, risk_dd, date_from_tb, date_to_tb,
                                sort_dd, pagesize_dd, page_state]).then(
            fn=_run_query, inputs=QUERY_INPUTS, outputs=QUERY_OUTPUTS)

        # 分页
        btn_prev_page.click(fn=lambda p: max(1, int(p) - 1),
                            inputs=[page_state], outputs=page_state).then(
            fn=_run_query, inputs=QUERY_INPUTS, outputs=QUERY_OUTPUTS)
        btn_next_page.click(fn=lambda p: int(p) + 1,
                            inputs=[page_state], outputs=page_state).then(
            fn=_run_query, inputs=QUERY_INPUTS, outputs=QUERY_OUTPUTS)

        # 首次加载 / 手动刷新（图表同样按当前用户范围）
        def _charts_for(request: gr.Request = None):
            user_id, is_admin = _current_scope(request)
            scope = None if is_admin else user_id
            return charts_html(owner_user_id=scope)

        btn_refresh.click(fn=_run_query, inputs=QUERY_INPUTS, outputs=QUERY_OUTPUTS).then(
            fn=_charts_for, inputs=[], outputs=[history_charts])
        app.load(fn=_run_query, inputs=QUERY_INPUTS, outputs=QUERY_OUTPUTS).then(
            fn=_charts_for, inputs=[], outputs=[history_charts])

        # 详情
        btn_view_detail.click(
            fn=view_history_detail,
            inputs=[history_record_dd],
            outputs=[history_detail, history_json, note_tb],
        )
        btn_save_note.click(
            fn=save_note,
            inputs=[history_record_dd, note_tb],
            outputs=[filter_status],
        )

        # 单条删除（确认条两步）
        btn_delete_one.click(
            fn=ask_delete_record,
            inputs=[history_record_dd],
            outputs=[confirm_md, confirm_row],
        )
        btn_delete_cancel.click(
            fn=lambda: gr.update(visible=False),
            inputs=[], outputs=[confirm_row],
        )
        btn_delete_confirm.click(
            fn=do_delete_record,
            inputs=[history_record_dd],
            outputs=[history_stats, history_list, page_info_html,
                     history_record_dd, confirm_row, filter_status],
        )

        # 清空（输入确认文字）
        btn_clear_history.click(
            fn=do_clear_history,
            inputs=[clear_typed_tb],
            outputs=[history_stats, history_list, page_info_html,
                     history_record_dd, clear_typed_tb, filter_status],
        )

    # 页脚 — 放在 Tabs 外层，全宽居中
    gr.HTML(
        "<div class='footer-note'>"
        + tr("footer") +
        "</div>"
    )

    # gradio 6：js 参数在 launch()/mount_gradio_app() 上传入（页面加载后注入用户徽章）
    app._wd_badge_js = badge_js
    return app


if __name__ == "__main__":
    # 统一经由 server.py 组装（FastAPI 独立路由 + Gradio 挂载）
    from server import create_app
    import uvicorn
    from history import init_db

    init_db()
    port = int(os.environ.get("GRADIO_SERVER_PORT", "7860"))
    print("=" * 60)
    print(f"  {tr('app_title')} V1.0  [UI: {i18n.LANG}]  http://0.0.0.0:{port}")
    print("=" * 60)
    uvicorn.run(create_app(), host="0.0.0.0", port=port, log_level="info")
