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
from history import init_db, save_record, list_records, get_record, clear_all, get_stats
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

def analyze_single(image):
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

        # 保存历史记录（先拿到记录 ID，用于摘要卡报告编号）
        record_id = save_record(os.path.basename(image_path), parsed, infer_time, image_path)

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

def analyze_batch(files):
    """批量分析多张图片。生成器逐张产出 (summary, table_html, status)，实时刷新进度。"""
    if not files:
        yield "", _empty_result_html(), tr("msg_upload_first")
        return

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

            # 保存历史
            save_record(image_name, parsed, infer_time, image_path)

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
#  Tab 3: 历史记录
# ══════════════════════════════════════════════════════════

def refresh_history():
    """刷新历史记录表格、统计卡、图表，并填充记录选择下拉框。"""
    records = list_records(50)
    stats = get_stats()
    chart_html = charts_html()

    # 记录选择下拉框选项（label：#id | 图片名 | 风险 | 优先级 | 时间）
    choices = []
    for r in records:
        risk_txt = tr("badge_high_risk") if r["high_risk"] else tr("badge_normal")
        prio = tr_value(r["priority"]) if r["priority"] else "—"
        label = f'#{r["id"]} | {r["image_name"]} | {risk_txt} | {prio} | {r["timestamp"]}'
        choices.append((label, str(r["id"])))

    dropdown_update = gr.update(choices=choices, value=choices[0][1] if choices else None)

    if not records:
        empty = uc.empty_state(tr("no_records"), tr("history_select_hint"), _UPLOAD_ICON_SVG)
        return empty, empty, chart_html, dropdown_update

    # 统计卡
    stats_html = (
        '<div class="wd-stats">'
        + uc.stat_card(stats["total"], tr("stat_total"))
        + uc.stat_card(stats["high_risk"], tr("stat_high_risk"), tone="danger")
        + uc.stat_card(stats["damaged"], tr("stat_damaged"), tone="warn")
        + uc.stat_card(stats["normal"], tr("stat_normal"), tone="success")
        + "</div>"
    )

    # 历史表
    header = [tr("hdr_id"), tr("hdr_timestamp"), tr("hdr_image"), tr("hdr_risk"),
              tr("hdr_damage"), tr("hdr_damage_type"), tr("hdr_component"),
              tr("hdr_priority"), tr("hdr_confidence"), tr("hdr_infer_time")]
    rows = []
    for r in records:
        risk_cell = (
            f'<span class="wd-badge wd-badge-{"danger" if r["high_risk"] else "success"}">'
            f'{tr("badge_high_risk") if r["high_risk"] else tr("badge_normal")}</span>'
        )
        row_cls = ' class="wd-row-danger"' if r["high_risk"] else ""
        cells = [
            f'<td class="wd-num">{r["id"]}</td>',
            f'<td class="wd-num">{uc.esc(r["timestamp"])}</td>',
            f"<td>{uc.esc(r['image_name'])}</td>",
            f"<td>{risk_cell}</td>",
            f"<td>{uc.risk_badge(tr_value(r['has_damage'])) if r['has_damage'] else '—'}</td>",
            f"<td>{uc.esc(tr_value(r['damage_type'])) if r['damage_type'] else '—'}</td>",
            f"<td>{uc.esc(tr_value(r['component'])) if r['component'] else '—'}</td>",
            f"<td>{uc.risk_badge(tr_value(r['priority'])) if r['priority'] else '—'}</td>",
            f"<td>{uc.esc(tr_value(r['confidence'])) if r['confidence'] else '—'}</td>",
            f'<td class="wd-num">{r["infer_time"] or "—"}s</td>',
        ]
        rows.append(f"<tr{row_cls}>{''.join(cells)}</tr>")
    table_html = uc.data_table(header, "".join(rows))

    return stats_html, table_html, chart_html, dropdown_update


def view_history_detail(record_id_str):
    """查看单条历史记录详情（记录由下拉框选择，替代手输 ID）。"""
    if not record_id_str or not str(record_id_str).strip().isdigit():
        return uc.status_banner(tr("msg_invalid_id"), "warn"), ""

    record = get_record(int(str(record_id_str).strip()))
    if not record:
        return uc.status_banner(tr("msg_record_not_found", id=record_id_str), "error"), ""

    report = json.loads(record["json_report"])
    detail_html, formatted = _build_result_html(report, meta={
        "record_id": record["id"],
        "timestamp": record["timestamp"],
        "infer_time": record["infer_time"] or 0,
    })
    json_str = formatted["json_str"]

    return detail_html, json_str


def copy_json(json_str):
    """复制 JSON 到剪贴板（返回提示文字）。"""
    if json_str:
        return tr("msg_copied")
    return tr("msg_no_json")


def do_clear_history(confirmed):
    """清空历史记录（需勾选确认框；未勾选则提示并保留数据）。"""
    if not confirmed:
        stats_html, table_html, chart_html, dropdown_update = refresh_history()
        return stats_html, table_html, chart_html, dropdown_update, "", tr("msg_confirm_first")
    n = get_stats()["total"]
    clear_all()
    stats_html, table_html, chart_html, dropdown_update = refresh_history()
    return stats_html, table_html, chart_html, dropdown_update, "", tr("msg_cleared_n", n=n)


# ══════════════════════════════════════════════════════════
#  Gradio 界面
# ══════════════════════════════════════════════════════════

def build_ui():
    with gr.Blocks(title=tr("app_title")) as app:
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
                with gr.Row():
                    btn_refresh = gr.Button(tr("btn_refresh"), variant="primary")
                    btn_clear_history = gr.Button(tr("btn_clear_history"), variant="stop",
                                                  elem_classes=["wd-btn-danger"])

                history_stats = gr.HTML(value=tr("history_hint"))
                history_charts = gr.HTML(value=tr("charts_hint"))
                history_table = gr.HTML(value="")

                gr.Markdown(tr("detail_section"))
                with gr.Row():
                    history_record_dd = gr.Dropdown(
                        label=tr("history_select_label"),
                        choices=[], interactive=True,
                        info=tr("history_select_hint"),
                    )
                    btn_view_detail = gr.Button(tr("btn_view_detail"), variant="primary")
                    btn_copy_history_json = gr.Button(tr("btn_copy_json"))

                history_detail = gr.HTML(value=tr("detail_hint"))
                with gr.Accordion(tr("json_accordion2"), open=False):
                    history_json = gr.Code(language="json", interactive=False)

                clear_confirm = gr.Checkbox(label=tr("confirm_clear_label"), value=False)

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

        # Tab 3
        btn_refresh.click(
            fn=refresh_history,
            outputs=[history_stats, history_table, history_charts, history_record_dd],
        )
        btn_clear_history.click(
            fn=do_clear_history,
            inputs=[clear_confirm],
            outputs=[history_stats, history_table, history_charts, history_record_dd,
                     clear_confirm, batch_status],
        )
        btn_view_detail.click(
            fn=view_history_detail,
            inputs=[history_record_dd],
            outputs=[history_detail, history_json],
        )
        btn_copy_history_json.click(
            fn=copy_json,
            inputs=[history_json],
            outputs=[batch_status],
        )

    # 页脚 — 放在 Tabs 外层，全宽居中
    gr.HTML(
        "<div class='footer-note'>"
        + tr("footer") +
        "</div>"
    )

    return app


if __name__ == "__main__":
    init_db()
    print("=" * 60)
    print(f"  {tr('app_title')} V1.0  [UI: {i18n.LANG}]")
    print("=" * 60)

    # 支持环境变量覆盖端口（软著截图等自动化场景用）
    server_port = int(os.environ.get("GRADIO_SERVER_PORT", "7860"))

    app = build_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=server_port,
        share=False,
        show_error=True,
        theme=gr.themes.Soft(primary_hue="blue"),  # Gradio 6：theme/css 移至 launch()
        css=uc.BASE_CSS,
    )
