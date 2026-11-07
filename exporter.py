"""
风电塔灾损测算软件 — 报告导出模块

支持导出为 Markdown 和 JSON 文件。
Markdown 导出跟随 i18n.LANG；JSON 导出保持模型原始中文键值。
"""

import os
import json
from datetime import datetime
from typing import Optional
from parser import get_field
import i18n
from i18n import tr_value, section_title, field_label, t as tr


def export_markdown(report: dict, image_name: str = "", infer_time: float = 0) -> str:
    """将检测报告导出为 Markdown 字符串（跟随当前语言）。"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# {tr('export_title')}",
        f"",
        f"| {tr('export_item')} | {tr('export_content')} |",
        f"|----|------|",
        f"| {tr('export_time')} | {ts} |",
        f"| {tr('export_image_name')} | {image_name} |",
        f"| {tr('export_infer_time')} | {infer_time:.1f}s |",
        f"",
    ]

    section_keys = [
        i18n.SECTION_CAPTION,
        i18n.SECTION_COMPONENT,
        i18n.SECTION_DAMAGE,
        i18n.SECTION_RISK,
        i18n.SECTION_OM,
        i18n.SECTION_UNCERTAINTY,
        i18n.SECTION_CONCLUSION,
    ]

    for section_key in section_keys:
        if section_key not in report:
            continue
        lines.append(f"## {section_title(section_key)}")
        lines.append("")
        for field_key, value in report[section_key].items():
            label = field_label(section_key, field_key)
            display = tr_value(str(value))
            lines.append(f"- **{label}**: {display}")
        lines.append("")

    return "\n".join(lines)


def export_json(report: dict, image_name: str = "", infer_time: float = 0) -> str:
    """将检测报告导出为格式化 JSON 字符串（保持模型原始输出）。"""
    export_data = {
        "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "image_name": image_name,
        "infer_time": round(infer_time, 1),
        "report": report,
    }
    return json.dumps(export_data, ensure_ascii=False, indent=2)


def save_export(report: dict, image_name: str, infer_time: float,
                fmt: str = "md", output_dir: str = None) -> str:
    """导出报告到文件，返回文件路径。

    Args:
        fmt: "md" 或 "json"
        output_dir: 输出目录，默认为项目下 exports/
    """
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "exports"
        )
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.splitext(image_name)[0] if image_name else "report"

    if fmt == "json":
        content = export_json(report, image_name, infer_time)
        filename = f"{base_name}_{timestamp}.json"
    else:
        content = export_markdown(report, image_name, infer_time)
        filename = f"{base_name}_{timestamp}.md"

    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


# ══════════════════════════════════════════════════════════
#  批量汇总导出（CSV / Markdown 汇总表）
# ══════════════════════════════════════════════════════════

def export_batch_csv(rows: list, header: list) -> str:
    """批量结果汇总 CSV 字符串。rows 为已渲染纯文本的行（无 HTML 标签）。"""
    import csv
    import io
    buf = io.StringIO()
    # utf-8-sig：让 Excel 直接打开不乱码
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buf.getvalue()


def export_batch_markdown(rows: list, header: list,
                          summary: str = "") -> str:
    """批量结果汇总 Markdown 字符串（跟随当前语言）。"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# {tr('batch_export_title')}",
        "",
        f"- {tr('export_time')}: {ts}",
    ]
    if summary:
        lines.append(f"- {tr('batch_export_summary')}: {summary}")
    lines += [
        "",
        f"| {' | '.join(header)} |",
        "|" + "|".join(["----"] * len(header)) + "|",
    ]
    for row in rows:
        cells = [str(c).replace("|", "\\|") for c in row]
        lines.append(f"| {' | '.join(cells)} |")
    return "\n".join(lines)


def save_batch_export(rows: list, header: list, summary: str = "",
                      fmt: str = "csv", output_dir: str = None) -> str:
    """批量汇总导出到文件，返回文件路径。fmt: "csv" 或 "md"。"""
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "exports"
        )
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if fmt == "md":
        content = export_batch_markdown(rows, header, summary)
        filename = f"batch_{timestamp}.md"
    else:
        content = export_batch_csv(rows, header)
        filename = f"batch_{timestamp}.csv"

    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        f.write(content)
    return filepath
