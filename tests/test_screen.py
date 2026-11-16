"""新版大屏 /screen 契约测试。

设计文档：OUTPUT/设计文档.md；实施计划：OUTPUT/实施计划.md。
旧界面零改动约束：本文件只测新增模块，不触碰 app/ui_components 行为。
"""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth

REQUIRED_PATHS = {
    "/screen", "/screen/login", "/screen/batch", "/screen/history",
    "/screen/account", "/screen/api/me", "/screen/api/overview",
    "/screen/api/analyze", "/screen/api/records",
}


class TestScreenRoutes(unittest.TestCase):
    """路由契约：screen_api.router 必须注册全部必需路径。"""

    def test_router_registers_all_required_paths(self):
        import screen_api
        paths = {getattr(r, "path", "").rstrip("/") for r in screen_api.router.routes}
        missing = REQUIRED_PATHS - paths
        self.assertFalse(missing, f"缺少路由: {missing}")

    def test_assets_screen_dir_exists(self):
        d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "assets", "screen")
        self.assertTrue(os.path.isdir(d), "assets/screen/ 静态目录应存在")


class TestScreenGuard(unittest.TestCase):
    """中间件契约：server.create_app 必须保护 /screen 前缀。"""

    def test_guard_source_protects_screen(self):
        import inspect
        import server
        src = inspect.getsource(server.create_app)
        self.assertIn('path.startswith("/screen")', src)
        self.assertIn('"/screen/login?expired=1"', src)
        self.assertIn("include_router(screen_api.router)", src)


class TestScreenLogin(unittest.TestCase):
    """大屏登录页契约：表单字段、POST 行为、共享样式文件。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["WD_DB_PATH"] = os.path.join(self.tmp, "h.db")
        import history
        history.init_db()
        self.auth = auth
        self.uid = auth.create_user("screenop", "Passw0rd1")

    def tearDown(self):
        os.environ.pop("WD_DB_PATH", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_css_exists_with_panel_system(self):
        css = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "assets", "screen", "screen.css")
        with open(css, encoding="utf-8") as f:
            src = f.read()
        for token in (".sc-panel", ".sc-col", ".sc-btn", ".sc-drop",
                      ".sc-tag", "position:fixed"):
            self.assertIn(token, src)

    def test_login_page_html_has_form(self):
        import asyncio
        import screen_api
        resp = asyncio.run(screen_api.login_page())
        html = resp.body.decode("utf-8")
        self.assertIn('name="username"', html)
        self.assertIn('name="password"', html)
        self.assertIn('action="/screen/login"', html)
        self.assertIn("/screen-assets/screen.css", html)

    def test_login_submit_success_sets_cookie_and_redirects(self):
        import asyncio
        import screen_api

        class FakeForm(dict):
            def __init__(self, d):
                super().__init__(d)

        class FakeRequest:
            headers = {"cookie": ""}
            async def form(self_inner):
                return FakeForm({"username": "screenop", "password": "Passw0rd1"})

        resp = asyncio.run(screen_api.login_submit(FakeRequest()))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.headers["location"], "/screen")
        self.assertIn(auth.SESSION_COOKIE, resp.headers.get("set-cookie", ""))

    def test_login_submit_bad_password_rerenders_with_error(self):
        import asyncio
        import screen_api

        class FakeRequest:
            headers = {"cookie": ""}
            async def form(self_inner):
                return {"username": "screenop", "password": "wrong"}

        resp = asyncio.run(screen_api.login_submit(FakeRequest()))
        self.assertEqual(resp.status_code, 200)
        html = resp.body.decode("utf-8")
        self.assertIn("sc-form-error", html)


if __name__ == "__main__":
    unittest.main()
