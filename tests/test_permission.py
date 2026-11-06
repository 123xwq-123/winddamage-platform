"""权限隔离测试：两个用户 + admin，经会话解析 scope，验证查询/详情/删除/清空/图表隔离。"""
import os
import sys
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPORT_A = {"1. 构件识别": {"构件名称": "叶片"},
            "2. 损伤判定": {"是否存在损伤": "是", "损伤类型": "裂纹"},
            "6. 结论建议": {"巡检优先级": "高", "本次判断的置信度": "高"}}
REPORT_B = {"1. 构件识别": {"构件名称": "塔筒"},
            "2. 损伤判定": {"是否存在损伤": "否", "损伤类型": "无"},
            "6. 结论建议": {"巡检优先级": "低", "本次判断的置信度": "高"}}


class _FakeRequest:
    """模拟 gr.Request / FastAPI Request 的最小接口（auth 只读 headers）。"""

    def __init__(self, cookie_token=None):
        headers = {}
        if cookie_token:
            headers["cookie"] = f"{__import__('auth').SESSION_COOKIE}={cookie_token}"
        self.headers = headers


class TestPermission(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "history.db")
        os.environ["WD_DB_PATH"] = self.db
        import history, auth, app as app_module, charts
        self.history, self.auth, self.app, self.charts = history, auth, app_module, charts
        history.init_db()

        # 三个账号：admin / 用户甲 / 用户乙
        self.admin_id = auth.create_user("perm_admin", "Passw0rd1", role="admin")
        self.ua_id = auth.create_user("perm_user_a", "Passw0rd1")
        self.ub_id = auth.create_user("perm_user_b", "Passw0rd1")
        self.admin_token = auth.create_session(self.admin_id)
        self.ua_token = auth.create_session(self.ua_id)
        self.ub_token = auth.create_session(self.ub_id)

        # 数据：甲 1 条高风险，乙 1 条低风险，迁移数据 1 条（owner NULL）
        self.rec_a = history.save_record("a.jpg", REPORT_A, source="ui",
                                         owner_user_id=self.ua_id, created_by="perm_user_a")
        self.rec_b = history.save_record("b.jpg", REPORT_B, source="ui",
                                         owner_user_id=self.ub_id, created_by="perm_user_b")
        self.rec_m = history.save_record("m.jpg", REPORT_B, source="migration")

    def tearDown(self):
        os.environ.pop("WD_DB_PATH", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _req(self, token):
        return _FakeRequest(token)

    # ─── scope 解析 ──────────────────────────────────
    def test_scope_resolution(self):
        self.assertEqual(self.app._current_scope(self._req(self.ua_token)),
                         (self.ua_id, False))
        self.assertEqual(self.app._current_scope(self._req(self.admin_token)),
                         (self.admin_id, True))
        # 未登录：明确拒绝（不能落回 admin 视角）
        self.assertEqual(self.app._current_scope(self._req(None)), (None, False))
        self.assertEqual(self.app._current_scope(self._req("bad-token")), (None, False))
        # None 请求（测试/直连兼容路径）保持旧行为
        self.assertEqual(self.app._current_scope(None), (None, True))

    # ─── 历史查询隔离 ────────────────────────────────
    def test_query_history_isolation(self):
        import gradio as gr
        for token, expect_ids in ((self.ua_token, {self.rec_a}),
                                  (self.ub_token, {self.rec_b}),
                                  (self.admin_token, {self.rec_a, self.rec_b, self.rec_m})):
            _stats, list_html, _page, _dd, _status = self.app.query_history(
                "", "", "", "", "time_desc", 20, 1, request=self._req(token))
            for rid in (self.rec_a, self.rec_b, self.rec_m):
                row_visible = f">{rid}</td>" in list_html
                if rid in expect_ids:
                    self.assertTrue(row_visible, f"{token[:6]}: 缺记录 {rid}")
                else:
                    self.assertNotIn(f">{rid}</td>", list_html,
                                     f"{token[:6]}: 越权看到 {rid}")

    def test_query_history_logged_out_is_empty(self):
        import gradio as gr
        _stats, list_html, _page, _dd, _status = self.app.query_history(
            "", "", "", "", "time_desc", 20, 1, request=self._req(None))
        # 未登录绝不返回任何数据
        self.assertNotIn(f">{self.rec_a}</td>", list_html)
        self.assertNotIn(f">{self.rec_b}</td>", list_html)
        self.assertNotIn(f">{self.rec_m}</td>", list_html)

    def test_stats_scoped(self):
        for token, total in ((self.ua_token, 1), (self.ub_token, 1), (self.admin_token, 3)):
            stats_html, *_ = self.app.query_history(
                "", "", "", "", "time_desc", 20, 1, request=self._req(token))
            self.assertIn(f">{total}</div>", stats_html)

    # ─── 详情 / 备注 / 删除权限 ───────────────────────
    def test_detail_access(self):
        ok, _json, _note = self.app.view_history_detail(
            str(self.rec_a), request=self._req(self.ua_token))
        self.assertNotIn("msg_record_no_access", ok)
        # 乙看甲的记录 → 拒绝
        denied, _json, _note = self.app.view_history_detail(
            str(self.rec_a), request=self._req(self.ub_token))
        self.assertIn("无权", denied)
        # admin 看迁移记录 → 允许
        ok_admin, _json, _note = self.app.view_history_detail(
            str(self.rec_m), request=self._req(self.admin_token))
        self.assertNotIn("无权", ok_admin)
        # 乙看迁移记录 → 拒绝
        denied_m, _json, _note = self.app.view_history_detail(
            str(self.rec_m), request=self._req(self.ub_token))
        self.assertIn("无权", denied_m)

    def test_note_access(self):
        self.assertEqual(self.app.save_note(str(self.rec_a), "ok备注",
                                            request=self._req(self.ua_token)),
                         self.app.tr("msg_note_saved"))
        self.assertEqual(self.app.save_note(str(self.rec_a), "越权",
                                            request=self._req(self.ub_token)),
                         self.app.tr("msg_record_no_access"))

    def test_delete_requires_access(self):
        # 乙删除甲的记录：确认条直接拒绝，不显示对方图片名
        msg, vis = self.app.ask_delete_record(str(self.rec_a),
                                              request=self._req(self.ub_token))
        self.assertNotIn("a.jpg", msg)
        # admin 删除乙的记录：允许
        _stats, list_html, _page, _dd, _confirm, status = self.app.do_delete_record(
            str(self.rec_b), request=self._req(self.admin_token))
        self.assertIsNone(self.history.get_record(self.rec_b))

    def test_clear_history_scope(self):
        # 普通用户清空：只清自己的
        _s, _l, _p, _dd, _c, status = self.app.do_clear_history(
            self.app.tr("clear_typed_word"), request=self._req(self.ua_token))
        self.assertIsNone(self.history.get_record(self.rec_a))    # 自己的没了
        self.assertIsNotNone(self.history.get_record(self.rec_b))  # 别人的还在
        self.assertIsNotNone(self.history.get_record(self.rec_m))  # 迁移数据还在
        # admin 清空：全库
        _s, _l, _p, _dd, _c, status = self.app.do_clear_history(
            self.app.tr("clear_typed_word"), request=self._req(self.admin_token))
        self.assertIsNone(self.history.get_record(self.rec_b))
        self.assertIsNone(self.history.get_record(self.rec_m))

    # ─── 图表隔离 ────────────────────────────────────
    def test_charts_scoped(self):
        html_all = self.charts.charts_html(owner_user_id=None)
        self.assertIn("base64", html_all)
        html_a = self.charts.charts_html(owner_user_id=self.ua_id)
        self.assertIn("base64", html_a)
        # 空用户 → 占位文本，无图
        empty = self.history.list_records(owner_user_id=999999)
        self.assertEqual(empty, [])
        html_none = self.charts.charts_html(owner_user_id=999999)
        self.assertNotIn("base64", html_none)


if __name__ == "__main__":
    unittest.main(verbosity=2)
