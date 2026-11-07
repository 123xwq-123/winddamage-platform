"""
风电塔灾损测算软件 — UI 组件与设计令牌模块

统一管理全局 CSS 令牌（颜色/字体/间距/圆角/阴影/动效）与
可复用 HTML 组件模板（风险徽章、摘要卡、折叠板块、空状态、状态条、统计卡、表格）。

设计规范详见 DEVELOPMENT_PLAN.md §5（设计系统 v2）。
所有颜色走 CSS 变量；风险语义色沿用 formatter.RISK_COLORS 原值，不改变数据含义。
"""

import html as _html

import i18n


# ══════════════════════════════════════════════════════════
#  设计令牌 + 全局样式（经 launch(css=...) 注入）
# ══════════════════════════════════════════════════════════

BASE_CSS = """
:root {
  /* 品牌色 */
  --brand-900:#0D3A66; --brand-700:#125191; --brand-500:#1E6BB8; --brand-100:#E3EEF8;
  /* 语义色（= formatter.RISK_COLORS，仅表达业务风险） */
  --danger:#E74C3C; --danger-deep:#C0392B; --danger-bg:#FDEDEB;
  --warn:#F39C12;   --warn-deep:#B9770E;   --warn-bg:#FEF5E7;
  --success:#27AE60;--success-deep:#1E8449;--success-bg:#EAF7F0;
  --info:#3498DB;   --info-bg:#EBF5FB;
  /* 中性色 */
  --text-1:#1F2933; --text-2:#52606D; --text-3:#9AA5B1;
  --border:#E4E7EB; --bg-page:#F5F7FA; --bg-card:#FFFFFF;
  --table-head:#F0F3F7;
  /* 阴影 / 焦点 / 遮罩 */
  --shadow-1:0 1px 3px rgba(31,41,51,.08);
  --shadow-2:0 4px 12px rgba(31,41,51,.12);
  --focus-ring:0 0 0 3px rgba(30,107,184,.22);
  --overlay:rgba(15,23,42,.45);
  /* 动效 */
  --duration-fast:120ms; --duration-normal:200ms;
  --ease-standard:cubic-bezier(.2,0,0,1);
}

/* ── 页面基调（风机场景背景 + 宋体/Times New Roman 字体）── */
:root {
  --bg-scene: url("/assets/bg_scene.svg");
  --font-stack: "Times New Roman", "SimSun", "宋体", "NSimSun", serif;
}
body, .gradio-container {
  background: var(--bg-page) var(--bg-scene) no-repeat fixed bottom center / 100% auto !important;
}
.gradio-container, .gradio-container button, .gradio-container input,
.gradio-container textarea, .gradio-container select,
.gradio-container .prose, body, body button, body input, body select, body textarea {
  font-family: var(--font-stack) !important;
}
.gradio-container { font-variant-numeric: tabular-nums; }

/* ── 隐藏 Gradio 自带页脚（API/品牌/设置入口，避免误触）── */
.gradio-container footer, .gradio-container .footer { display: none !important; }

/* ── 下拉选择框：字号随框宽自适应 + 更顺滑的展开/悬停 ── */
.gradio-container .dropdown input,
.gradio-container .dropdown button,
.gradio-container .wrap.default.dropdown,
.gradio-container ul.options,
.gradio-container ul.options li {
  font-size: clamp(13px, 0.35vw + 11.5px, 15px) !important;
}
.gradio-container ul.options {
  max-height: 300px; overflow-y: auto;
  animation: wd-dd-in var(--duration-fast) var(--ease-standard);
}
@keyframes wd-dd-in {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: none; }
}
.gradio-container ul.options li {
  padding: 8px 12px; cursor: pointer; user-select: none;
  transition: background 100ms linear;
}
.gradio-container ul.options li:hover,
.gradio-container ul.options li.selected { background: var(--brand-100); }

.main-title { text-align:center; padding:14px 0 6px; }
.main-title h1 { font-size:26px; color:var(--brand-700); margin-bottom:4px; letter-spacing:.5px; }
.title-icon { display:inline-flex; vertical-align:-7px; margin-right:8px; }
.footer-note { text-align:center; color:var(--text-3); font-size:12px; padding:12px 0 4px; margin-top:10px; }

/* ── 卡片 ─────────────────────────────────────────── */
.wd-card {
  background:var(--bg-card); border:1px solid var(--border); border-radius:8px;
  box-shadow:var(--shadow-1); padding:16px; margin-bottom:16px;
}

/* ── 结论摘要卡（结果页第一层） ────────────────────── */
.wd-summary {
  background:var(--bg-card); border:1px solid var(--border); border-radius:8px;
  box-shadow:var(--shadow-1); padding:16px 18px; margin-bottom:16px;
  border-left:4px solid var(--success);
}
.wd-summary.wd-tone-danger  { border-left-color:var(--danger);  background:var(--danger-bg); }
.wd-summary.wd-tone-warn    { border-left-color:var(--warn);    background:var(--warn-bg); }
.wd-summary.wd-tone-success { border-left-color:var(--success); background:var(--success-bg); }
.wd-summary-grid { display:flex; flex-wrap:wrap; gap:8px 32px; align-items:center; }
.wd-summary-item { min-width:120px; }
.wd-summary-item .wd-label { font-size:12px; color:var(--text-2); margin-bottom:2px; }
.wd-summary-item .wd-value { font-size:16px; font-weight:600; color:var(--text-1); }
.wd-summary-title { font-size:15px; font-weight:600; color:var(--text-1); margin-bottom:10px; }

/* ── 风险横幅（浅底 + 色条，不用高饱和红块） ───────── */
.wd-banner {
  display:flex; align-items:center; gap:10px;
  border-radius:8px; padding:12px 16px; margin-bottom:16px;
  background:var(--danger-bg); border-left:4px solid var(--danger);
}
.wd-banner .wd-banner-text { font-size:15px; font-weight:600; color:var(--danger-deep); }

/* ── 风险徽章（胶囊，浅底深字，文字+颜色双通道） ───── */
.wd-badge {
  display:inline-block; padding:2px 12px; border-radius:999px;
  font-size:13px; font-weight:600; line-height:20px; white-space:nowrap;
}
.wd-badge-danger  { background:var(--danger-bg);  color:var(--danger-deep); }
.wd-badge-warn    { background:var(--warn-bg);    color:var(--warn-deep); }
.wd-badge-success { background:var(--success-bg); color:var(--success-deep); }
.wd-badge-muted   { background:var(--table-head); color:var(--text-2); }

/* ── 折叠板块（详细报告分组） ──────────────────────── */
details.wd-sec {
  background:var(--bg-card); border:1px solid var(--border); border-radius:8px;
  box-shadow:var(--shadow-1); margin-bottom:12px; overflow:hidden;
}
details.wd-sec > summary {
  cursor:pointer; list-style:none; display:flex; align-items:center; gap:8px;
  padding:12px 16px; font-size:15px; font-weight:600; color:var(--brand-700);
  background:var(--table-head); border-bottom:1px solid transparent;
  transition:background var(--duration-fast) var(--ease-standard);
}
details.wd-sec > summary::-webkit-details-marker { display:none; }
details.wd-sec > summary::after {
  content:"▾"; margin-left:auto; color:var(--text-3); font-size:12px;
  transition:transform var(--duration-fast) var(--ease-standard);
}
details.wd-sec:not([open]) > summary:hover { background:var(--brand-100); }
details.wd-sec[open] > summary { border-bottom-color:var(--border); }
details.wd-sec[open] > summary::after { transform:rotate(180deg); }
details.wd-sec > .wd-sec-body { padding:12px 16px; }

/* ── 键值表格（报告字段） ──────────────────────────── */
table.wd-kv { width:100%; border-collapse:collapse; font-size:14px; }
table.wd-kv td { padding:7px 8px; vertical-align:top; border-bottom:1px solid var(--border); }
table.wd-kv tr:last-child td { border-bottom:none; }
table.wd-kv td.wd-kv-label { width:150px; color:var(--text-2); white-space:nowrap; }
table.wd-kv td.wd-kv-value { color:var(--text-1); font-weight:500; word-break:break-word; }

/* ── 数据表格（历史/批量） ─────────────────────────── */
.table-wrap { overflow-x:auto; border:1px solid var(--border); border-radius:8px;
  box-shadow:var(--shadow-1); background:var(--bg-card); }
table.wd-table { width:100%; border-collapse:collapse; font-size:13px; }
table.wd-table th {
  background:var(--table-head); color:var(--text-2); font-weight:600;
  padding:9px 10px; text-align:left; white-space:nowrap;
  border-bottom:1px solid var(--border);
  position:sticky; top:0;
}
table.wd-table td { padding:7px 10px; border-bottom:1px solid var(--border); color:var(--text-1); }
table.wd-table tbody tr:nth-child(even) { background:var(--bg-page); }
table.wd-table tbody tr:hover { background:var(--brand-100); }
table.wd-table tr.wd-row-danger { background:var(--danger-bg); }
table.wd-table tr.wd-row-danger:hover { background:#FBDDD9; }
table.wd-table td.wd-num { font-variant-numeric:tabular-nums; text-align:right; }

/* ── 统计卡 ────────────────────────────────────────── */
.wd-stats { display:flex; gap:16px; flex-wrap:wrap; margin-bottom:16px; }
.wd-stat {
  flex:1; min-width:140px; background:var(--bg-card); border:1px solid var(--border);
  border-radius:8px; box-shadow:var(--shadow-1); padding:14px; text-align:center;
  border-top:3px solid var(--brand-500);
}
.wd-stat .wd-stat-num { font-size:28px; font-weight:700; color:var(--brand-700);
  font-variant-numeric:tabular-nums; }
.wd-stat .wd-stat-label { font-size:13px; color:var(--text-2); margin-top:2px; }
.wd-stat.wd-tone-danger  { border-top-color:var(--danger); }
.wd-stat.wd-tone-danger  .wd-stat-num { color:var(--danger-deep); }
.wd-stat.wd-tone-warn    { border-top-color:var(--warn); }
.wd-stat.wd-tone-warn    .wd-stat-num { color:var(--warn-deep); }
.wd-stat.wd-tone-success { border-top-color:var(--success); }
.wd-stat.wd-tone-success .wd-stat-num { color:var(--success-deep); }

/* ── 空状态 ────────────────────────────────────────── */
.wd-empty {
  border:1.5px dashed var(--border); border-radius:8px;
  padding:44px 24px; text-align:center; background:var(--bg-card);
}
.wd-empty .wd-empty-title { font-size:17px; color:var(--text-1); font-weight:600; margin:10px 0 6px; }
.wd-empty .wd-empty-desc  { font-size:13px; color:var(--text-3); }

/* ── 状态条 ────────────────────────────────────────── */
.wd-status {
  border-radius:8px; padding:10px 14px; font-size:14px; margin-bottom:12px;
  border-left:4px solid var(--info); background:var(--info-bg); color:var(--text-1);
}
.wd-status.wd-status-success { border-left-color:var(--success); background:var(--success-bg); }
.wd-status.wd-status-error   { border-left-color:var(--danger);  background:var(--danger-bg);  color:var(--danger-deep); }
.wd-status.wd-status-warn    { border-left-color:var(--warn);    background:var(--warn-bg);    color:var(--warn-deep); }

/* ── 图表卡 ────────────────────────────────────────── */
.wd-chart-card { flex:1; min-width:240px; background:var(--bg-card);
  border:1px solid var(--border); border-radius:8px; box-shadow:var(--shadow-1); padding:10px; }
.wd-charts { display:flex; gap:14px; flex-wrap:wrap; margin-bottom:16px; }
.wd-chart-card img { width:100%; border-radius:6px; display:block; }

/* ── 危险按钮（清空/删除类） ───────────────────────── */
button.wd-btn-danger {
  background:var(--bg-card) !important; color:var(--danger-deep) !important;
  border:1px solid var(--danger) !important;
}
button.wd-btn-danger:hover { background:var(--danger-bg) !important; }

/* ── 筛选工具栏 / 分页 ─────────────────────────────── */
.wd-filterbar { display:flex; flex-wrap:wrap; gap:8px 12px; align-items:flex-end;
  background:var(--bg-card); border:1px solid var(--border); border-radius:8px;
  box-shadow:var(--shadow-1); padding:12px 14px; margin-bottom:14px; }
.wd-filterbar .wd-fitem { display:flex; flex-direction:column; gap:4px; min-width:130px; }
.wd-filterbar .wd-flabel { font-size:12px; color:var(--text-2); }
.wd-filterbar .wd-finput { border:1px solid var(--border); border-radius:6px;
  padding:6px 10px; font-size:14px; background:var(--bg-card); color:var(--text-1); }
.wd-filterbar .wd-finput:focus { outline:none; box-shadow:var(--focus-ring); border-color:var(--brand-500); }
.wd-total-count { font-size:13px; color:var(--text-2); margin-left:auto; align-self:center; }
.wd-pager { display:flex; align-items:center; gap:12px; justify-content:center;
  padding:12px 0 4px; }
.wd-pager .wd-page-btn { border:1px solid var(--border); background:var(--bg-card);
  color:var(--text-1); border-radius:6px; padding:6px 16px; font-size:13px; cursor:pointer; }
.wd-pager .wd-page-btn:disabled { color:var(--text-3); cursor:not-allowed; }
.wd-pager .wd-page-info { font-size:13px; color:var(--text-2); font-variant-numeric:tabular-nums; }

/* ── 详情页头部 / 返回链接 ─────────────────────────── */
.wd-page-head { max-width:var(--reading-max, 880px); margin:0 auto; padding:20px 16px 0; }
.wd-backlink { font-size:14px; color:var(--brand-500); text-decoration:none; }
.wd-backlink:hover { text-decoration:underline; }

/* ── 桌面 / 移动双渲染切换（服务端渲染两套，CSS 切换显示） ── */
.wd-mobile-only { display:none; }
@media (max-width: 767px) {
  .wd-desktop-only { display:none; }
  .wd-mobile-only { display:block; }
}

/* ── 移动端历史卡片 ────────────────────────────────── */
.wd-mcard { background:var(--bg-card); border:1px solid var(--border); border-radius:8px;
  box-shadow:var(--shadow-1); padding:12px 14px; margin-bottom:10px; }
.wd-mcard.wd-row-danger { background:var(--danger-bg); }
.wd-mcard .wd-mcard-head { display:flex; align-items:center; gap:8px; margin-bottom:4px; }
.wd-mcard .wd-mcard-name { font-size:14px; color:var(--text-2); word-break:break-all; }
.wd-mcard .wd-mcard-meta { font-size:12px; color:var(--text-3); margin:6px 0 10px;
  font-variant-numeric:tabular-nums; }
.wd-mcard .wd-mcard-actions { display:flex; gap:8px; }
.wd-mcard .wd-mcard-actions a { flex:1; text-align:center; border:1px solid var(--border);
  border-radius:6px; padding:8px 0; font-size:13px; color:var(--brand-700);
  text-decoration:none; background:var(--bg-card); }
.wd-mcard .wd-mcard-actions a.wd-mcard-primary { background:var(--brand-700);
  color:#fff; border-color:var(--brand-700); }

/* ── 响应式 ────────────────────────────────────────── */
@media (max-width: 767px) {
  .main-title h1 { font-size:20px; }
  .wd-summary-grid { flex-direction:column; align-items:flex-start; }
  .wd-stat { min-width:calc(50% - 8px); }
}

/* ── 动效降级 ──────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  * { transition:none !important; animation:none !important; }
}

/* ── 可访问性（§6.4 子集）：键盘焦点可见，鼠标点击不高亮 ── */
:focus { outline:none; }
:focus-visible { outline:2px solid var(--brand-500); outline-offset:2px;
  border-radius:4px; }
.wd-btn:focus-visible, button:focus-visible, a:focus-visible {
  outline:2px solid var(--brand-500); outline-offset:2px; }

/* ── 历史记录抽屉快捷预览（右侧滑出，iframe 加载独立详情页）── */
.wd-drawer-mask { position:fixed; inset:0; background:var(--overlay); z-index:9998;
  opacity:0; pointer-events:none;
  transition:opacity var(--duration-normal) var(--ease-standard); }
.wd-drawer-mask.wd-open { opacity:1; pointer-events:auto; }
.wd-drawer { position:fixed; top:0; right:0; height:100vh; width:min(600px,94vw);
  background:var(--bg-card); box-shadow:var(--shadow-2); z-index:9999;
  display:flex; flex-direction:column;
  transform:translateX(102%);
  transition:transform var(--duration-normal) var(--ease-standard); }
.wd-drawer.wd-open { transform:none; }
.wd-drawer-head { display:flex; align-items:center; gap:12px; padding:12px 16px;
  border-bottom:1px solid var(--border); background:var(--table-head); }
.wd-drawer-head .wd-drawer-title { flex:1; font-size:15px; font-weight:600;
  color:var(--brand-700); }
.wd-drawer-head a { font-size:13px; color:var(--brand-500); font-weight:600;
  text-decoration:none; white-space:nowrap; }
.wd-drawer-head a:hover { text-decoration:underline; }
.wd-drawer-head button { font-size:13px; padding:5px 14px; cursor:pointer;
  border:1px solid var(--border); border-radius:6px; background:var(--bg-card);
  color:var(--text-1); }
.wd-drawer-head button:hover { background:var(--brand-100); }
.wd-drawer-body { flex:1; overflow-y:auto; padding:14px 16px; }
.wd-drawer-body iframe { width:100%; height:100%; min-height:calc(100vh - 70px);
  border:none; display:block; }
.wd-preview-link { color:var(--brand-500); cursor:pointer; user-select:none;
  font-size:12px; margin-left:8px; text-decoration:underline; white-space:nowrap; }
.wd-preview-link:hover { color:var(--brand-700); }
.wd-mcard-actions .wd-preview-link { flex:0 0 auto; margin-left:0; margin-right:8px;
  text-align:center; border:1px solid var(--border); border-radius:6px;
  padding:8px 12px; color:var(--brand-700); text-decoration:none;
  background:var(--bg-card); display:inline-block; }

/* ── 批量进度日志（可滚动，column-reverse 使新内容保持在视野底部）── */
.wd-progress-box { max-height:230px; overflow-y:auto; display:flex;
  flex-direction:column-reverse; border:1px solid var(--border); border-radius:8px;
  background:var(--table-head); }
.wd-progress-box pre.wd-progress-log { margin:0; padding:10px 12px;
  font-size:13px; line-height:1.7; white-space:pre-wrap; word-break:break-all;
  font-family:var(--font-stack) !important; color:var(--text-1); }

/* ── 记录巡检图像卡（历史详情 / 独立页 / 抽屉预览共用）────── */
.wd-img-card { background:var(--bg-card); border:1px solid var(--border);
  border-radius:8px; box-shadow:var(--shadow-1); padding:10px 12px; margin-bottom:16px; }
.wd-img-card .wd-img-title { font-size:13px; color:var(--text-2); margin-bottom:8px; }
.wd-img-card img { width:100%; height:auto; display:block; border-radius:6px; }

/* ── 认证页（登录/注册/初始化，§10）────────────────── */
.wd-auth-wrap { min-height:calc(100vh - 40px); display:flex; align-items:center;
  justify-content:center; padding:20px 16px; }
.wd-auth-card { width:100%; max-width:400px; background:var(--bg-card);
  border:1px solid var(--border); border-radius:12px; box-shadow:var(--shadow-2);
  padding:28px 26px 24px; }
.wd-auth-card h1 { font-size:20px; margin:0 0 4px; color:var(--text-1);
  display:flex; align-items:center; gap:8px; }
.wd-auth-sub { font-size:13px; color:var(--text-3); margin:0 0 18px; line-height:1.5; }
.wd-field { margin-bottom:14px; }
.wd-field label { display:block; font-size:13px; color:var(--text-2);
  font-weight:600; margin-bottom:5px; }
.wd-field input[type="text"], .wd-field input[type="password"] {
  width:100%; box-sizing:border-box; padding:10px 12px; font-size:14px;
  border:1px solid var(--border); border-radius:8px; background:#fff;
  color:var(--text-1); }
.wd-field input:focus { outline:2px solid var(--brand-500); outline-offset:1px;
  border-color:var(--brand-500); }
.wd-field-row { display:flex; align-items:center; justify-content:space-between;
  margin-top:6px; font-size:12px; color:var(--text-3); }
.wd-field-row label { font-weight:400; display:flex; align-items:center; gap:5px;
  margin:0; cursor:pointer; }
.wd-form-error { color:#C0392B; font-size:13px; margin:2px 0 10px; line-height:1.45; }
.wd-pw-rules { list-style:none; margin:8px 0 0; padding:0; font-size:12px; }
.wd-pw-rules li { color:var(--text-3); margin-bottom:3px; }
.wd-pw-rules li::before { content:"○ "; }
.wd-pw-rules li.wd-rule-ok { color:#1E8449; }
.wd-pw-rules li.wd-rule-ok::before { content:"● "; }
.wd-auth-alt { margin-top:16px; padding-top:14px; border-top:1px solid var(--border);
  font-size:13px; color:var(--text-3); }
.wd-auth-alt a { color:var(--brand-500); font-weight:600; text-decoration:none; }
.wd-auth-alt a:hover { text-decoration:underline; }
.wd-btn-primary-block { width:100%; padding:11px 0; font-size:15px; font-weight:600;
  background:var(--brand-700); color:#fff; border:none; border-radius:8px;
  cursor:pointer; margin-top:6px; }
.wd-btn-primary-block:hover { background:var(--brand-500); }
.wd-auth-banner { max-width:400px; margin:0 auto 12px; border-radius:8px;
  padding:10px 14px; font-size:13px; line-height:1.5; }
.wd-auth-banner.wd-banner-warn { background:#FEF5E7; border:1px solid #F5B041; color:#7E5109; }
.wd-auth-banner.wd-banner-error { background:var(--danger-bg, #FDEDEC); border:1px solid #EC7063; color:#943126; }

/* ── 用户管理表 ────────────────────────────────────── */
.wd-users-wrap { max-width:var(--reading-max, 880px); margin:0 auto; padding:24px 16px; }
.wd-users-actions { display:flex; gap:6px; flex-wrap:wrap; }
.wd-users-actions form { display:inline-flex; gap:6px; align-items:center; }
.wd-users-actions button, .wd-users-actions input[type="submit"] {
  font-size:12px; padding:5px 10px; border:1px solid var(--border); border-radius:6px;
  background:var(--bg-card); color:var(--brand-700); cursor:pointer; }
.wd-users-actions .wd-u-danger { color:#C0392B; border-color:#EC7063; }
.wd-users-actions input[type="password"] { padding:4px 8px; font-size:12px;
  border:1px solid var(--border); border-radius:6px; width:170px; }

/* ── 顶栏用户徽章 ──────────────────────────────────── */
.wd-user-badge { display:flex; gap:12px; align-items:center; justify-content:flex-end;
  max-width:1280px; margin:0 auto; padding:8px 16px 0; font-size:13px; min-height:22px; }
.wd-user-badge:empty { display:none; }
.wd-user-badge a { color:var(--brand-500); font-weight:600; text-decoration:none; }
.wd-user-badge a:hover { text-decoration:underline; }
.wd-user-badge .wd-ub-name { font-weight:600; color:var(--text-2);
  max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
"""


# ══════════════════════════════════════════════════════════
#  HTML 组件模板
# ══════════════════════════════════════════════════════════

def esc(text) -> str:
    """HTML 转义（所有用户/模型可控内容必须经过此函数再入模板）。"""
    return _html.escape(str(text), quote=True)


def risk_badge(value: str, tone: str = "") -> str:
    """风险徽章：胶囊形，浅色语义底 + 深色文字（文字+颜色双通道）。

    tone: "danger" / "warn" / "success" / "muted"；空串时按 value 自动判断。
    """
    if not value:
        return ""
    if not tone:
        tone = tone_for_value(value)
    return f'<span class="wd-badge wd-badge-{tone}">{esc(value)}</span>'


# 与 formatter.RISK_COLORS 一致的语义映射（展示值，zh/en 都覆盖）
_TONE_BY_VALUE = {
    # 高风险类
    "高": "danger", "High": "danger", "是": "danger", "Yes": "danger",
    "严重": "danger", "Severe": "danger", "紧急": "danger", "Urgent": "danger",
    # 中等
    "中": "warn", "Medium": "warn", "一般": "warn", "Moderate": "warn",
    # 安全类
    "低": "success", "Low": "success", "否": "success", "No": "success",
    "无": "success", "None": "success", "正常": "success", "Normal": "success",
}


def tone_for_value(value: str) -> str:
    return _TONE_BY_VALUE.get(str(value).strip(), "muted")


def status_banner(text: str, kind: str = "info") -> str:
    """状态条。kind: info / success / error / warn"""
    return f'<div class="wd-status wd-status-{esc(kind)}">{text}</div>'


def empty_state(title: str, desc: str = "", icon_svg: str = "") -> str:
    """空状态：图标 + 标题 + 一句说明。"""
    icon = f"<div>{icon_svg}</div>" if icon_svg else ""
    desc_html = f'<div class="wd-empty-desc">{desc}</div>' if desc else ""
    return (
        f'<div class="wd-empty">{icon}'
        f'<div class="wd-empty-title">{title}</div>{desc_html}</div>'
    )


def stat_card(num, label: str, tone: str = "") -> str:
    """统计卡。tone: ""(品牌蓝) / danger / warn / success"""
    tone_cls = f" wd-tone-{tone}" if tone else ""
    return (
        f'<div class="wd-stat{tone_cls}">'
        f'<div class="wd-stat-num">{esc(num)}</div>'
        f'<div class="wd-stat-label">{esc(label)}</div></div>'
    )


def summary_card(items, tone: str = "success", title: str = "") -> str:
    """结论摘要卡（结果页第一层）。

    items: [(label, value_html), ...]；tone: danger / warn / success
    """
    tone_cls = f" wd-tone-{tone}" if tone != "muted" else ""
    title_html = f'<div class="wd-summary-title">{title}</div>' if title else ""
    cells = "".join(
        f'<div class="wd-summary-item"><div class="wd-label">{esc(label)}</div>'
        f'<div class="wd-value">{value}</div></div>'
        for label, value in items
    )
    return (
        f'<div class="wd-summary{tone_cls}">{title_html}'
        f'<div class="wd-summary-grid">{cells}</div></div>'
    )


def risk_banner(text: str) -> str:
    """高风险横幅：浅底 + 左侧色条 + 图标 + 明确文字（不用高饱和红块）。"""
    return (
        '<div class="wd-banner">'
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#C0392B" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86'
        'a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/>'
        '<line x1="12" y1="17" x2="12.01" y2="17"/></svg>'
        f'<span class="wd-banner-text">{text}</span></div>'
    )


def sec_details(icon: str, title: str, body: str, open_: bool = False) -> str:
    """折叠报告板块（原生 <details>，无需 JS）。"""
    open_attr = " open" if open_ else ""
    return (
        f'<details class="wd-sec"{open_attr}>'
        f"<summary><span>{icon}</span><span>{esc(title)}</span></summary>"
        f'<div class="wd-sec-body">{body}</div></details>'
    )


def kv_rows(fields) -> str:
    """键值行表格。fields: [(label, value_html, is_risk), ...]"""
    rows = []
    for label, value, is_risk in fields:
        weight = "" if is_risk else "font-weight:500;"
        rows.append(
            "<tr>"
            f'<td class="wd-kv-label">{esc(label)}</td>'
            f'<td class="wd-kv-value" style="{weight}">{value}</td>'
            "</tr>"
        )
    return f'<table class="wd-kv">{"".join(rows)}</table>'


def data_table(headers, rows_html: str) -> str:
    """标准数据表格（浅色 sticky 表头）。rows_html 为已构建的 <tr>... 串。"""
    ths = "".join(f"<th>{esc(h)}</th>" for h in headers)
    return (
        f'<div class="table-wrap"><table class="wd-table">'
        f"<thead><tr>{ths}</tr></thead><tbody>{rows_html}</tbody></table></div>"
    )


def mobile_history_card(badge_html: str, image_name: str, meta_html: str,
                        detail_url: str, detail_label: str,
                        danger: bool = False,
                        preview_html: str = "") -> str:
    """移动端历史记录卡片（§7：<768px 替代表格）。preview_html 为抽屉预览触发器。"""
    cls = " wd-row-danger" if danger else ""
    return (
        f'<div class="wd-mcard{cls}">'
        f'<div class="wd-mcard-head">{badge_html}</div>'
        f'<div class="wd-mcard-name">{esc(image_name)}</div>'
        f'<div class="wd-mcard-meta">{meta_html}</div>'
        f'<div class="wd-mcard-actions">'
        f'{preview_html}'
        f'<a class="wd-mcard-primary" href="{esc(detail_url)}">{esc(detail_label)}</a>'
        f"</div></div>"
    )


def page_shell(title: str, body_html: str, lang: str = None) -> str:
    """独立页（FastAPI 渲染）的完整 HTML 外壳：内嵌设计令牌，viewport 齐全。"""
    lang_attr = esc(lang or i18n.LANG)
    return f"""<!doctype html>
<html lang="{lang_attr}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>
{BASE_CSS}
body {{ margin:0; }}
</style>
</head>
<body>
{body_html}
</body>
</html>"""
