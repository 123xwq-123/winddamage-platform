"""新版大屏 /screen 契约测试。

设计文档：OUTPUT/设计文档.md；实施计划：OUTPUT/实施计划.md。
旧界面零改动约束：本文件只测新增模块，不触碰 app/ui_components 行为。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


if __name__ == "__main__":
    unittest.main()
