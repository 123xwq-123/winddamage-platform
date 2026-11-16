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

    def test_login_page_no_redirect_loop(self):
        """未登录访问 /screen/login 必须 200（回归：曾 302 成环）。"""
        self.tmp = tempfile.mkdtemp()
        os.environ["WD_DB_PATH"] = os.path.join(self.tmp, "h.db")
        try:
            import history
            history.init_db()
            auth.create_user("guardadmin", "Passw0rd1", role="admin")
            from fastapi.testclient import TestClient
            import server
            with TestClient(server.create_app()) as client:
                r = client.get("/screen/login")
                self.assertEqual(r.status_code, 200)
                self.assertIn('name="username"', r.text)
                # 未登录 /screen → 302 登录页，且登录页不再二次跳转
                r2 = client.get("/screen", follow_redirects=False)
                self.assertEqual(r2.status_code, 302)
                self.assertIn("/screen/login", r2.headers["location"])
                r3 = client.get("/screen/login?expired=1")
                self.assertEqual(r3.status_code, 200)
                # 静态资源未登录也要放行（登录页样式依赖）
                r4 = client.get("/screen-assets/screen.css")
                self.assertEqual(r4.status_code, 200)
        finally:
            os.environ.pop("WD_DB_PATH", None)
            shutil.rmtree(self.tmp, ignore_errors=True)


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


class TestFarmViewer(unittest.TestCase):
    """3D 风场底座契约：vendor 引入、postMessage 协议、标签锚点。"""

    def setUp(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.p = os.path.join(base, "assets", "screen", "farm_viewer.html")

    def _src(self):
        with open(self.p, encoding="utf-8") as f:
            return f.read()

    def test_exists_with_vendor_import(self):
        src = self._src()
        # farm_viewer 由 /screen-assets/ 提供，vendor 走 /wd-assets 绝对路径
        self.assertIn("/wd-assets/vendor/three/three.module.js", src)
        self.assertIn("OrbitControls", src)

    def test_message_protocol(self):
        src = self._src()
        for token in ('"wd:labels"', '"wd:damage"', '"wd:focus"', '"wd:ready"'):
            self.assertIn(token, src)

    def test_anchor_ids(self):
        src = self._src()
        for anchor in ("turbine", "nacelle", "substation", "damage"):
            self.assertIn(f'"{anchor}"', src)


REPORT_HIGH = {
    "1. 构件识别": {"构件名称": "叶片"},
    "2. 损伤判定": {"是否存在损伤": "是", "损伤类型": "裂纹",
                "损伤分布位置与范围": "迎风面 距根部 12.4 m"},
    "6. 结论建议": {"巡检优先级": "高", "本次判断的置信度": "高"},
}


class TestScreenPayloads(unittest.TestCase):
    """主页 JSON payload 纯函数契约。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["WD_DB_PATH"] = os.path.join(self.tmp, "h.db")
        import history
        history.init_db()
        self.history = history

    def tearDown(self):
        os.environ.pop("WD_DB_PATH", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_overview_payload_keys(self):
        import screen_api
        p = screen_api._overview_payload(owner_scope=None, week=3, recheck=2)
        for k in ("total", "week", "high_risk", "recheck", "completion"):
            self.assertIn(k, p)
        self.assertEqual(p["week"], 3)
        self.assertEqual(p["recheck"], 2)

    def test_report_payload_shape(self):
        import screen_api
        p = screen_api._report_payload(
            REPORT_HIGH, record_id=1, infer_time=1.2,
            image_info={"filename": "a.jpg", "width": 4032, "height": 3024},
            recent=[])
        self.assertTrue(p["locator"]["hasDamage"])
        self.assertEqual(p["locator"]["part"], "叶片")
        self.assertEqual(p["risk"]["type"], "裂纹")
        self.assertEqual(p["risk"]["level"], "高")
        for k in ("component", "location", "size", "advice", "model", "time", "report_no"):
            self.assertIn(k, p["kv"])
        self.assertEqual(p["kv"]["component"], "叶片")
        self.assertIn("复检", p["kv"]["advice"])
        self.assertEqual(p["recent"], [])
        self.assertEqual(p["record_id"], 1)

    def test_row_item_shape(self):
        import screen_api
        item = screen_api._row_item({
            "id": 7, "timestamp": "2026-11-16 09:47:00", "image_name": "b.jpg",
            "high_risk": 1, "has_damage": "是", "damage_type": "裂纹",
            "component": "叶片", "priority": "高", "confidence": "高",
            "infer_time": 1.5, "note": ""})
        for k in ("id", "timestamp", "image_name", "high_risk", "damage_type",
                  "component", "priority"):
            self.assertIn(k, item)
        self.assertTrue(item["high_risk"])


class FakeReq:
    """轻量请求桩：auth.user_for_request 只依赖 headers.get("cookie")。"""

    def __init__(self, cookie="", body=None):
        self.headers = {"cookie": cookie}
        self._body = body or {}

    async def json(self):
        return self._body


def _cookie_for(uid):
    return "wd_session=" + auth.create_session(uid)


class TestScreenRecordsApi(unittest.TestCase):
    """历史记录 API 契约：scope 过滤、详情权限、备注/删除。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["WD_DB_PATH"] = os.path.join(self.tmp, "h.db")
        import history
        history.init_db()
        self.history = history
        self.uid = auth.create_user("recowner", "Passw0rd1")
        self.other_uid = auth.create_user("recother", "Passw0rd1")
        self.rid = history.save_record("a.jpg", REPORT_HIGH, 1.2, "",
                                       owner_user_id=self.uid, created_by="recowner")

    def tearDown(self):
        os.environ.pop("WD_DB_PATH", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _body(self, resp):
        import json as _j
        return _j.loads(resp.body)

    def test_records_api_returns_scope_rows(self):
        import asyncio
        import screen_api
        # 他人记录不可见
        self.history.save_record("b.jpg", REPORT_HIGH, 0.9, "",
                                 owner_user_id=self.other_uid, created_by="recother")
        resp = asyncio.run(screen_api.api_records(FakeReq(_cookie_for(self.uid))))
        data = self._body(resp)
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["rows"][0]["id"], self.rid)
        for k in ("rows", "total", "stats"):
            self.assertIn(k, data)
        # admin 见全部
        admin_uid = auth.create_user("recadmin", "Passw0rd1", role="admin")
        resp2 = asyncio.run(screen_api.api_records(FakeReq(_cookie_for(admin_uid))))
        self.assertEqual(self._body(resp2)["total"], 2)

    def test_records_api_filters(self):
        import asyncio
        import screen_api
        resp = asyncio.run(screen_api.api_records(
            FakeReq(_cookie_for(self.uid)), risk="high"))
        self.assertEqual(self._body(resp)["total"], 1)
        resp2 = asyncio.run(screen_api.api_records(
            FakeReq(_cookie_for(self.uid)), search="b.jpg"))
        self.assertEqual(self._body(resp2)["total"], 0)

    def test_record_detail_permission(self):
        import asyncio
        import screen_api
        ok = asyncio.run(screen_api.api_record_detail(
            FakeReq(_cookie_for(self.uid)), record_id=self.rid))
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(self._body(ok)["id"], self.rid)
        forbidden = asyncio.run(screen_api.api_record_detail(
            FakeReq(_cookie_for(self.other_uid)), record_id=self.rid))
        self.assertEqual(forbidden.status_code, 403)

    def test_note_and_delete(self):
        import asyncio
        import screen_api
        resp = asyncio.run(screen_api.api_record_note(
            FakeReq(_cookie_for(self.uid), {"note": "复查通过"}),
            record_id=self.rid))
        self.assertEqual(self._body(resp), {"ok": True})
        self.assertEqual(self.history.get_record(self.rid)["note"], "复查通过")
        resp2 = asyncio.run(screen_api.api_record_delete(
            FakeReq(_cookie_for(self.other_uid)), record_id=self.rid))
        self.assertEqual(resp2.status_code, 403)
        resp3 = asyncio.run(screen_api.api_record_delete(
            FakeReq(_cookie_for(self.uid)), record_id=self.rid))
        self.assertEqual(self._body(resp3), {"ok": True})
        self.assertIsNone(self.history.get_record(self.rid))

    def test_history_page_exists(self):
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "assets", "screen", "history.html")
        with open(p, encoding="utf-8") as f:
            src = f.read()
        for token in ("sc-subpage", "history.js"):
            self.assertIn(token, src)


class TestScreenBatchApi(unittest.TestCase):
    """批量检测 API 契约：逐张分析、归属、失败容错、汇总。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["WD_DB_PATH"] = os.path.join(self.tmp, "h.db")
        import history
        history.init_db()
        self.history = history
        self.uid = auth.create_user("batchop", "Passw0rd1")

    def tearDown(self):
        os.environ.pop("WD_DB_PATH", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _req(self, uploads):
        cookie = "wd_session=" + auth.create_session(self.uid)

        class FakeForm:
            def getlist(self_inner, key):
                return uploads

        class FakeUpload:
            def __init__(self, name):
                self.filename = name

            async def read(self_inner):
                return b"\x89PNG\r\n\x1a\n" + b"0" * 32   # PNG 魔数占位

        class FakeRequest(FakeReq):
            async def form(self_inner):
                return FakeForm()

        return FakeRequest(cookie)

    @staticmethod
    def _upload(name):
        class U:
            async def read(self_inner):
                return b"\x89PNG\r\n\x1a\n" + b"0" * 32
        U.filename = name
        return U()

    def test_batch_results_and_attribution(self):
        import asyncio
        from unittest import mock
        import screen_api
        normal = {"1. 构件识别": {"构件名称": "塔筒"},
                  "2. 损伤判定": {"是否存在损伤": "否", "损伤类型": "无"},
                  "6. 结论建议": {"巡检优先级": "低", "本次判断的置信度": "高"}}
        seq = [(REPORT_HIGH, "{}", 0.5), (normal, "{}", 0.4),
               (REPORT_HIGH, "{}", 0.6)]
        def up(name):
            return self._upload(name)

        with mock.patch("app._do_inference", side_effect=lambda p: seq.pop(0)):
            resp = asyncio.run(screen_api.api_batch(self._req(
                [self._upload(f"img{i}.jpg") for i in range(3)])))
        import json as _j
        data = _j.loads(resp.body)
        self.assertTrue(all(r["ok"] for r in data["results"]))
        self.assertEqual(data["total"], 3)
        self.assertEqual(data["high_risk"], 2)
        ids = [r["record_id"] for r in data["results"]]
        self.assertTrue(all(ids))
        # 归属校验
        rec = self.history.get_record(ids[0])
        self.assertEqual(rec["owner_user_id"], self.uid)
        self.assertEqual(rec["source"], "screen")

    def test_batch_tolerates_failure(self):
        import asyncio
        from unittest import mock
        import screen_api

        def boom(path):
            raise RuntimeError("model offline")

        with mock.patch("app._do_inference", side_effect=boom):
            resp = asyncio.run(screen_api.api_batch(self._req([self._upload("x.jpg")])))
        import json as _j
        data = _j.loads(resp.body)
        self.assertFalse(data["results"][0]["ok"])
        self.assertIn("model offline", data["results"][0]["error"])


class TestScreenAccountApi(unittest.TestCase):
    """账户中心 API 契约：改密、用户管理权限、导出。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["WD_DB_PATH"] = os.path.join(self.tmp, "h.db")
        import history
        history.init_db()
        self.history = history
        self.uid = auth.create_user("acctop", "Passw0rd1")
        self.admin_uid = auth.create_user("acctadmin", "Passw0rd1", role="admin")
        self.rid = self.history.save_record("exp.jpg", REPORT_HIGH, 1.0, "",
                                            owner_user_id=self.uid,
                                            created_by="acctop")

    def tearDown(self):
        os.environ.pop("WD_DB_PATH", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _req(self, uid, body=None):
        return FakeReq("wd_session=" + auth.create_session(uid), body)

    def _body(self, resp):
        import json as _j
        return _j.loads(resp.body)

    def test_change_password_flow(self):
        import asyncio
        import screen_api
        bad = asyncio.run(screen_api.api_change_password(
            self._req(self.uid, {"old_password": "wrong", "new_password": "NewPass9x"})))
        self.assertEqual(bad.status_code, 400)
        ok = asyncio.run(screen_api.api_change_password(
            self._req(self.uid, {"old_password": "Passw0rd1", "new_password": "NewPass9x"})))
        self.assertEqual(self._body(ok), {"ok": True})
        status, payload = auth.authenticate("acctop", "NewPass9x")
        self.assertEqual(status, "ok")

    def test_users_api_admin_only(self):
        import asyncio
        import screen_api
        forbidden = asyncio.run(screen_api.api_users(self._req(self.uid)))
        self.assertEqual(forbidden.status_code, 403)
        ok = asyncio.run(screen_api.api_users(self._req(self.admin_uid)))
        users = self._body(ok)["users"]
        self.assertTrue(any(u["username"] == "acctop" for u in users))
        self.assertFalse(any("pw_hash" in u or "pw_salt" in u for u in users))

    def test_user_action_admin_only(self):
        import asyncio
        import screen_api
        forbidden = asyncio.run(screen_api.api_user_action(
            self._req(self.uid, {"action": "deactivate"}), target_id=self.uid))
        self.assertEqual(forbidden.status_code, 403)
        ok = asyncio.run(screen_api.api_user_action(
            self._req(self.admin_uid, {"action": "deactivate"}), target_id=self.uid))
        self.assertEqual(self._body(ok), {"ok": True})
        self.assertEqual(auth.get_user(self.uid)["is_active"], 0)
        asyncio.run(screen_api.api_user_action(
            self._req(self.admin_uid, {"action": "activate"}), target_id=self.uid))
        self.assertEqual(auth.get_user(self.uid)["is_active"], 1)

    def test_export_endpoint(self):
        import asyncio
        import screen_api
        ok = asyncio.run(screen_api.api_export(self._req(self.uid), record_id=self.rid))
        self.assertEqual(ok.status_code, 200)
        text = ok.body.decode("utf-8")
        self.assertIn("叶片", text)
        forbidden = asyncio.run(screen_api.api_export(
            self._req(auth.create_user("expother", "Passw0rd1")), record_id=self.rid))
        self.assertEqual(forbidden.status_code, 403)


class TestScreenLoginV2(unittest.TestCase):
    """登录页 V2：开放注册 + 记住密码（30 天免登录 + 本地记忆）。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["WD_DB_PATH"] = os.path.join(self.tmp, "h.db")
        import history
        history.init_db()
        self.uid = auth.create_user("v2login", "Passw0rd1")

    def tearDown(self):
        os.environ.pop("WD_DB_PATH", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _client(self):
        from fastapi.testclient import TestClient
        import server
        return TestClient(server.create_app())

    def _max_age(self, resp):
        import re
        m = re.search(r"max-age=(\d+)", resp.headers.get("set-cookie", ""), re.I)
        return int(m.group(1)) if m else None

    def test_register_success_auto_login(self):
        with self._client() as c:
            r = c.post("/screen/register", data={
                "username": "NewInspector", "password": "Passw0rd1",
                "confirm": "Passw0rd1"}, follow_redirects=False)
            self.assertEqual(r.status_code, 302)
            self.assertEqual(r.headers["location"], "/screen")
            self.assertIsNotNone(self._max_age(r))   # 已下发会话 Cookie
            u = auth.get_user_by_name("newinspector")
            self.assertIsNotNone(u)
            self.assertEqual(u["role"], "user")
            # 带 Cookie 能进大屏
            r2 = c.get("/screen", follow_redirects=False)
            self.assertEqual(r2.status_code, 200)

    def test_register_duplicate_username(self):
        with self._client() as c:
            r = c.post("/screen/register", data={
                "username": "v2login", "password": "Passw0rd1",
                "confirm": "Passw0rd1"})
            self.assertEqual(r.status_code, 200)
            self.assertIn("已被注册", r.text)

    def test_register_weak_password(self):
        with self._client() as c:
            r = c.post("/screen/register", data={
                "username": "weakpw", "password": "1234",
                "confirm": "1234"})
            self.assertEqual(r.status_code, 200)
            self.assertIn("密码", r.text)
            self.assertIsNone(auth.get_user_by_name("weakpw"))

    def test_register_password_mismatch(self):
        with self._client() as c:
            r = c.post("/screen/register", data={
                "username": "mismatch", "password": "Passw0rd1",
                "confirm": "Passw0rd2"})
            self.assertEqual(r.status_code, 200)
            self.assertIn("不一致", r.text)
            self.assertIsNone(auth.get_user_by_name("mismatch"))

    def test_register_route_open_unauthenticated(self):
        """回归：未登录 POST /screen/register 不得被中间件 302 拦截。"""
        with self._client() as c:
            r = c.post("/screen/register", data={}, follow_redirects=False)
            self.assertEqual(r.status_code, 200)

    def test_login_remember_extends_session(self):
        with self._client() as c:
            r = c.post("/screen/login", data={
                "username": "v2login", "password": "Passw0rd1",
                "remember": "on"}, follow_redirects=False)
            self.assertEqual(r.status_code, 302)
            self.assertEqual(self._max_age(r), 30 * 86400)
            # 服务端会话有效期约 30 天
            import datetime as _dt
            token = c.cookies.get("wd_session")
            row = auth.get_conn().execute(
                "SELECT expires_at FROM sessions WHERE token = ?", (token,)).fetchone()
            delta = (_dt.datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
                     - _dt.datetime.now()).total_seconds()
            self.assertTrue(29.9 * 86400 < delta <= 30.1 * 86400)

    def test_login_without_remember_default_ttl(self):
        with self._client() as c:
            r = c.post("/screen/login", data={
                "username": "v2login", "password": "Passw0rd1"},
                follow_redirects=False)
            self.assertEqual(self._max_age(r), auth.SESSION_TTL_HOURS * 3600)

    def test_create_session_days_param(self):
        import datetime as _dt
        token = auth.create_session(self.uid, days=30)
        row = auth.get_conn().execute(
            "SELECT expires_at FROM sessions WHERE token = ?", (token,)).fetchone()
        delta = (_dt.datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
                 - _dt.datetime.now()).total_seconds()
        self.assertTrue(29.9 * 86400 < delta <= 30.1 * 86400)
        # 不传 days 保持旧行为（SESSION_TTL_HOURS 小时）
        token2 = auth.create_session(self.uid)
        row2 = auth.get_conn().execute(
            "SELECT expires_at FROM sessions WHERE token = ?", (token2,)).fetchone()
        delta2 = (_dt.datetime.strptime(row2["expires_at"], "%Y-%m-%d %H:%M:%S")
                  - _dt.datetime.now()).total_seconds()
        self.assertTrue(delta2 <= auth.SESSION_TTL_HOURS * 3600 + 5)

    def test_lockout_disabled_by_default(self):
        """连续错 7 次不再触发锁定（锁定保护默认关闭）。"""
        with self._client() as c:
            for _ in range(7):
                r = c.post("/screen/login", data={
                    "username": "v2login", "password": "wrong-pw"},
                    follow_redirects=False)
                self.assertEqual(r.status_code, 200)
            u = auth.get_user(self.uid)
            self.assertIsNone(u["locked_until"], "默认不应触发锁定")
            self.assertEqual(u["failed_count"], 0)
            # 正确密码照常登录
            r = c.post("/screen/login", data={
                "username": "v2login", "password": "Passw0rd1"},
                follow_redirects=False)
            self.assertEqual(r.status_code, 302)

    def test_login_page_v2_has_tabs_and_remember(self):
        import asyncio
        import screen_api
        html = asyncio.run(screen_api.login_page())
        for token in ("data-mode", "记住密码", "screen-assets/login.js", "注册"):
            self.assertIn(token, html.body.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
