"""导出测试：四格式生成与文件头、预设差异、路径安全、任务状态流转、过期清理、权限。"""
import os
import sys
import csv
import json
import shutil
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import i18n

REPORT = {
    i18n.SECTION_CAPTION: {"图像编号": "IMG-007"},
    i18n.SECTION_COMPONENT: {"构件名称": "叶片", "图像清晰度": "清晰"},
    i18n.SECTION_DAMAGE: {"是否存在损伤": "是", "损伤类型": "涂层破损",
                          "损伤程度": "中度"},
    i18n.SECTION_RISK: {"潜在风险": "涂层破损扩大"},
    i18n.SECTION_OM: {"处置建议": "计划性修复"},
    i18n.SECTION_UNCERTAINTY: {"不确定性说明": "图像角度受限"},
    i18n.SECTION_CONCLUSION: {"巡检优先级": "中", "本次判断的置信度": "高"},
}


class TestReportExport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.out = os.path.join(self.tmp, "exports")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _rec(self):
        return {"id": 7, "image_name": "blade_03.jpg", "timestamp": "2026-11-06 10:00:00",
                "infer_time": 3.2, "note": "待复查", "source": "ui"}

    def test_all_four_formats(self):
        import report_export as re_
        for fmt, magic in (("pdf", b"%PDF"), ("docx", b"PK"),
                           ("xlsx", b"PK"), ("csv", b"\xef\xbb\xbf")):
            path = re_.generate_export(fmt, REPORT, self._rec(), preset="standard",
                                       out_dir=self.out)
            self.assertTrue(os.path.exists(path), fmt)
            with open(path, "rb") as f:
                head = f.read(4)
            self.assertTrue(head.startswith(magic), f"{fmt}: {head!r}")
            self.assertTrue(os.path.getsize(path) > 200, fmt)

    def test_presets_change_content(self):
        import report_export as re_
        full = re_.build_content(REPORT, self._rec(), preset="full", lang="zh")
        brief = re_.build_content(REPORT, self._rec(), preset="brief", lang="zh")
        std = re_.build_content(REPORT, self._rec(), preset="standard", lang="zh")
        # full：全部 7 个区块 + 原始 JSON + 备注
        self.assertEqual(len(full["sections"]), 7)
        self.assertIn("涂层破损", full["raw_json"])
        self.assertEqual(full["note"], "待复查")
        # brief：只含 构件识别/损伤判定/结论建议 3 个区块，无 JSON
        self.assertEqual(len(brief["sections"]), 3)
        self.assertEqual(brief["raw_json"], "")
        # standard：5 个区块（无不确定性、无结论建议）
        self.assertEqual(len(std["sections"]), 5)
        self.assertEqual(std["raw_json"], "")
        titles = " ".join(t for t, _ in std["sections"])
        self.assertNotIn(i18n.section_title(i18n.SECTION_CONCLUSION), titles)
        self.assertNotIn(i18n.section_title(i18n.SECTION_UNCERTAINTY), titles)

    def test_export_language_independent(self):
        import report_export as re_
        zh = re_.build_content(REPORT, self._rec(), preset="brief", lang="zh")
        en = re_.build_content(REPORT, self._rec(), preset="brief", lang="en")
        zh_titles = " ".join(t for t, _ in zh["sections"])
        en_titles = " ".join(t for t, _ in en["sections"])
        self.assertIn(i18n.section_title(i18n.SECTION_COMPONENT, lang="zh"), zh_titles)
        self.assertIn("Component", en_titles)
        # 值翻译：是 → Yes
        en_vals = " ".join(v for _, f in en["sections"] for _, v in f)
        self.assertIn("Yes", en_vals)

    def test_bad_format_rejected(self):
        import report_export as re_
        with self.assertRaises(ValueError):
            re_.generate_export("exe", REPORT, self._rec(), out_dir=self.out)

    def test_bad_preset_falls_back(self):
        import report_export as re_
        c = re_.build_content(REPORT, self._rec(), preset="hacker", lang="zh")
        self.assertEqual(len(c["sections"]), 5)  # 回落 standard

    def test_cleanup_expired_files(self):
        import report_export as re_
        old = os.path.join(self.out, "export_old_standard_x.csv")
        new = os.path.join(self.out, "export_new_standard_x.csv")
        os.makedirs(self.out, exist_ok=True)
        for p in (old, new):
            with open(p, "w") as f:
                f.write("x")
        past = (datetime.now() - timedelta(days=re_.TASK_EXPIRE_DAYS + 1)).timestamp()
        os.utime(old, (past, past))
        n = re_.cleanup_expired(out_dir=self.out)
        self.assertEqual(n, 1)
        self.assertFalse(os.path.exists(old))
        self.assertTrue(os.path.exists(new))


class TestExportTasks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "history.db")
        os.environ["WD_DB_PATH"] = self.db
        # 导出目录也指向临时区
        import report_export
        self._orig_out = report_export.EXPORTS_DIR
        report_export.EXPORTS_DIR = os.path.join(self.tmp, "exports")

        import history, auth, export_tasks as xt
        self.history, self.auth, self.xt = history, auth, xt
        history.init_db()
        self.admin_id = auth.create_user("exp_admin", "Passw0rd1", role="admin")
        self.ua_id = auth.create_user("exp_user_a", "Passw0rd1")
        self.ub_id = auth.create_user("exp_user_b", "Passw0rd1")
        self.rec_a = history.save_record("a.jpg", REPORT, source="ui",
                                         owner_user_id=self.ua_id)
        self.rec_b = history.save_record("b.jpg", REPORT, source="ui",
                                         owner_user_id=self.ub_id)

    def tearDown(self):
        os.environ.pop("WD_DB_PATH", None)
        import report_export
        report_export.EXPORTS_DIR = self._orig_out
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_task_lifecycle_pending_run_done(self):
        tid = self.xt.create_task(self.ua_id, self.rec_a, "pdf", "standard")
        t = self.xt.get_task(tid)
        self.assertEqual(t["status"], "pending")
        t = self.xt.run_task(tid, self.ua_id, is_admin=False)
        self.assertEqual(t["status"], "done", t["error"])
        self.assertTrue(os.path.exists(t["file_path"]))
        self.assertTrue(t["file_path"].endswith(".pdf"))
        self.assertTrue(t["expires_at"])  # 有过期时间（§11.2）

    def test_user_cannot_export_others_record(self):
        tid = self.xt.create_task(self.ub_id, self.rec_a, "csv", "standard")
        t = self.xt.run_task(tid, self.ub_id, is_admin=False)
        self.assertEqual(t["status"], "failed")
        self.assertEqual(t["error"], "msg_record_no_access")
        # admin（角色授权）可以导出任意记录
        tid2 = self.xt.create_task(self.admin_id, self.rec_a, "csv", "standard")
        t2 = self.xt.run_task(tid2, self.admin_id, is_admin=True)
        self.assertEqual(t2["status"], "done", t2["error"])

    def test_task_list_isolation(self):
        self.xt.create_task(self.ua_id, self.rec_a, "csv", "standard")
        self.xt.create_task(self.ub_id, self.rec_b, "csv", "standard")
        mine = self.xt.list_tasks(owner_user_id=self.ua_id)
        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0]["user_id"], self.ua_id)
        everyone = self.xt.list_tasks(owner_user_id=None)
        self.assertEqual(len(everyone), 2)

    def test_retry_failed_task(self):
        tid = self.xt.create_task(self.ub_id, self.rec_a, "csv", "standard")  # 越权 → failed
        self.xt.run_task(tid, self.ub_id, is_admin=False)
        # admin 重试：权限变成 admin 视角 → 成功
        t = self.xt.retry_task(tid, self.admin_id, is_admin=True)
        self.assertEqual(t["status"], "done", t["error"])
        # 正常任务重试是 no-op（只允许 failed/expired）
        t2 = self.xt.retry_task(tid, self.admin_id, is_admin=True)
        self.assertEqual(t2["status"], "done")

    def test_expiry_marking_and_cleanup(self):
        tid = self.xt.create_task(self.ua_id, self.rec_a, "csv", "standard")
        self.xt.run_task(tid, self.ua_id, is_admin=False)
        # 把 expires_at 改到过去 → mark → expired
        past = (datetime.now() - timedelta(days=1)).strftime(self.xt._TIME_FMT)
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE export_tasks SET expires_at = ? WHERE id = ?", (past, tid))
        conn.commit()
        conn.close()
        self.assertEqual(self.xt.mark_expired_tasks(), 1)
        self.assertEqual(self.xt.get_task(tid)["status"], "expired")
        # 过期任务可重新生成
        t = self.xt.retry_task(tid, self.ua_id, is_admin=False)
        self.assertEqual(t["status"], "done", t["error"])

    def test_missing_file_marks_expired(self):
        tid = self.xt.create_task(self.ua_id, self.rec_a, "csv", "standard")
        t = self.xt.run_task(tid, self.ua_id, is_admin=False)
        os.remove(t["file_path"])
        self.assertEqual(self.xt.mark_expired_tasks(), 1)
        self.assertEqual(self.xt.get_task(tid)["status"], "expired")

    def test_delete_task_scoped(self):
        tid = self.xt.create_task(self.ua_id, self.rec_a, "csv", "standard")
        self.assertFalse(self.xt.delete_task(tid, self.ub_id, is_admin=False))
        self.assertTrue(self.xt.delete_task(tid, self.ua_id, is_admin=False))
        self.assertIsNone(self.xt.get_task(tid))

    def test_bad_fmt_preset_rejected(self):
        with self.assertRaises(AssertionError):
            self.xt.create_task(self.ua_id, self.rec_a, "exe", "standard")
        with self.assertRaises(AssertionError):
            self.xt.create_task(self.ua_id, self.rec_a, "pdf", "whatever")


if __name__ == "__main__":
    unittest.main(verbosity=2)
