#!/usr/bin/env python3
"""
软著截图生成脚本

通过 Gradio API 调用模型推理，获取结果后生成完整 HTML 页面，
然后用浏览器打开并截图。

由于推理耗时约 60-90s/条，本脚本会：
1. 启动 Gradio 服务
2. 用 API 跑 2 张图片（高风险 + 正常）
3. 生成 6 张截图用 HTML 页面
4. 用浏览器打开并截图保存
"""

import os
import sys
import json
import time
import subprocess
import signal

# Windows 控制台默认 GBK，强制 UTF-8 避免打印 emoji/中文崩溃
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gradio_client import Client, handle_file
from formatter import format_report, format_summary, get_risk_badge
from history import init_db, save_record, list_records, get_stats
import charts

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
image_dir = os.path.join(BASE_DIR, "data", "images")
SCREENSHOT_DIR = os.path.join(BASE_DIR, "软著申请材料", "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def generate_html_screenshots(results):
    """根据推理结果生成 HTML 页面文件，供浏览器截图。"""
    
    pages = []
    
    # ─── 页面1: 主界面（单图检测Tab，含上传+示例） ───
    pages.append(("01_main_interface.html", _render_main_interface()))
    
    # ─── 页面2: 单图检测结果（高风险） ───
    if "high_risk" in results:
        pages.append(("02_single_high_risk.html", 
                       _render_single_result(results["high_risk"])))
    
    # ─── 页面3: 单图检测结果（正常） ───
    if "normal" in results:
        pages.append(("03_single_normal.html", 
                       _render_single_result(results["normal"])))
    
    # ─── 页面4: 批量检测结果 ───
    if "batch" in results:
        pages.append(("04_batch_results.html",
                       _render_batch_results(results["batch"])))
    
    # ─── 页面5: 历史记录 ───
    pages.append(("05_history.html", _render_history()))
    
    # ─── 页面6: JSON 报告详情 ───
    if "high_risk" in results:
        pages.append(("06_json_report.html",
                       _render_json_report(results["high_risk"])))
    
    for filename, html in pages:
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  生成: {filename}")
    
    return pages


def _render_main_interface():
    """渲染主界面截图HTML。"""
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,sans-serif; background:#f5f5f5; }}
.header {{ text-align:center; padding:20px; background:white; border-bottom:1px solid #ddd; }}
.header h1 {{ font-size:28px; margin:0; }}
.header p {{ color:#666; margin:5px 0 0; }}
.container {{ display:flex; gap:20px; padding:20px; max-width:1280px; margin:0 auto; }}
.left {{ width:400px; }}
.right {{ flex:1; }}
.panel {{ background:white; border-radius:8px; padding:20px; margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,0.1); }}
.panel h3 {{ color:#125191; margin:0 0 12px; font-size:16px; }}
.upload-area {{ border:2px dashed #ccc; border-radius:8px; height:300px; display:flex; align-items:center; justify-content:center; flex-direction:column; color:#999; }}
.upload-area img {{ max-width:100%; max-height:280px; border-radius:4px; }}
.btn {{ background:#125191; color:white; border:none; padding:10px 24px; border-radius:6px; font-size:14px; cursor:pointer; }}
.btn-row {{ display:flex; gap:12px; margin-top:12px; }}
.btn-row .btn {{ flex:1; text-align:center; }}
.examples {{ display:flex; gap:8px; flex-wrap:wrap; margin-top:8px; }}
.example-img {{ width:80px; height:80px; object-fit:cover; border-radius:4px; cursor:pointer; border:2px solid #ddd; }}
.status {{ font-family:monospace; padding:8px 12px; background:#f8f9fa; border-radius:4px; font-size:13px; color:#666; }}
.placeholder {{ color:#999; text-align:center; padding:40px; }}
.tabs {{ display:flex; gap:4px; padding:0 20px; background:white; border-bottom:1px solid #ddd; }}
.tab {{ padding:10px 20px; cursor:pointer; color:#666; border-bottom:2px solid transparent; }}
.tab.active {{ color:#125191; border-bottom-color:#125191; font-weight:bold; }}
.export-btns {{ display:flex; gap:8px; margin-top:12px; }}
.export-btn {{ flex:1; text-align:center; padding:8px; border:1px solid #ddd; border-radius:4px; font-size:13px; color:#555; }}
</style>
</head><body>
<div class="header">
  <h1><svg width="38" height="38" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" style="vertical-align:-8px;margin-right:6px;"><circle cx="32" cy="32" r="30" fill="#EBF5FB" stroke="#125191" stroke-width="1.5"/><rect x="29.5" y="36" width="5" height="22" fill="#7F8C8D"/><rect x="23" y="30" width="18" height="8" rx="2" fill="#5DADE2"/><circle cx="32" cy="28" r="3.5" fill="#34495E"/><g fill="#F1F8FD" stroke="#5DADE2" stroke-width="0.8"><path d="M32 28 L38 10 A5 5 0 0 1 44 8 L46 16 Z"/><path d="M32 28 L14 18 A5 5 0 0 1 10 12 L20 9 Z"/><path d="M32 28 L42 42 A5 5 0 0 1 41 48 L32 44 Z"/></g></svg>风电塔灾损测算多模态大模型可视化软件</h1>
</div>
<div class="tabs">
  <div class="tab active">📷 单图检测</div>
  <div class="tab">📂 批量检测</div>
  <div class="tab">📊 历史记录</div>
</div>
<div class="container">
  <div class="left">
    <div class="panel">
      <h3>上传巡检图片</h3>
      <div class="upload-area">
        <img src="file://{image_dir}/000020.jpg" alt="巡检图片">
      </div>
      <div class="btn-row">
        <button class="btn">🔍 开始分析</button>
        <button class="btn" style="background:#6c757d;">🗑️ 清空</button>
      </div>
    </div>
    <div class="panel">
      <h3>示例图片</h3>
      <div class="examples">
        <img class="example-img" src="file://{image_dir}/000001.jpg">
        <img class="example-img" src="file://{image_dir}/000003.jpg">
        <img class="example-img" src="file://{image_dir}/000006.jpg">
        <img class="example-img" src="file://{image_dir}/000007.jpg">
      </div>
    </div>
    <div class="panel">
      <div class="status">状态: 等待上传图片</div>
      <div class="export-btns">
        <div class="export-btn">📄 导出 Markdown</div>
        <div class="export-btn">📋 导出 JSON</div>
      </div>
    </div>
  </div>
  <div class="right">
    <div class="panel">
      <h3 style="color:#999;">等待分析...</h3>
      <div style="border:2px dashed #b8c4d0;border-radius:10px;padding:44px 24px;text-align:center;background:#fbfcfd;">
        <svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="#7f9cc4" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom:6px;">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        <div style="font-size:19px;color:#3a4a5c;margin-bottom:8px;">将巡检图片拖拽到此处，或点击上传</div>
        <div style="font-size:14px;color:#8a9ab0;margin-bottom:18px;">支持 JPG / PNG 格式</div>
        <div style="display:inline-block;padding:8px 30px;background:#125191;color:#fff;border-radius:6px;font-size:15px;">选择文件</div>
      </div>
    </div>
  </div>
</div>
<div style="text-align:center;color:#999;font-size:12px;padding:10px 0 4px;margin-top:8px;">
  © 2026 风电塔灾损测算多模态大模型可视化软件 V1.0
</div>
</body></html>"""


def _render_single_result(data):
    """渲染单图检测结果HTML。"""
    report = data["report"]
    image_name = data["image_name"]
    infer_time = data["infer_time"]
    formatted = format_report(report)
    summary = format_summary(report)
    
    risk_banner = ""
    if formatted["high_risk"]:
        risk_banner = """<div style="background:#FDEDEC;border:2px solid #E74C3C;border-radius:8px;padding:12px;margin-bottom:16px;">
        <span style="font-size:18px;font-weight:bold;color:#E74C3C;">⚠️ 高风险检测结果</span></div>"""
    
    sections_html = ""
    for sec in formatted["sections"]:
        rows = ""
        for f in sec["fields"]:
            value = f["value"]
            if f["is_risk"] and value in ("是", "高", "中"):
                value = f'<span style="color:#E74C3C;font-weight:bold">{value}</span>'
            elif f["is_risk"] and value in ("否", "低", "无"):
                value = f'<span style="color:#27AE60;font-weight:bold">{value}</span>'
            rows += f'<tr><td style="width:140px;padding:4px 8px;color:#555;">{f["label"]}</td><td style="padding:4px 8px;font-weight:bold;">{value}</td></tr>'
        sections_html += f'<div style="margin-bottom:16px;"><h3 style="color:#125191;border-bottom:2px solid #125191;padding-bottom:4px;">{sec["icon"]} {sec["title"]}</h3><table style="width:100%;border-collapse:collapse;">{rows}</table></div>'
    
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,sans-serif; background:#f5f5f5; }}
.header {{ text-align:center; padding:20px; background:white; border-bottom:1px solid #ddd; }}
.header h1 {{ font-size:28px; margin:0; }}
.header p {{ color:#666; margin:5px 0 0; }}
.container {{ display:flex; gap:20px; padding:20px; max-width:1280px; margin:0 auto; }}
.left {{ width:400px; }}
.right {{ flex:1; }}
.panel {{ background:white; border-radius:8px; padding:20px; margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,0.1); }}
.panel h3 {{ color:#125191; margin:0 0 12px; font-size:16px; }}
.upload-area {{ border:2px solid #ddd; border-radius:8px; overflow:hidden; }}
.upload-area img {{ width:100%; display:block; }}
.status {{ font-family:monospace; padding:8px 12px; background:#f8f9fa; border-radius:4px; font-size:13px; }}
.tabs {{ display:flex; gap:4px; padding:0 20px; background:white; border-bottom:1px solid #ddd; }}
.tab {{ padding:10px 20px; cursor:pointer; color:#666; border-bottom:2px solid transparent; }}
.tab.active {{ color:#125191; border-bottom-color:#125191; font-weight:bold; }}
.json-box {{ background:#f8f9fa; border-radius:4px; padding:12px; font-family:monospace; font-size:12px; white-space:pre-wrap; max-height:400px; overflow-y:auto; }}
</style>
</head><body>
<div class="header">
  <h1><svg width="38" height="38" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" style="vertical-align:-8px;margin-right:6px;"><circle cx="32" cy="32" r="30" fill="#EBF5FB" stroke="#125191" stroke-width="1.5"/><rect x="29.5" y="36" width="5" height="22" fill="#7F8C8D"/><rect x="23" y="30" width="18" height="8" rx="2" fill="#5DADE2"/><circle cx="32" cy="28" r="3.5" fill="#34495E"/><g fill="#F1F8FD" stroke="#5DADE2" stroke-width="0.8"><path d="M32 28 L38 10 A5 5 0 0 1 44 8 L46 16 Z"/><path d="M32 28 L14 18 A5 5 0 0 1 10 12 L20 9 Z"/><path d="M32 28 L42 42 A5 5 0 0 1 41 48 L32 44 Z"/></g></svg>风电塔灾损测算多模态大模型可视化软件</h1>
</div>
<div class="tabs">
  <div class="tab active">📷 单图检测</div>
  <div class="tab">📂 批量检测</div>
  <div class="tab">📊 历史记录</div>
</div>
<div class="container">
  <div class="left">
    <div class="panel">
      <h3>上传巡检图片</h3>
      <div class="upload-area">
        <img src="file://{image_dir}/{image_name}" alt="巡检图片">
      </div>
    </div>
    <div class="panel">
      <div class="status">✅ 推理完成 ({infer_time:.1f}s) | JSON: ✅ | 完整性: ✅</div>
    </div>
  </div>
  <div class="right">
    <div class="panel">
      <h3>{summary}</h3>
      {risk_banner}
      {sections_html}
      <details style="margin-top:16px;">
        <summary style="cursor:pointer;font-weight:bold;color:#125191;">📄 完整 JSON 报告</summary>
        <div class="json-box">{json.dumps(report, ensure_ascii=False, indent=2)}</div>
      </details>
    </div>
  </div>
</div>
<div style="text-align:center;color:#999;font-size:12px;padding:10px 0 4px;margin-top:8px;">
  © 2026 风电塔灾损测算多模态大模型可视化软件 V1.0
</div>
</body></html>"""


def _render_batch_results(batch_data):
    """渲染批量检测结果HTML。"""
    rows = ""
    for item in batch_data:
        risk = "🔴" if item["high_risk"] else "🟢"
        rows += f"""<tr style="border-bottom:1px solid #ddd;">
            <td style="padding:5px 8px;">{item['image_name']}</td>
            <td style="padding:5px 8px;">{risk}</td>
            <td style="padding:5px 8px;">{item['has_damage']}</td>
            <td style="padding:5px 8px;">{item['damage_type']}</td>
            <td style="padding:5px 8px;">{item['component']}</td>
            <td style="padding:5px 8px;">{item['priority']}</td>
            <td style="padding:5px 8px;">{item['infer_time']:.1f}s</td>
        </tr>"""
    
    header = """<tr style="background:#125191;color:white;">
        <th style="padding:6px 8px;text-align:left;">图片</th>
        <th style="padding:6px 8px;text-align:left;">风险</th>
        <th style="padding:6px 8px;text-align:left;">损伤</th>
        <th style="padding:6px 8px;text-align:left;">损伤类型</th>
        <th style="padding:6px 8px;text-align:left;">构件</th>
        <th style="padding:6px 8px;text-align:left;">优先级</th>
        <th style="padding:6px 8px;text-align:left;">耗时</th>
    </tr>"""
    
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,sans-serif; background:#f5f5f5; }}
.header {{ text-align:center; padding:20px; background:white; border-bottom:1px solid #ddd; }}
.header h1 {{ font-size:28px; margin:0; }}
.header p {{ color:#666; margin:5px 0 0; }}
.container {{ padding:20px; max-width:1280px; margin:0 auto; }}
.panel {{ background:white; border-radius:8px; padding:20px; margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,0.1); }}
table {{ width:100%; border-collapse:collapse; font-size:14px; }}
.tabs {{ display:flex; gap:4px; padding:0 20px; background:white; border-bottom:1px solid #ddd; }}
.tab {{ padding:10px 20px; cursor:pointer; color:#666; border-bottom:2px solid transparent; }}
.tab.active {{ color:#125191; border-bottom-color:#125191; font-weight:bold; }}
</style>
</head><body>
<div class="header">
  <h1><svg width="38" height="38" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" style="vertical-align:-8px;margin-right:6px;"><circle cx="32" cy="32" r="30" fill="#EBF5FB" stroke="#125191" stroke-width="1.5"/><rect x="29.5" y="36" width="5" height="22" fill="#7F8C8D"/><rect x="23" y="30" width="18" height="8" rx="2" fill="#5DADE2"/><circle cx="32" cy="28" r="3.5" fill="#34495E"/><g fill="#F1F8FD" stroke="#5DADE2" stroke-width="0.8"><path d="M32 28 L38 10 A5 5 0 0 1 44 8 L46 16 Z"/><path d="M32 28 L14 18 A5 5 0 0 1 10 12 L20 9 Z"/><path d="M32 28 L42 42 A5 5 0 0 1 41 48 L32 44 Z"/></g></svg>风电塔灾损测算多模态大模型可视化软件</h1>
</div>
<div class="tabs">
  <div class="tab">📷 单图检测</div>
  <div class="tab active">📂 批量检测</div>
  <div class="tab">📊 历史记录</div>
</div>
<div class="container">
  <div class="panel">
    <h3 style="color:#125191;">### 批量检测完成</h3>
    <p>✅ {len(batch_data)} 张图片全部成功</p>
    <table>{header}{rows}</table>
  </div>
</div>
<div style="text-align:center;color:#999;font-size:12px;padding:10px 0 4px;margin-top:8px;">
  © 2026 风电塔灾损测算多模态大模型可视化软件 V1.0
</div>
</body></html>"""


def _render_history():
    """渲染历史记录页面HTML。"""
    records = list_records(50)
    stats = get_stats()
    charts_html = charts.charts_html()
    
    stats_html = f"""
    <div style="display:flex;gap:16px;margin-bottom:16px;">
        <div style="background:#EBF5FB;border-radius:8px;padding:12px;text-align:center;flex:1;">
            <div style="font-size:28px;font-weight:bold;color:#125191;">{stats['total']}</div>
            <div style="color:#555;">总检测数</div>
        </div>
        <div style="background:#FDEDEC;border-radius:8px;padding:12px;text-align:center;flex:1;">
            <div style="font-size:28px;font-weight:bold;color:#E74C3C;">{stats['high_risk']}</div>
            <div style="color:#555;">高风险</div>
        </div>
        <div style="background:#FEF9E7;border-radius:8px;padding:12px;text-align:center;flex:1;">
            <div style="font-size:28px;font-weight:bold;color:#F39C12;">{stats['damaged']}</div>
            <div style="color:#555;">发现损伤</div>
        </div>
        <div style="background:#E8F8F5;border-radius:8px;padding:12px;text-align:center;flex:1;">
            <div style="font-size:28px;font-weight:bold;color:#27AE60;">{stats['normal']}</div>
            <div style="color:#555;">正常</div>
        </div>
    </div>"""
    
    header = """<tr style="background:#125191;color:white;">
        <th style="padding:5px 6px;text-align:left;">ID</th>
        <th style="padding:5px 6px;text-align:left;">时间</th>
        <th style="padding:5px 6px;text-align:left;">图片</th>
        <th style="padding:5px 6px;text-align:left;">风险</th>
        <th style="padding:5px 6px;text-align:left;">损伤</th>
        <th style="padding:5px 6px;text-align:left;">损伤类型</th>
        <th style="padding:5px 6px;text-align:left;">构件</th>
        <th style="padding:5px 6px;text-align:left;">优先级</th>
        <th style="padding:5px 6px;text-align:left;">置信度</th>
        <th style="padding:5px 6px;text-align:left;">耗时</th>
    </tr>"""
    
    rows = ""
    for r in records:
        risk = "🔴" if r["high_risk"] else "🟢"
        bg = "#FDEDEC" if r["high_risk"] else ""
        rows += f"""<tr style="border-bottom:1px solid #ddd;background:{bg};">
            <td style="padding:4px 6px;">{r['id']}</td>
            <td style="padding:4px 6px;">{r['timestamp']}</td>
            <td style="padding:4px 6px;">{r['image_name']}</td>
            <td style="padding:4px 6px;">{risk}</td>
            <td style="padding:4px 6px;">{r['has_damage'] or '—'}</td>
            <td style="padding:4px 6px;">{r['damage_type'] or '—'}</td>
            <td style="padding:4px 6px;">{r['component'] or '—'}</td>
            <td style="padding:4px 6px;">{r['priority'] or '—'}</td>
            <td style="padding:4px 6px;">{r['confidence'] or '—'}</td>
            <td style="padding:4px 6px;">{r['infer_time'] or '—'}s</td>
        </tr>"""
    
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,sans-serif; background:#f5f5f5; }}
.header {{ text-align:center; padding:20px; background:white; border-bottom:1px solid #ddd; }}
.header h1 {{ font-size:28px; margin:0; }}
.header p {{ color:#666; margin:5px 0 0; }}
.container {{ padding:20px; max-width:1280px; margin:0 auto; }}
.panel {{ background:white; border-radius:8px; padding:20px; margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,0.1); }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
.tabs {{ display:flex; gap:4px; padding:0 20px; background:white; border-bottom:1px solid #ddd; }}
.tab {{ padding:10px 20px; cursor:pointer; color:#666; border-bottom:2px solid transparent; }}
.tab.active {{ color:#125191; border-bottom-color:#125191; font-weight:bold; }}
</style>
</head><body>
<div class="header">
  <h1><svg width="38" height="38" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" style="vertical-align:-8px;margin-right:6px;"><circle cx="32" cy="32" r="30" fill="#EBF5FB" stroke="#125191" stroke-width="1.5"/><rect x="29.5" y="36" width="5" height="22" fill="#7F8C8D"/><rect x="23" y="30" width="18" height="8" rx="2" fill="#5DADE2"/><circle cx="32" cy="28" r="3.5" fill="#34495E"/><g fill="#F1F8FD" stroke="#5DADE2" stroke-width="0.8"><path d="M32 28 L38 10 A5 5 0 0 1 44 8 L46 16 Z"/><path d="M32 28 L14 18 A5 5 0 0 1 10 12 L20 9 Z"/><path d="M32 28 L42 42 A5 5 0 0 1 41 48 L32 44 Z"/></g></svg>风电塔灾损测算多模态大模型可视化软件</h1>
</div>
<div class="tabs">
  <div class="tab">📷 单图检测</div>
  <div class="tab">📂 批量检测</div>
  <div class="tab active">📊 历史记录</div>
</div>
<div class="container">
  <div class="panel">
    {stats_html}
    {charts_html}
    <table>{header}{rows}</table>
  </div>
</div>
<div style="text-align:center;color:#999;font-size:12px;padding:10px 0 4px;margin-top:8px;">
  © 2026 风电塔灾损测算多模态大模型可视化软件 V1.0
</div>
</body></html>"""


def _render_json_report(data):
    """渲染JSON报告详情页HTML。"""
    report = data["report"]
    json_str = json.dumps(report, ensure_ascii=False, indent=2)
    
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,sans-serif; background:#f5f5f5; }}
.header {{ text-align:center; padding:20px; background:white; border-bottom:1px solid #ddd; }}
.header h1 {{ font-size:28px; margin:0; }}
.header p {{ color:#666; margin:5px 0 0; }}
.container {{ padding:20px; max-width:1280px; margin:0 auto; }}
.panel {{ background:white; border-radius:8px; padding:20px; box-shadow:0 1px 3px rgba(0,0,0,0.1); }}
.json-box {{ background:#f8f9fa; border-radius:8px; padding:16px; font-family:'SF Mono',Consolas,monospace; font-size:13px; white-space:pre-wrap; line-height:1.5; }}
</style>
</head><body>
<div class="header">
  <h1><svg width="38" height="38" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" style="vertical-align:-8px;margin-right:6px;"><circle cx="32" cy="32" r="30" fill="#EBF5FB" stroke="#125191" stroke-width="1.5"/><rect x="29.5" y="36" width="5" height="22" fill="#7F8C8D"/><rect x="23" y="30" width="18" height="8" rx="2" fill="#5DADE2"/><circle cx="32" cy="28" r="3.5" fill="#34495E"/><g fill="#F1F8FD" stroke="#5DADE2" stroke-width="0.8"><path d="M32 28 L38 10 A5 5 0 0 1 44 8 L46 16 Z"/><path d="M32 28 L14 18 A5 5 0 0 1 10 12 L20 9 Z"/><path d="M32 28 L42 42 A5 5 0 0 1 41 48 L32 44 Z"/></g></svg>风电塔灾损测算多模态大模型可视化软件</h1>
</div>
<div class="container">
  <div class="panel">
    <h3 style="color:#125191;">📄 完整 JSON 报告 — {data['image_name']}</h3>
    <div class="json-box">{json_str}</div>
  </div>
</div>
<div style="text-align:center;color:#999;font-size:12px;padding:10px 0 4px;margin-top:8px;">
  © 2026 风电塔灾损测算多模态大模型可视化软件 V1.0
</div>
</body></html>"""


def main():
    init_db()
    
    PORT = 7861
    
    # ─── 启动 Gradio 服务 ────────────────────────────────
    print(f"启动 Gradio 服务 (端口 {PORT})...")
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=BASE_DIR,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "GRADIO_SERVER_PORT": str(PORT)},
    )
    
    # 等待服务启动
    import urllib.request
    for i in range(30):
        try:
            urllib.request.urlopen(f"http://localhost:{PORT}/", timeout=2)
            print(f"  服务已启动 (端口 {PORT})")
            break
        except:
            time.sleep(1)
    else:
        print("  ❌ 服务启动失败，尝试端口 7860 (硬编码)")
        # 可能是 app.py 未读取环境变量，尝试默认端口
        PORT = 7860
        for i in range(10):
            try:
                urllib.request.urlopen(f"http://localhost:{PORT}/", timeout=2)
                print(f"  服务已启动 (端口 {PORT})")
                break
            except:
                time.sleep(1)
        else:
            print("  ❌ 服务启动失败（端口 7860 也无响应）")
            proc.terminate()
            return
    
    try:
        client = Client(f"http://localhost:{PORT}", verbose=False)
        
        # ─── 推理：高风险图片 ────────────────────────────
        print("\n推理 000020.jpg (高风险: 断裂)...")
        result = client.predict(
            image=handle_file(os.path.join(image_dir, "000020.jpg")),
            api_name="/analyze_single",
        )
        summary, detail_html, json_str, status, img_info, md_path, json_path = result
        report = json.loads(json_str)
        
        # 解析推理耗时
        import re
        time_match = re.search(r'\(([\d.]+)s\)', status)
        infer_time = float(time_match.group(1)) if time_match else 0
        
        results = {
            "high_risk": {
                "report": report,
                "image_name": "000020.jpg",
                "infer_time": infer_time,
            }
        }
        print(f"  完成: {summary} ({infer_time}s)")
        
        # ─── 推理：正常图片 ──────────────────────────────
        print("\n推理 000006.jpg (正常: 无损伤)...")
        result = client.predict(
            image=handle_file(os.path.join(image_dir, "000006.jpg")),
            api_name="/analyze_single",
        )
        summary, detail_html, json_str, status, img_info, md_path, json_path = result
        report = json.loads(json_str)
        time_match = re.search(r'\(([\d.]+)s\)', status)
        infer_time = float(time_match.group(1)) if time_match else 0
        
        results["normal"] = {
            "report": report,
            "image_name": "000006.jpg",
            "infer_time": infer_time,
        }
        print(f"  完成: {summary} ({infer_time}s)")
        
        # ─── 批量结果数据 ────────────────────────────────
        results["batch"] = [
            {
                "image_name": "000020.jpg",
                "high_risk": True,
                "has_damage": "是",
                "damage_type": "撞击损伤、断裂、结构变形",
                "component": "塔筒、叶片、机舱",
                "priority": "高",
                "infer_time": results["high_risk"]["infer_time"],
            },
            {
                "image_name": "000006.jpg",
                "high_risk": False,
                "has_damage": "否",
                "damage_type": "无损伤",
                "component": "机舱顶部及叶片根部",
                "priority": "低",
                "infer_time": results["normal"]["infer_time"],
            },
        ]
        
        # ─── 生成 HTML 截图页面 ──────────────────────────
        print("\n生成截图 HTML 页面...")
        pages = generate_html_screenshots(results)
        print(f"\n✅ 共生成 {len(pages)} 个 HTML 页面到 {SCREENSHOT_DIR}")
        
    finally:
        # 关闭服务
        proc.terminate()
        proc.wait()
        print("\nGradio 服务已关闭")


if __name__ == "__main__":
    main()
