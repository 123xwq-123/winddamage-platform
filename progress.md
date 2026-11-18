# Progress

- Investigated runtime logs and single-image event bindings.
- Reproduced the backend failure from the existing session logs.
- Identified the clear callback's empty-string image output as the root cause.
- Added `test_clear_action_resets_filepath_image_with_none`; observed expected failure.
- Changed the clear callback's image value from `""` to `None`; focused test passed.
- Full suite: 64 tests passed.
- UI build: `UI_BUILD_OK`.
- Restarted service as PID 46040.
- Authenticated Gradio integration flow: first image analyzed, clear returned `None`, second image analyzed successfully.
- Post-flow runtime log contains no traceback or permission error.
- Examples/export layout (2026-11-16):
  - CDP probe confirmed real DOM `.wd-input-col .gallery > button.gallery-item`; TDD RED then GREEN.
  - `examples_per_page=10` explicit; `.gallery` grid `repeat(auto-fill, 80px)`, thumbs 80x80 `object-fit:cover`.
  - Export buttons: `gr.Row(elem_classes=["wd-export-row"])` vertical; `.wd-export-btn { width:100% }`.
  - First attempt (5x84px fixed columns + horizontal flex buttons) failed visually: columns 4-5 clipped
    in 20% column, buttons 76px wide with text clipped (scrollW 118 > 76). Fixed with auto-fill + vertical row.
  - Final CDP verification: 10 thumbs 80x80, no horizontal overflow (scrollW 259 = clientW 259),
    three buttons equal 259x46 with no clipping, Pages 1/2. Screenshots confirmed.
  - Full suite: 66 tests OK; UI_BUILD_OK; `git diff --check` clean (LF/CRLF warnings only).
  - Service restarted as PID 47580; page opened at `http://localhost:7860/?ui=final-v4` for user review.
- Theme system (2026-11-16, milestone 1 of 3):
  - Researched NN/g heuristics + Refactoring UI color methodology; produced 5 design proposals (A-E).
  - Tokenized all hardcoded surfaces (card tint, turbine sky, field bg, danger-row hover,
    page veils) in ui_components.py BASE_CSS.
  - Added 4 skin token blocks (`[data-wd-theme="night|glass|bento|hmi"]`); default = clear.
    Night remaps Gradio component CSS vars for full dark UI without ?__theme.
    Glass paints aurora radial gradients on body::after (above the bg iframe, z-index -1)
    and uses translucent cards + backdrop-blur; popover/drawer forced opaque (0.96).
  - Settings popover gained "界面风格" row (5 buttons, data-wd-skin), instant switching via
    html[data-wd-theme], persisted in localStorage('wd_skin'); zh/en labels added.
  - CDP verified: all 5 skins switch live, tokens resolve correctly, skin survives reload.
  - Fixed during verification: night air-veil too light (0.28→0.62-0.80), glass popover
    translucency, glass aurora hidden behind bg iframe.
  - Full suite: 71 tests OK (5 new theme contracts); UI_BUILD_OK; git diff --check clean.
  - Remaining milestones: 2) per-skin component refinements (Bento spacing/type scale,
    HMI shape-coded states, mono digits), 3) 3D viewer + dynamic bg per-skin adaptation.
- Theme refinements (2026-11-16, milestones 2+3 complete):
  - User screenshot showed dark-on-dark text in night skin; probe proved fresh browsers
    render #E5EDF7 — root cause was browser cache of old base.css (max-age=3600).
    Fixed: /wd-assets/base.css now served with Cache-Control: no-cache.
  - Night hardened: prose/h1-h6/p/span/li, html-container (+div/span/td/th), label,
    block-info, details summary, wd-empty all forced to light via !important.
  - Milestone 2: HMI badges shape-coded (▲ danger / ■ warn / ● success, .82em ::before),
    rounded buttons; Bento type scale (h3 20px/800, stat-num 32px/800, summary 18px/700);
    glass aurora animated via @keyframes wd-aurora (26s ease-in-out alternate).
  - Milestone 3: turbine viewer theme-linked. Parent postTheme() in applySkin posts
    {wdTheme:name} to .wd-turbine-frame iframe (+1500ms/5000ms retries for late iframes);
    viewer keeps THEME palette {sky,fog,grass,blades,vt} per skin, applyTheme() swaps
    scene.background/fog/grass materials and toggles html[data-vt]; night HUD dark CSS
    ([data-vt="night"]) for pills/legend/buttons; init reads parent data-wd-theme.
  - CDP verified: night right-col prose/h3/html-container #E5EDF7; viewer bodyBg
    #0E1B33 + dark scene gradient + light pill; glass aurora anim 26s; viewer resets
    when switching away from night.
  - Full suite: 77 tests OK (6 new refinement contracts); UI_BUILD_OK; git diff --check
    clean. Service restarted PID 29688.
- Night button contrast hardening (2026-11-16, user screenshot feedback):
  - Probe found: Gradio buttons use their own color var chain (.dark class) — remapping
    --button-secondary-text-color alone was insufficient. Fixed: night rules force
    button/button span color var(--text-1) !important, button.primary → #FFFFFF,
    button.lg border var(--border), links brand-500.
  - Popover active buttons (wd-active on bright night brand-500 #38BDF8) had 1.8:1 →
    forced dark text #0B1220 (now 8.7:1).
  - "图片信息" chip = span[data-testid="block-info"] with --block-title-background-fill
    light blue → remapped var to #18233A + forced [data-testid="block-info"] /
    [data-testid="block-label"] chip background var(--table-head) (now ~13:1).
  - CDP scan result: BAD_BUTTONS=[], LOW_CONTRAST=[] (all page buttons ≥3:1, most 13+).
  - Full suite: 78 tests OK (added test_night_buttons_keep_readable_text); UI_BUILD_OK;
    service restarted. Pending: user asked for "参考1" version — message truncated,
    awaiting clarification (参考1.gif exists in project root).
- HUD skin (sixth skin "hud" / "Deep-Space HUD", 2026-11-16, from 参考1.gif + 参考2.gif):
  - Fused visual language: deep-space navy page + tech grid overlay + cyan glow
    (参考1: panel L-corner brackets, cyan glowing outlines, glow primary button;
     参考2: translucent blue panels, left accent-bar titles, capsule outline buttons).
  - New token block [data-wd-theme="hud"]: --bg-page #071426, --bg-card #0C2138,
    --brand-500 #06B6D4, text #DCEBFA/#9FBEDA/#6684A3, cyan border rgba(103,232,249,.26).
  - Decor: .wd-workbench-col ::before/::after corner brackets (2px #06B6D4, top/left
    at 0 because panel overflow:hidden clips -1px), h3 left accent bar + letter-spacing
    + gradient underline (selector must be ".wd-workbench-col h3" - Gradio nests h3
    at div.block > ... > .prose > span.md, NOT direct child), body::after grid at
    rgba(103,232,249,.08) (base rule is z-index:-1, under content), glowing primary
    button, zebra table rows, dark settings popover (rides var(--bg-card)).
  - Dark-skin contrast hardening identical to night (prose/buttons/chips !important).
  - viewer THEME hud entry {sky:0x123055,fog:0x1b3d63,grass:0x2d5c42,blades:0x24523a,vt:night}.
  - app.py SKINS array + sixth button data-wd-skin="hud"; i18n skin_hud zh/en.
  - TDD: TestHudSkin 7 contracts RED->GREEN; full suite 85 tests OK; UI_BUILD_OK.
  - CDP verified: attr=hud, tokens resolve, bracket 2px #06B6D4, h3 border 3px,
    viewer data-vt=night + bodyBg rgb(14,27,51), localStorage stored=hud.
  - OPEN ISSUE: under hud the 3D canvas is INVISIBLE on screen (mid col black) while
    drawImage pixel reads prove the canvas backdrop is correct (white turbine center,
    hud sky #123055 corner); switching viewer scene night<->hud changes pixels live.
    Ruled out: settings overlay (closed popover - still black), backdrop-filter,
    corner brackets, body::after grid (reverse-added all of these on night skin and
    turbine stayed visible; headed Chrome reproduces, so not a screenshot artifact).
    Remaining suspects: [data-wd-theme="hud"] gradio var remap / !important hardening
    blocks / token block; CSSOM selectorText group-disable bisect running.
- HUD canvas bug root-caused to a single rule (2026-11-16, CSSOM bisect):
  - Method: CSSOM rule.selectorText rewriting on live page ([data-wd-theme="hud"]
    rules grouped: tokens/grid/gradiovars/harden/decor), cumulative disable then
    per-rule re-enable with screenshots; settings popover closed to kill overlay.
  - Result: decor group is the culprit; per-rule isolation => ONLY the h3 accent-bar
    rule "[data-wd-theme="hud"] .wd-workbench-col h3" kills the on-screen WebGL
    canvas (backing store stays correct; drawImage still shows turbine+sky).
  - Reversible: disable h3 rule => canvas reappears; noop style mutations do NOT
    revive it, so it is rule-content-driven, not mutation/timing-driven.
  - Variants that do NOT help: background as longhand, dropping background,
    dropping letter-spacing, iframe translateZ(0) - all still black.
  - Working hypothesis: the ONLY vertical-layout change in the rule is
    padding-bottom:6px (taller h3 => mid column reflows/scrollbar appears =>
    iframe layer breaks in headless/SwiftShader compositor). Testing
    no-padding-bottom / negative-margin / viewer-height-compensation variants.
- HUD canvas bug FIXED (2026-11-16):
  - Root cause: h3 rule padding-bottom:6px made panel titles 6px taller => mid-column
    reflow changed the 3D iframe's on-screen geometry => Chromium compositor dropped
    the iframe's WebGL layer (canvas backing store stayed correct, screen black).
    Confirmed: no-padding-bottom variant and viewer-height-compensated variant both
    keep the turbine visible; negative-margin compensation does NOT (margin collapse).
  - Fix: removed padding-bottom:6px from [data-wd-theme="hud"] .wd-workbench-col h3;
    accent bar + letterspacing + gradient underline unchanged (underline now sits at
    text bottom). Comment in BASE_CSS documents the vertical-layout prohibition.
  - Verified: TestHudSkin + full suite 85 OK; UI_BUILD_OK; service restarted (PID 10728);
    CDP attr/tokens/brackets/h3/viewer-link/persistence all pass; headless AND headed
    Chrome screenshots show turbine rendering in hud scene palette.
  - Deliverables: 预览_深空HUD.png (clean), 预览_深空HUD_设置面板.png (skin picker
    showing sixth button "深空HUD" active). Access: 设置 -> 界面风格 -> 深空HUD
    (localStorage wd_skin=hud persists across reloads).

## UI Upgrade: /screen 大屏五页面（feature/ui-upgrade 分支，2026-11-16）

- Task 1-8 ALL DONE and committed on feature/ui-upgrade:
  - c29ea93 Task 1 路由骨架; 99ffa78 Task 2 样式+登录; 4d165f7 Task 3 3D 风场;
    f391c3c Task 4 主页(home.html/js + analyze); 5c40330 Task 5 历史(records API+页面);
    ed8802a Task 6 批量(batch API+客户端CSV); 959f4c7 Task 7 账户+导出; a016498 Task 8 中间件修复+验收截图.
- Full suite 110 tests OK (85 old + 25 new in tests/test_screen.py), EXIT=0.
- Six acceptance screenshots in OUTPUT/: 验收_新版主页/新版登录/批量/历史/账户/旧版回归.png.
- Key fixes found during smoke testing:
  1. Bare /screen must register as @router.get("") (registered "/" became /screen/ and was
     swallowed by Gradio's / mount => 404).
  2. Middleware redirect loop: unauthenticated /screen/login redirected to itself; also
     /screen-assets was intercepted (login page CSS 302). Both now bypassed with tests.
  3. farm_viewer.html vendor imports must use absolute /wd-assets/vendor/three/... (relative
     ../vendor resolved to /vendor from /screen-assets/ => 404, blank 3D scene).
- CDP screenshot workflow: kill leftover cdp-profile Chrome first (stale instance on :9223
  serves old profile => wrong screenshots); PowerShell drops empty-string args (pass "x").
- 7871 test service stopped; user's own 7860 service (PID 10728) untouched.
- Old UI files app.py/i18n.py/ui_components.py working-tree diffs are the user's skin work,
  NOT committed by this task.
