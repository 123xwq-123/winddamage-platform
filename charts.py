"""
风电塔灾损测算软件 — 统计图表模块

基于历史检测记录生成统计图表（matplotlib），
输出为 base64 PNG 供前端展示。图表文字跟随 i18n.LANG（zh/en）。
"""

import os
import io
import base64
import sqlite3
from collections import Counter

import matplotlib
matplotlib.use("Agg")  # 无界面后端
import matplotlib.pyplot as plt
from matplotlib import font_manager

from history import DB_PATH
import i18n
from i18n import t as tr, tr_value

# ─── 中文字体（macOS 可用 PingFang/Heiti；Windows 中文标签需要）──
def _setup_font():
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "C:/Windows/Fonts/msyh.ttc",    # 微软雅黑（Windows）
        "C:/Windows/Fonts/simhei.ttf",  # 黑体（Windows）
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                font_manager.fontManager.addfont(path)
                name = font_manager.FontProperties(fname=path).get_name()
                plt.rcParams["font.family"] = [name, "sans-serif"]
                return
            except Exception:
                continue
    plt.rcParams["font.family"] = ["sans-serif"]


_setup_font()
plt.rcParams["axes.unicode_minus"] = False


def _fig_to_base64(fig):
    """将 matplotlib 图像转为 base64 PNG。"""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def _load_records():
    """从数据库读取全部检测记录。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT damage_type, priority, high_risk, has_damage FROM detections"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def damage_type_chart() -> str:
    """损伤类型分布饼图，返回 base64 PNG。"""
    records = _load_records()
    counter = Counter()
    for r in records:
        dt = (r.get("damage_type") or "—").strip()
        # 多类型以逗号分隔，逐项计入
        for item in dt.replace("、", ",").replace("，", ",").split(","):
            item = item.strip()
            if item and item != "—":
                counter[item] += 1

    if not counter:
        return ""

    # 取 Top-8，其余归入"其他"
    items = counter.most_common(8)
    others = counter.total() - sum(c for _, c in items) if hasattr(counter, "total") else 0
    labels = [tr_value(k) for k, _ in items]
    sizes = [c for _, c in items]
    if others > 0:
        labels.append(tr("chart_others"))
        sizes.append(others)

    colors = ["#5DADE2", "#F5B041", "#58D68D", "#EC7063",
              "#AF7AC5", "#5D6D7E", "#F7DC6F", "#48C9B0", "#B2BABB"]
    fig, ax = plt.subplots(figsize=(5.2, 3.8))
    result = ax.pie(
        sizes, labels=labels, colors=colors[:len(sizes)],
        autopct="%1.0f%%", startangle=90, pctdistance=0.78,
        textprops={"fontsize": 9},
    )
    # matplotlib 版本不同返回值个数不同：2 个（wedges, texts）或 3 个（+ autotexts）
    wedges = result[0]
    for w in wedges:
        w.set_edgecolor("white")
        w.set_linewidth(1.5)
    ax.set_title(tr("chart_damage_title"), fontsize=13, pad=12)
    return _fig_to_base64(fig)


def priority_chart() -> str:
    """巡检优先级分布柱状图，返回 base64 PNG。"""
    records = _load_records()
    order_zh = ["低", "中", "高"]
    order_en = ["Low", "Medium", "High"]
    order_disp = order_en if i18n.LANG == "en" else order_zh
    counts = {p: 0 for p in order_zh}
    for r in records:
        p = (r.get("priority") or "").strip()
        if p in counts:
            counts[p] += 1

    if sum(counts.values()) == 0:
        return ""

    colors = {"低": "#27AE60", "中": "#F39C12", "高": "#E74C3C"}
    fig, ax = plt.subplots(figsize=(5.2, 3.8))
    bars = ax.bar(order_disp, [counts[p] for p in order_zh],
                  color=[colors[p] for p in order_zh], width=0.5)
    for bar, v in zip(bars, [counts[p] for p in order_zh]):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.3,
                str(v), ha="center", fontsize=11)
    ax.set_ylabel(tr("chart_ylabel_count"), fontsize=11)
    ax.set_title(tr("chart_priority_title"), fontsize=13, pad=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_ylim(0, max(counts.values()) * 1.25 + 1)
    return _fig_to_base64(fig)


def trend_chart() -> str:
    """检测数量趋势图（按日期），返回 base64 PNG。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT date(timestamp) as d FROM detections ORDER BY timestamp"
    ).fetchall()
    conn.close()
    if not rows:
        return ""

    dates = [r["d"] for r in rows]
    counter = Counter(dates)
    xs = sorted(counter.keys())
    ys = [counter[x] for x in xs]

    fig, ax = plt.subplots(figsize=(5.2, 3.8))
    ax.plot(range(len(xs)), ys, marker="o", color="#125191",
            linewidth=2, markersize=5)
    ax.set_xticks(range(len(xs)))
    ax.set_xticklabels([x[5:] for x in xs], fontsize=8, rotation=30)
    ax.set_ylabel(tr("chart_ylabel_count"), fontsize=11)
    ax.set_title(tr("chart_trend_title"), fontsize=13, pad=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for i, v in enumerate(ys):
        ax.text(i, v + 0.2, str(v), ha="center", fontsize=9)
    return _fig_to_base64(fig)


def charts_html() -> str:
    """生成图表区 HTML（三图并排），无数据时返回占位。"""
    dmg = damage_type_chart()
    pri = priority_chart()
    trd = trend_chart()

    if not dmg and not pri and not trd:
        return (f"<p style='color:#999;text-align:center;padding:20px;'>"
                f"{tr('no_chart_data')}</p>")

    img_style = "width:100%;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1);"
    parts = ["<div style='display:flex;gap:14px;flex-wrap:wrap;margin-bottom:16px;'>"]
    for b64, title in [(dmg, tr("chart_damage_short")),
                       (pri, tr("chart_priority_short")),
                       (trd, tr("chart_trend_short"))]:
        if b64:
            parts.append(
                f"<div style='flex:1;min-width:240px;background:white;border-radius:8px;"
                f"padding:10px;'>"
                f"<img src='data:image/png;base64,{b64}' style='{img_style}' alt='{title}'/>"
                f"</div>"
            )
    parts.append("</div>")
    return "".join(parts)
