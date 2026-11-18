"""单图检测页的全屏三栏布局契约。"""
import os
import re
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestSingleImageWorkbenchLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "ui_components.py"), encoding="utf-8") as f:
            cls.css_source = f.read()
        with open(os.path.join(ROOT, "app.py"), encoding="utf-8") as f:
            cls.app_source = f.read()
        with open(os.path.join(ROOT, "assets", "dynamic_wind_farm.html"), encoding="utf-8") as f:
            cls.background_source = f.read()
        with open(os.path.join(ROOT, "assets", "wind_turbine_viewer.html"), encoding="utf-8") as f:
            cls.viewer_source = f.read()

    def test_desktop_workbench_fills_available_viewport(self):
        block = re.search(
            r"\.wd-workbench-grid\s*\{(?P<body>.*?)\}",
            self.css_source,
            re.S,
        ).group("body")
        self.assertIn("height:calc(100dvh - 158px)", block)
        self.assertNotIn("810px", block)
        self.assertNotIn("max-height:calc(100vw * 9 / 16)", block)

    def test_gradio_inner_app_does_not_cap_page_width(self):
        self.assertIn(
            ".app.fillable:not(.fill_width) { max-width:none !important; width:100% !important; }",
            self.css_source,
        )

    def test_3d_viewer_fills_the_model_column_below_its_heading(self):
        self.assertIn(
            'elem_classes=["wd-turbine-viewer"]',
            self.app_source,
        )
        self.assertIn("height:calc(100dvh - 230px) !important", self.css_source)
        self.assertIn("min-height:620px !important", self.css_source)
        self.assertIn(".wd-turbine-viewer > div { height:100% !important", self.css_source)
        self.assertIn("position:absolute; inset:0", self.css_source)

    def test_desktop_columns_prioritize_the_3d_view(self):
        self.assertIn(".wd-input-col { flex:0 1 20%", self.css_source)
        self.assertIn(".wd-model-col { flex:1 1 58%", self.css_source)
        self.assertIn(".wd-report-col { flex:0 1 22%", self.css_source)
        self.assertRegex(
            self.app_source,
            r"gr\.Column\(scale=20, min_width=300, elem_classes=\[\"wd-workbench-col\", \"wd-input-col\"\]\)",
        )
        self.assertRegex(
            self.app_source,
            r"gr\.Column\(scale=58, min_width=0, elem_classes=\[\"wd-workbench-col\", \"wd-model-col\"\]\)",
        )
        self.assertRegex(
            self.app_source,
            r"gr\.Column\(scale=22, min_width=340, elem_classes=\[\"wd-workbench-col\", \"wd-report-col\"\]\)",
        )

    def test_desktop_controls_use_readable_ui_sizing(self):
        self.assertRegex(self.css_source, r":root\s*\{[^}]*--wd-fs:\s*1\.15", re.S)
        self.assertNotRegex(self.css_source, r"\.gradio-container\s*\{\s*--wd-fs:")
        self.assertIn(".gradio-container .tab-nav button", self.css_source)
        self.assertIn("min-height:44px", self.css_source)
        self.assertIn("font-size:calc(16px * var(--wd-fs))", self.css_source)

    def test_font_settings_default_and_reset_to_115_percent(self):
        self.assertIn('value="115"', self.app_source)
        self.assertIn('id="wd-sp-font-val">115%</span>', self.app_source)
        self.assertIn("fs = 1.15", self.app_source)
        self.assertIn("fs = 1.15; applyFont(1.15)", self.app_source)
        self.assertIn("range.value = '115'", self.app_source)
        self.assertIn("val.textContent = '115%'", self.app_source)

    def test_report_text_has_readable_minimum_sizes(self):
        self.assertIn("table.wd-kv { width:100%; border-collapse:collapse; font-size:calc(16px * var(--wd-fs)); }", self.css_source)
        self.assertIn("table.wd-table { width:100%; border-collapse:collapse; font-size:calc(15px * var(--wd-fs)); }", self.css_source)
        self.assertIn(".wd-summary-item .wd-label { font-size:calc(14px * var(--wd-fs))", self.css_source)
        self.assertIn(".wd-summary-title { font-size:calc(17px * var(--wd-fs))", self.css_source)

    def test_report_components_stack_vertically_inside_scroll_column(self):
        report_col = re.search(
            r"\.wd-report-col\s*\{(?P<body>.*?)\}",
            self.css_source,
            re.S,
        ).group("body")
        self.assertIn("flex-direction:column !important", report_col)
        self.assertIn("flex-wrap:nowrap !important", report_col)
        self.assertIn(
            ".wd-report-col > * { flex:0 0 auto !important; min-height:min-content !important; }",
            self.css_source,
        )
        self.assertIn(
            ".wd-report-output { flex:0 0 auto !important; height:auto !important; overflow:visible !important; }",
            self.css_source,
        )
        self.assertIn('elem_classes=["wd-report-output"]', self.app_source)

    def test_3d_turbine_matches_reference_proportions_and_markings(self):
        self.assertIn("const towerH=52", self.viewer_source)
        self.assertIn("const bladeLen=23", self.viewer_source)
        self.assertIn("function makeBlade", self.viewer_source)
        self.assertIn("function addBladeBand", self.viewer_source)
        self.assertIn("0xd92832", self.viewer_source)
        self.assertIn("new THREE.BoxGeometry(8.8,3.1,3.2", self.viewer_source)
        self.assertIn("camera.position.set(132,46,54)", self.viewer_source)
        self.assertIn("controls.target.set(0,35,0)", self.viewer_source)
        self.assertIn("pivot.rotation.x=i*Math.PI*2/3-.035", self.viewer_source)

    def test_3d_hud_text_is_readable(self):
        self.assertIn(".title{font-size:22px", self.viewer_source)
        self.assertIn("font-size:16px;color:#0d4f78", self.viewer_source)
        self.assertIn("gap:15px;font-size:16px", self.viewer_source)
        self.assertIn(".controls button{font-size:15px", self.viewer_source)
        self.assertIn("transform:translateX(-50%);font-size:14px", self.viewer_source)
        self.assertIn("color:#573030;font-size:16px", self.viewer_source)

    def test_clear_action_resets_filepath_image_with_none(self):
        clear_binding = re.search(
            r"btn_clear\.click\((?P<body>.*?)\n\s*\)",
            self.app_source,
            re.S,
        ).group("body")
        self.assertIn('fn=lambda: (None, EMPTY_RESULT_HTML', clear_binding)
        self.assertNotIn('fn=lambda: ("", EMPTY_RESULT_HTML', clear_binding)

    def test_examples_show_exactly_ten_uniform_cards_per_page(self):
        self.assertIn("examples_per_page=10", self.app_source)
        gallery_block = re.search(
            r"\.wd-input-col \.gallery\s*\{(?P<body>.*?)\}",
            self.css_source,
            re.S,
        ).group("body")
        self.assertIn("display:grid !important", gallery_block)
        self.assertIn("grid-template-columns:repeat(auto-fill, 80px) !important", gallery_block)
        self.assertIn(".wd-input-col .gallery .gallery-item", self.css_source)
        self.assertIn("width:80px !important", self.css_source)
        self.assertIn("height:80px !important", self.css_source)
        self.assertIn("object-fit:cover !important", self.css_source)

    def test_export_buttons_render_equal_size(self):
        self.assertRegex(
            self.app_source,
            r"gr\.Row\(elem_classes=\[\"wd-export-row\"\]\)",
        )
        for name in ("btn_export_md", "btn_export_json", "btn_copy_json"):
            self.assertRegex(
                self.app_source,
                rf"{name} = gr\.Button\(tr\(\"btn_[a-z_]+\"\), elem_classes=\[\"wd-export-btn\"\]\)",
            )
        row = re.search(
            r"\.wd-export-row\s*\{(?P<body>.*?)\}",
            self.css_source,
            re.S,
        ).group("body")
        self.assertIn("flex-direction:column !important", row)
        self.assertIn("flex-wrap:nowrap !important", row)
        btn = re.search(
            r"\.wd-export-btn\s*\{(?P<body>.*?)\}",
            self.css_source,
            re.S,
        ).group("body")
        self.assertIn("width:100% !important", btn)
        self.assertIn("white-space:nowrap !important", btn)
        self.assertNotIn("flex:1 1 0", btn)

    def test_example_thumbnails_have_consistent_dimensions(self):
        self.assertIn(".wd-input-col .gallery-item", self.css_source)
        self.assertIn("width:80px !important", self.css_source)
        self.assertIn("height:80px !important", self.css_source)
        self.assertIn("object-fit:cover !important", self.css_source)

    def test_background_uses_fresh_renewable_energy_layers(self):
        self.assertIn("drawSun", self.background_source)
        self.assertIn("drawHills", self.background_source)
        self.assertIn("drawEnergyFlow", self.background_source)
        self.assertIn("prefers-reduced-motion", self.background_source)


class TestThemeSystem(unittest.TestCase):
    """五主题皮肤系统：token 覆盖 + 设置弹层切换器契约。"""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "ui_components.py"), encoding="utf-8") as f:
            cls.css_source = f.read()
        with open(os.path.join(ROOT, "app.py"), encoding="utf-8") as f:
            cls.app_source = f.read()

    def test_five_skins_defined_as_token_overrides(self):
        for skin in ("night", "glass", "bento", "hmi"):
            block = re.search(
                rf'\[data-wd-theme="{skin}"\]\s*\{{(?P<body>.*?)\}}',
                self.css_source,
                re.S,
            )
            self.assertIsNotNone(block, f"missing [data-wd-theme=\"{skin}\"] block")
            body = block.group("body")
            for token in ("--brand-700", "--bg-page", "--bg-card", "--text-1", "--border"):
                self.assertIn(token, body, f"{skin} missing {token}")

    def test_hardcoded_surfaces_use_tokens(self):
        # 卡片/工作台面板、3D 天空、输入框底色、危险行悬停必须是变量
        self.assertIn("background:var(--bg-card-tint)", self.css_source)
        self.assertIn("var(--turbine-sky)", self.css_source)
        self.assertIn("--turbine-sky:", self.css_source)
        self.assertIn("var(--bg-field)", self.css_source)
        self.assertIn("var(--row-danger-hover)", self.css_source)
        self.assertIn("var(--veil-top)", self.css_source)
        # 夜航主题能整体反转页面基调
        night = re.search(
            r'\[data-wd-theme="night"\]\s*\{(?P<body>.*?)\}',
            self.css_source,
            re.S,
        ).group("body")
        self.assertIn("--veil-top:", night)
        self.assertIn("--bg-field:", night)

    def test_night_skin_remaps_gradio_component_vars(self):
        night = re.search(
            r'\[data-wd-theme="night"\] \.gradio-container\s*\{(?P<body>.*?)\}',
            self.css_source,
            re.S,
        )
        self.assertIsNotNone(night)
        for token in ("--background-fill-primary", "--block-background-fill",
                      "--body-text-color", "--input-background-fill"):
            self.assertIn(token, night.group("body"))

    def test_settings_popover_offers_five_skins(self):
        for skin in ("clear", "night", "glass", "bento", "hmi"):
            self.assertIn(f'data-wd-skin="{skin}"', self.app_source)
        self.assertIn('id="wd-sp-skin"', self.app_source)
        self.assertIn('tr("settings_skin")', self.app_source)
    def test_skin_preference_persisted_and_applied_live(self):
        self.assertIn("wd_skin", self.app_source)
        self.assertIn("setAttribute('data-wd-theme'", self.app_source)
        self.assertIn("applySkin(get('wd_skin')", self.app_source)


class TestThemeRefinements(unittest.TestCase):
    """里程碑 2/3：夜航对比度加固、Bento/HMI 精修、3D 视窗随主题联动、缓存治理。"""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "ui_components.py"), encoding="utf-8") as f:
            cls.css_source = f.read()
        with open(os.path.join(ROOT, "app.py"), encoding="utf-8") as f:
            cls.app_source = f.read()
        with open(os.path.join(ROOT, "server.py"), encoding="utf-8") as f:
            cls.server_source = f.read()
        with open(os.path.join(ROOT, "assets", "wind_turbine_viewer.html"), encoding="utf-8") as f:
            cls.viewer_source = f.read()

    def test_night_text_colors_are_hardened_with_important(self):
        # 无论 Gradio 深浅模式如何叠加，夜航下的正文/标签/空状态文字必须保持浅色
        for selector in ('.gradio-container .prose',):
            pattern = re.escape(selector) + r'[^\{]*\{ color:var\(--text-1\) !important'
            self.assertRegex(self.css_source, pattern)
        self.assertRegex(
            self.css_source,
            r'\.gradio-container \.html-container[^\{]*\{ color:var\(--text-1\) !important',
        )
        self.assertRegex(
            self.css_source,
            r'\[data-wd-theme="night"\] \.gradio-container label[^\{]*\{ color:var\(--text-1\) !important',
        )
        self.assertIn(
            '[data-wd-theme="night"] .gradio-container .wd-empty .wd-empty-title { color:var(--text-1) !important; }',
            self.css_source,
        )

    def test_base_css_is_never_served_stale(self):
        self.assertIn('"/wd-assets/base.css"', self.server_source)
        block = re.search(
            r'@fastapp\.get\("/wd-assets/base\.css"\)(?P<body>.*?)headers=\{(?P<hdr>.*?)\}',
            self.server_source,
            re.S,
        )
        self.assertIsNotNone(block)
        self.assertIn("no-cache", block.group("hdr"))
        self.assertNotIn("max-age", block.group("hdr"))

    def test_hmi_badges_use_shape_coded_states(self):
        hmi = re.search(
            r'\[data-wd-theme="hmi"\][^\{]*\.wd-badge-danger(?:::?before)?\s*\{(?P<body>.*?)\}',
            self.css_source,
            re.S,
        )
        self.assertIsNotNone(hmi)
        self.assertIn('content:"▲ "', hmi.group("body"))
        self.assertIn('content:"■ "', self.css_source)
        self.assertIn('content:"● "', self.css_source)

    def test_night_buttons_keep_readable_text(self):
        # 夜航下 Gradio 按钮（开始分析/清空/导出等）文字必须保持高对比：
        # 次级按钮浅字深底；主按钮（primary）深底白字；链接类按钮浅蓝字
        self.assertRegex(
            self.css_source,
            r'\[data-wd-theme="night"\] \.gradio-container button,[^\{]*\{[^}]*color:var\(--text-1\) !important',
        )
        self.assertRegex(
            self.css_source,
            r'\[data-wd-theme="night"\] \.gradio-container button\.primary[^\{]*\{[^}]*color:#FFFFFF !important',
        )
        self.assertIn(
            '[data-wd-theme="night"] .gradio-container button.lg { border:1px solid var(--border) !important; }',
            self.css_source,
        )

    def test_bento_enlarges_heading_and_stat_typography(self):
        self.assertIn('[data-wd-theme="bento"] .wd-workbench-col > .prose:first-child h3',
                      self.css_source)
        bento_stat = re.search(
            r'\[data-wd-theme="bento"\] \.wd-stat \.wd-stat-num\s*\{(?P<body>.*?)\}',
            self.css_source,
            re.S,
        )
        self.assertIsNotNone(bento_stat)
        self.assertIn("32px", bento_stat.group("body"))

    def test_turbine_viewer_adapts_to_theme(self):
        # 主页面主题变化时向 viewer iframe 发送 postMessage
        self.assertIn("postMessage({wdTheme:", self.app_source)
        # viewer 支持 night 场景配色（深色天空/雾/草地）与 HUD 深色化
        self.assertIn("wdTheme", self.viewer_source)
        self.assertIn("0x0e1b33", self.viewer_source.lower())
        self.assertIn('[data-vt="night"]', self.viewer_source)

    def test_glass_aurora_drifts_gently(self):
        self.assertIn("@keyframes wd-aurora", self.css_source)
        self.assertIn("wd-aurora", self.css_source)


class TestHudSkin(unittest.TestCase):
    """第六套皮肤「深空HUD」：融合参考1（角标/发光青边/斑马表）与
    参考2（竖条标题/半透明面板/网格底）的设计语言，独立可切换。"""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "ui_components.py"), encoding="utf-8") as f:
            cls.css_source = f.read()
        with open(os.path.join(ROOT, "app.py"), encoding="utf-8") as f:
            cls.app_source = f.read()
        with open(os.path.join(ROOT, "i18n.py"), encoding="utf-8") as f:
            cls.i18n_source = f.read()
        with open(os.path.join(ROOT, "assets", "wind_turbine_viewer.html"), encoding="utf-8") as f:
            cls.viewer_source = f.read()

    def test_hud_registered_as_sixth_skin(self):
        # 切换器第六个按钮 + SKINS 数组 + 双语词条
        self.assertIn('data-wd-skin="hud"', self.app_source)
        self.assertIn("'hud'", self.app_source)
        self.assertIn('"skin_hud"', self.i18n_source)
        hud_tokens = re.search(
            r'\[data-wd-theme="hud"\]\s*\{(?P<body>.*?)\}',
            self.css_source,
            re.S,
        )
        self.assertIsNotNone(hud_tokens)
        for token in ("--brand-700", "--bg-page", "--bg-card", "--text-1", "--border"):
            self.assertIn(token, hud_tokens.group("body"))

    def test_hud_panels_have_corner_brackets(self):
        # 参考1 的面板 L 形角标（::before / ::after 各画两角）
        self.assertRegex(
            self.css_source,
            r'\[data-wd-theme="hud"\] \.wd-workbench-col::before\s*\{[^}]*border-top[^}]*border-left',
        )
        self.assertRegex(
            self.css_source,
            r'\[data-wd-theme="hud"\] \.wd-workbench-col::after\s*\{[^}]*border-bottom[^}]*border-right',
        )

    def test_hud_titles_use_accent_bar_and_letterspacing(self):
        # 参考2 的左侧竖条标题 + 科技感字距 + 渐变下划线
        hud_title = re.search(
            r'\[data-wd-theme="hud"\] \.wd-workbench-col h3\s*\{(?P<body>.*?)\}',
            self.css_source,
            re.S,
        )
        self.assertIsNotNone(hud_title)
        self.assertIn("border-left", hud_title.group("body"))
        self.assertIn("letter-spacing", hud_title.group("body"))

    def test_hud_background_has_grid_overlay(self):
        # 参考2 的科技网格底（repeating-linear-gradient 网格线）
        self.assertRegex(
            self.css_source,
            r'\[data-wd-theme="hud"\] body::after\s*\{[^}]*repeating-linear-gradient',
        )

    def test_hud_primary_button_glows(self):
        hud_btn = re.search(
            r'\[data-wd-theme="hud"\] \.gradio-container button\.primary\s*\{(?P<body>.*?)\}',
            self.css_source,
            re.S,
        )
        self.assertIsNotNone(hud_btn)
        self.assertIn("box-shadow", hud_btn.group("body"))

    def test_hud_night_text_hardening_applies(self):
        # 深色皮肤必须复用夜航的对比度加固（按钮/chip/正文浅字）
        self.assertRegex(
            self.css_source,
            r'\[data-wd-theme="hud"\] \.gradio-container button,[^\{]*\{[^}]*color:var\(--text-1\) !important',
        )

    def test_hud_viewer_palette_registered(self):
        # viewer THEME 表要有 hud 条目（深空蓝天 + 复用夜航 HUD 深色化）
        self.assertRegex(
            self.viewer_source,
            r'hud:\{sky:0x[0-9a-f]+,fog:0x[0-9a-f]+,grass:0x[0-9a-f]+,blades:0x[0-9a-f]+,vt:\'night\'\}',
        )


if __name__ == "__main__":
    unittest.main()
