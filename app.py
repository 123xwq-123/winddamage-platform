#!/usr/bin/env python3
"""
风电塔灾损测算软件 — Gradio 前端

功能：
  - 单图/批量图片上传 → 模型推理 → 结构化报告展示
  - 高风险自动告警（红色高亮）
  - 完整 JSON 报告折叠查看
  - 报告导出（Markdown / JSON）
  - 检测历史记录（SQLite 存储，可回看）
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

# ─── 全局模型实例 ─────────────────────────────────────────
_model = None

# ─── 空状态：文件上传框样式 ───────────────────────────────
def _empty_result_html():
    return (
        "<div style='border:2px dashed #b8c4d0;border-radius:10px;"
        "padding:44px 24px;text-align:center;background:#fbfcfd;'>"
        "<svg width='52' height='52' viewBox='0 0 24 24' fill='none' stroke='#7f9cc4' "
        "stroke-width='1.4' stroke-linecap='round' stroke-linejoin='round' "
        "style='margin-bottom:6px;'>"
        "<path d='M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'/>"
        "<polyline points='17 8 12 3 7 8'/>"
        "<line x1='12' y1='3' x2='12' y2='15'/>"
        "</svg>"
        "<div style='font-size:19px;color:#3a4a5c;margin-bottom:8px;'>"
        f"{tr('empty_upload')}</div>"
        "<div style='font-size:14px;color:#8a9ab0;margin-bottom:18px;'>"
        f"{tr('empty_format')}</div>"
        "<div style='display:inline-block;padding:8px 30px;background:#125191;"
        "color:#fff;border-radius:6px;font-size:15px;'>"
        f"{tr('empty_btn')}</div>"
        "</div>"
    )


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


def _build_result_html(parsed):
    """将解析后的 JSON 构建 HTML 展示。"""
    formatted = format_report(parsed)
    html_parts = []

    if formatted["high_risk"]:
        html_parts.append(
            '<div style="background:#FDEDEC;border:2px solid #E74C3C;'
            'border-radius:8px;padding:12px;margin-bottom:16px;">'
            '<span style="font-size:18px;font-weight:bold;color:#E74C3C;">'
            f'{tr("msg_high_risk_banner")}</span></div>'
        )

    for sec in formatted["sections"]:
        html_parts.append('<div style="margin-bottom:16px;">')
        html_parts.append(
            f'<h3 style="color:#125191;border-bottom:2px solid #125191;'
            f'padding-bottom:4px;">{sec["icon"]} {sec["title"]}</h3>'
        )
        html_parts.append('<table style="width:100%;border-collapse:collapse;">')
        for f in sec["fields"]:
            value_html = f["value"]
            if f["is_risk"] and f["value"] in get_risk_badge_values():
                value_html = get_risk_badge(f["value"], f["raw_field"])
            if len(f["value"]) > 30:
                html_parts.append(
                    f'<tr><td style="width:140px;padding:4px 8px;color:#555;'
                    f'vertical-align:top;">{f["label"]}</td>'
                    f'<td style="padding:4px 8px;">{value_html}</td></tr>'
                )
            else:
                html_parts.append(
                    f'<tr><td style="width:140px;padding:4px 8px;color:#555;">'
                    f'{f["label"]}</td>'
                    f'<td style="padding:4px 8px;font-weight:bold;">'
                    f'{value_html}</td></tr>'
                )
        html_parts.append('</table></div>')

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
        return tr("msg_please_upload"), "", "", tr("msg_upload_first"), "", None, None

    image_path = image if isinstance(image, str) else getattr(image, 'name', str(image))

    if not os.path.exists(image_path):
        return tr("msg_file_not_exist"), "", "", f'{tr("msg_file_not_exist")}: {image_path}', "", None, None

    img_info = get_image_info(image_path)

    try:
        t0 = time.time()
        parsed, raw, infer_time = _do_inference(image_path)
        total_time = time.time() - t0

        if parsed is None:
            return (
                tr("msg_parse_fail"), f"<pre>{raw[:2000]}</pre>", raw,
                tr("msg_infer_parse_fail", t=infer_time), img_info, None, None
            )

        detail_html, formatted = _build_result_html(parsed)
        summary = format_summary(parsed)
        json_str = formatted["json_str"]
        val = formatted["validation"]
        image_name = os.path.basename(image_path)
        comp = "✅" if val["valid"] else f"⚠️ {val['message']}"
        status = (f'✅ {tr("msg_infer_done", t=infer_time)} | '
                  f'{tr("msg_json_ok")} | '
                  f'{tr("msg_completeness")}: {comp}')

        # 保存历史记录
        save_record(image_name, parsed, infer_time, image_path)

        # 导出文件
        md_path = save_export(parsed, image_name, infer_time, fmt="md")
        json_path = save_export(parsed, image_name, infer_time, fmt="json")

        return summary, detail_html, json_str, status, img_info, md_path, json_path

    except Exception as e:
        import traceback
        traceback.print_exc()
        return (
            tr("msg_infer_fail"), f"<pre>{traceback.format_exc()}</pre>", "",
            tr("msg_error", e=e), img_info, None, None
        )


# ══════════════════════════════════════════════════════════
#  Tab 2: 批量检测
# ══════════════════════════════════════════════════════════

def analyze_batch(files):
    """批量分析多张图片，返回 (summary_table, detail_html, status)。"""
    if not files:
        return "", "", tr("msg_upload_first")

    results = []
    all_html = []
    status_parts = []
    total = len(files)
    ok_count = 0

    for i, f in enumerate(files):
        image_path = f if isinstance(f, str) else f.name
        image_name = os.path.basename(image_path)

        try:
            t0 = time.time()
            parsed, raw, infer_time = _do_inference(image_path)

            if parsed is None:
                results.append([image_name, "❌", "—", "—", "—", f"{infer_time:.1f}s", tr("msg_parse_fail")])
                status_parts.append(f'[{i+1}/{total}] {image_name}: ❌ {tr("msg_parse_fail")}')
                continue

            ok_count += 1
            has_damage = tr_value(get_field(parsed, i18n.SECTION_DAMAGE, "是否存在损伤"))
            damage_type = tr_value(get_field(parsed, i18n.SECTION_DAMAGE, "损伤类型"))
            component = tr_value(get_field(parsed, i18n.SECTION_COMPONENT, "构件名称"))
            priority = tr_value(get_field(parsed, i18n.SECTION_CONCLUSION, "巡检优先级"))

            risk_icon = "🔴" if is_high_risk(parsed) else "🟢"
            results.append([
                image_name, risk_icon, has_damage, damage_type,
                component, priority, f"{infer_time:.1f}s"
            ])

            # 详情
            detail_html, _ = _build_result_html(parsed)
            all_html.append(f"<h3>📷 {image_name}</h3>{detail_html}<hr>")

            # 保存历史
            save_record(image_name, parsed, infer_time, image_path)

            status_parts.append(f"[{i+1}/{total}] {image_name}: ✅ {damage_type} | {priority}")

        except Exception as e:
            results.append([image_name, "❌", "—", "—", "—", "—", str(e)[:50]])
            status_parts.append(f"[{i+1}/{total}] {image_name}: ❌ {e}")

    # 汇总表
    header = [tr("hdr_image"), tr("hdr_risk"), tr("hdr_damage"), tr("hdr_damage_type"),
              tr("hdr_component"), tr("hdr_priority"), tr("hdr_time_cost")]
    table_html = '<table style="width:100%;border-collapse:collapse;font-size:14px;">'
    table_html += '<tr style="background:#125191;color:white;">'
    for h in header:
        table_html += f'<th style="padding:6px 8px;text-align:left;">{h}</th>'
    table_html += '</tr>'
    for row in results:
        table_html += '<tr style="border-bottom:1px solid #ddd;">'
        for cell in row:
            table_html += f'<td style="padding:4px 8px;">{cell}</td>'
        table_html += '</tr>'
    table_html += '</table>'

    summary = tr("batch_done", ok=ok_count, total=total)

    status_text = "\n".join(status_parts)
    detail_combined = "".join(all_html) if all_html else f"<p style='color:#999;'>{tr('no_detail')}</p>"

    return summary, table_html + detail_combined, status_text


# ══════════════════════════════════════════════════════════
#  Tab 3: 历史记录
# ══════════════════════════════════════════════════════════

def refresh_history():
    """刷新历史记录表格和统计（含图表）。"""
    records = list_records(50)
    stats = get_stats()
    chart_html = charts_html()

    if not records:
        no_rec = f"<p style='color:#999;'>{tr('no_records')}</p>"
        return no_rec, no_rec, chart_html

    # 统计面板
    stats_html = f"""
    <div style="display:flex;gap:16px;margin-bottom:16px;">
        <div style="background:#EBF5FB;border-radius:8px;padding:12px;text-align:center;flex:1;">
            <div style="font-size:28px;font-weight:bold;color:#125191;">{stats['total']}</div>
            <div style="color:#555;">{tr('stat_total')}</div>
        </div>
        <div style="background:#FDEDEC;border-radius:8px;padding:12px;text-align:center;flex:1;">
            <div style="font-size:28px;font-weight:bold;color:#E74C3C;">{stats['high_risk']}</div>
            <div style="color:#555;">{tr('stat_high_risk')}</div>
        </div>
        <div style="background:#FEF9E7;border-radius:8px;padding:12px;text-align:center;flex:1;">
            <div style="font-size:28px;font-weight:bold;color:#F39C12;">{stats['damaged']}</div>
            <div style="color:#555;">{tr('stat_damaged')}</div>
        </div>
        <div style="background:#E8F8F5;border-radius:8px;padding:12px;text-align:center;flex:1;">
            <div style="font-size:28px;font-weight:bold;color:#27AE60;">{stats['normal']}</div>
            <div style="color:#555;">{tr('stat_normal')}</div>
        </div>
    </div>
    """

    # 历史表
    header = [tr("hdr_id"), tr("hdr_timestamp"), tr("hdr_image"), tr("hdr_risk"),
              tr("hdr_damage"), tr("hdr_damage_type"), tr("hdr_component"),
              tr("hdr_priority"), tr("hdr_confidence"), tr("hdr_infer_time")]
    table_html = '<table style="width:100%;border-collapse:collapse;font-size:13px;">'
    table_html += '<tr style="background:#125191;color:white;">'
    for h in header:
        table_html += f'<th style="padding:5px 6px;text-align:left;">{h}</th>'
    table_html += '</tr>'
    for r in records:
        risk = "🔴" if r["high_risk"] else "🟢"
        row_bg = "#FDEDEC" if r["high_risk"] else ""
        table_html += f'<tr style="border-bottom:1px solid #ddd;background:{row_bg};">'
        table_html += f'<td style="padding:4px 6px;">{r["id"]}</td>'
        table_html += f'<td style="padding:4px 6px;">{r["timestamp"]}</td>'
        table_html += f'<td style="padding:4px 6px;">{r["image_name"]}</td>'
        table_html += f'<td style="padding:4px 6px;">{risk}</td>'
        table_html += f'<td style="padding:4px 6px;">{tr_value(r["has_damage"]) or "—"}</td>'
        table_html += f'<td style="padding:4px 6px;">{tr_value(r["damage_type"]) or "—"}</td>'
        table_html += f'<td style="padding:4px 6px;">{tr_value(r["component"]) or "—"}</td>'
        table_html += f'<td style="padding:4px 6px;">{tr_value(r["priority"]) or "—"}</td>'
        table_html += f'<td style="padding:4px 6px;">{tr_value(r["confidence"]) or "—"}</td>'
        table_html += f'<td style="padding:4px 6px;">{r["infer_time"] or "—"}s</td>'
        table_html += '</tr>'
    table_html += '</table>'

    return stats_html, table_html, chart_html


def view_history_detail(record_id_str):
    """查看单条历史记录详情。"""
    if not record_id_str or not record_id_str.strip().isdigit():
        return f"<p style='color:#999;'>{tr('msg_invalid_id')}</p>", ""

    record = get_record(int(record_id_str.strip()))
    if not record:
        return f"<p style='color:#E74C3C;'>{tr('msg_record_not_found', id=record_id_str)}</p>", ""

    report = json.loads(record["json_report"])
    detail_html, formatted = _build_result_html(report)

    header = f"<h3>📷 {record['image_name']} — {record['timestamp']}</h3>"
    json_str = formatted["json_str"]

    return header + detail_html, json_str


def copy_json(json_str):
    """复制 JSON 到剪贴板（返回提示文字）。"""
    if json_str:
        return tr("msg_copied")
    return tr("msg_no_json")


def do_clear_history():
    """清空历史记录。"""
    clear_all()
    stats_html, table_html, chart_html = refresh_history()
    return stats_html, table_html, chart_html, tr("msg_cleared")


# ══════════════════════════════════════════════════════════
#  Gradio 界面
# ══════════════════════════════════════════════════════════

def build_ui():
    with gr.Blocks(
        title=tr("app_title"),
        theme=gr.themes.Soft(primary_hue="blue"),
        css="""
        .main-title { text-align: center; padding: 12px 0 4px; }
        .main-title h1 { font-size: 26px; color: #125191; margin-bottom: 4px; }
        .title-icon { display: inline-flex; vertical-align: -6px; margin-right: 6px; }
        .footer-note { text-align: center; color: #999; font-size: 12px; padding: 10px 0 4px; margin-top: 8px; }
        .status-bar { font-family: monospace; }
        footer { display: none !important; }
        """,
    ) as app:
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

                        status_text = gr.Textbox(label=tr("status_label"), interactive=False, elem_classes=["status-bar"])

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
                    btn_clear_history = gr.Button(tr("btn_clear_history"), variant="stop")

                history_stats = gr.HTML(value=tr("history_hint"))
                history_charts = gr.HTML(value=tr("charts_hint"))
                history_table = gr.HTML(value="")

                gr.Markdown(tr("detail_section"))
                with gr.Row():
                    history_id_input = gr.Textbox(label=tr("id_label"), placeholder=tr("id_placeholder"))
                    btn_view_detail = gr.Button(tr("btn_view_detail"), variant="primary")
                    btn_copy_history_json = gr.Button(tr("btn_copy_json"))

                history_detail = gr.HTML(value=tr("detail_hint"))
                with gr.Accordion(tr("json_accordion2"), open=False):
                    history_json = gr.Code(language="json", interactive=False)

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
        btn_refresh.click(fn=refresh_history, outputs=[history_stats, history_table, history_charts])
        btn_clear_history.click(fn=do_clear_history, outputs=[history_stats, history_table, history_charts, batch_status])
        btn_view_detail.click(fn=view_history_detail, inputs=[history_id_input], outputs=[history_detail, history_json])
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
    )
