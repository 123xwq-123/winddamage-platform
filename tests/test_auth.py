"""认证模块测试：口令哈希/校验、失败锁定、会话生命周期、校验规则、迁移回填。"""
import os
import sys
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAuth(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "history.db")
        os.environ["WD_DB_PATH"] = self.db
        import history, auth, migrate
        self.history, self.auth, self.migrate = history, auth, migrate
        history.init_db()

    def tearDown(self):
        os.environ.pop("WD_DB_PATH", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ─── 口令哈希 ─────────────────────────────────────
    def test_hash_and_verify(self):
        salt, h = self.auth.hash_password("S3cret99x")
        self.assertNotEqual(salt, h)
        self.assertEqual(len(salt), 32)   # 16 bytes hex
        self.assertTrue(self.auth.verify_password("S3cret99x", salt, h))
        self.assertFalse(self.auth.verify_password("wrongpass", salt, h))

    def test_hash_salt_unique(self):
        s1, h1 = self.auth.hash_password("same-password1")
        s2, h2 = self.auth.hash_password("same-password1")
        self.assertNotEqual(s1, s2)
        self.assertNotEqual(h1, h2)

    def test_verify_bad_hex_returns_false(self):
        salt, h = self.auth.hash_password("whatever1")
        self.assertFalse(self.auth.verify_password("x", "zz-nothex", h))
        self.assertFalse(self.auth.verify_password("x", salt, "short"))

    # ─── 校验规则 ─────────────────────────────────────
    def test_username_rules(self):
        ok_names = ["admin", "巡检员小李", "user_01", "a-b-c-d"]
        for n in ok_names:
            self.assertIsNone(self.auth.username_issue(n), n)
        bad = ["ab", "x" * 41, "含空格 名称", "bad!name", ""]
        for n in bad:
            self.assertEqual(self.auth.username_issue(n), "auth_username_invalid", n)

    def test_username_normalized_lowercase(self):
        uid = self.auth.create_user("MixEDCase", "Passw0rd1")
        u = self.auth.get_user(uid)
        self.assertEqual(u["username"], "mixedcase")
        # 大小写不敏感：查得到
        self.assertIsNotNone(self.auth.get_user_by_name("MIXEDCASE"))
        with self.assertRaises(self.auth.UsernameExists):
            self.auth.create_user("mixedcase", "Passw0rd2")

    def test_password_rules(self):
        self.assertEqual(self.auth.password_issues("short1"), ["auth_pw_len"])
        self.assertEqual(self.auth.password_issues("nodigitshere"), ["auth_pw_digit"])
        self.assertEqual(self.auth.password_issues("12345678"), ["auth_pw_letter"])
        self.assertEqual(self.auth.password_issues("GoodPass1"), [])

    def test_create_user_strips_password_fields(self):
        uid = self.auth.create_user("tester01", "Passw0rd1", role="admin")
        u = self.auth.get_user(uid)
        self.assertNotIn("pw_hash", u)
        self.assertNotIn("pw_salt", u)
        self.assertEqual(u["role"], "admin")

    # ─── 登录 / 锁定 ─────────────────────────────────
    def test_authenticate_ok_and_failed(self):
        self.auth.create_user("locker01", "Passw0rd1")
        status, user = self.auth.authenticate("locker01", "Passw0rd1")
        self.assertEqual(status, "ok")
        self.assertEqual(user["username"], "locker01")
        status, payload = self.auth.authenticate("locker01", "WrongPass1")
        self.assertEqual(status, "failed")
        # 不存在用户：同样的模糊提示，不区分
        status2, payload2 = self.auth.authenticate("ghost-user", "WrongPass1")
        self.assertEqual(status2, "failed")

    def test_lockout_after_5_failures(self):
        self.auth.create_user("locker02", "Passw0rd1")
        for i in range(4):
            status, payload = self.auth.authenticate("locker02", "WrongPass1")
            self.assertEqual(status, "failed")
            self.assertEqual(payload, 4 - i)  # 递减的剩余次数
        # 第 5 次 → 锁定
        status, payload = self.auth.authenticate("locker02", "WrongPass1")
        self.assertEqual(status, "locked")
        self.assertEqual(payload, self.auth.LOCK_MINUTES)
        # 锁定期内：正确密码也拒绝
        status, payload = self.auth.authenticate("locker02", "Passw0rd1")
        self.assertEqual(status, "locked")
        # 解锁后恢复
        self.auth.unlock_user(self.auth.get_user_by_name("locker02")["id"])
        status, payload = self.auth.authenticate("locker02", "Passw0rd1")
        self.assertEqual(status, "ok")

    def test_lockout_expiry_resets(self):
        self.auth.create_user("locker03", "Passw0rd1")
        for _ in range(5):
            self.auth.authenticate("locker03", "WrongPass1")
        # 手动把 locked_until 改成已过期
        import sqlite3
        past = (datetime.now() - timedelta(minutes=1)).strftime(self.auth._TIME_FMT)
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE users SET locked_until = ? WHERE username = ?",
                     (past, "locker03"))
        conn.commit()
        conn.close()
        status, user = self.auth.authenticate("locker03", "Passw0rd1")
        self.assertEqual(status, "ok")

    def test_disabled_user_cannot_login(self):
        uid = self.auth.create_user("disabled1", "Passw0rd1")
        self.auth.set_user_active(uid, False)
        status, payload = self.auth.authenticate("disabled1", "Passw0rd1")
        self.assertEqual(status, "failed")

    # ─── 会话 ────────────────────────────────────────
    def test_session_lifecycle(self):
        uid = self.auth.create_user("sessuser1", "Passw0rd1")
        token = self.auth.create_session(uid)
        u = self.auth.get_session_user(token)
        self.assertIsNotNone(u)
        self.assertEqual(u["id"], uid)
        self.auth.revoke_session(token)
        self.assertIsNone(self.auth.get_session_user(token))

    def test_session_expiry(self):
        uid = self.auth.create_user("sessuser2", "Passw0rd1")
        token = self.auth.create_session(uid)
        import sqlite3
        past = (datetime.now() - timedelta(hours=1)).strftime(self.auth._TIME_FMT)
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE sessions SET expires_at = ? WHERE token = ?", (past, token))
        conn.commit()
        conn.close()
        self.assertIsNone(self.auth.get_session_user(token))

    def test_session_revoked_on_password_change(self):
        uid = self.auth.create_user("sessuser3", "Passw0rd1")
        t1 = self.auth.create_session(uid)
        t2 = self.auth.create_session(uid)
        ok, err = self.auth.change_password(uid, "Passw0rd1", "NewPassw0rd9",
                                            current_token=t1)
        self.assertTrue(ok, err)
        self.assertIsNotNone(self.auth.get_session_user(t1))  # 当前会话保留
        self.assertIsNone(self.auth.get_session_user(t2))     # 其他会话吊销
        # 新密码可登录，旧密码不行
        self.assertEqual(self.auth.authenticate("sessuser3", "NewPassw0rd9")[0], "ok")
        self.assertEqual(self.auth.authenticate("sessuser3", "Passw0rd1")[0], "failed")

    def test_cookie_parse_and_user_for_request(self):
        uid = self.auth.create_user("cookuser1", "Passw0rd1")
        token = self.auth.create_session(uid)

        class FakeRequest:
            headers = {"cookie": f"other=1; {self.auth.SESSION_COOKIE}={token}"}

        u = self.auth.user_for_request(FakeRequest())
        self.assertEqual(u["id"], uid)
        # 无 cookie / 无效 token
        class EmptyReq:
            headers = {}
        self.assertIsNone(self.auth.user_for_request(EmptyReq()))
        self.assertIsNone(self.auth.user_for_request(None))

    # ─── 管理操作 ────────────────────────────────────
    def test_reset_password_and_role(self):
        uid = self.auth.create_user("adminop1", "Passw0rd1")
        old_token = self.auth.create_session(uid)
        self.assertIsNone(self.auth.reset_password(uid, "ResetPass9"))
        self.assertIsNone(self.auth.get_session_user(old_token))  # 重置后吊销会话
        self.assertEqual(self.auth.authenticate("adminop1", "ResetPass9")[0], "ok")
        self.auth.set_user_role(uid, "admin")
        self.assertEqual(self.auth.get_user(uid)["role"], "admin")
        with self.assertRaises(ValueError):
            self.auth.set_user_role(uid, "superadmin")
        # 重置弱密码报错
        self.assertEqual(self.auth.reset_password(uid, "weak"), "auth_pw_len")

    # ─── 迁移数据回填（§13.1）─────────────────────────
    def test_backfill_migration_owner(self):
        rid1 = self.history.save_record("m1.jpg", {"2. 损伤判定": {"是否存在损伤": "是"}},
                                        source="migration")
        rid2 = self.history.save_record("m2.jpg", {"2. 损伤判定": {"是否存在损伤": "否"}},
                                        source="migration")
        rid3 = self.history.save_record("ui.jpg", {"2. 损伤判定": {"是否存在损伤": "否"}},
                                        source="ui")
        admin_id = self.auth.create_user("backadmin", "Passw0rd1", role="admin")
        n = self.auth.backfill_migration_owner("backadmin")
        self.assertEqual(n, 2)
        r1 = self.history.get_record(rid1)
        self.assertEqual(r1["owner_user_id"], admin_id)
        self.assertEqual(r1["source"], "migration")  # source 保留迁移标识
        r3 = self.history.get_record(rid3)
        self.assertIsNone(r3["owner_user_id"])       # 非 migration 不动
        # 不存在的用户名 → 0
        self.assertEqual(self.auth.backfill_migration_owner("ghost"), 0)

    def test_backfill_by_username_not_id(self):
        """admin id 不假设为 1：回填目标按用户名查询。"""
        other_id = self.auth.create_user("plainuser1", "Passw0rd1")
        self.history.save_record("m3.jpg", {}, source="migration")
        admin_id = self.auth.create_user("realadmin1", "Passw0rd1", role="admin")
        self.assertGreater(admin_id, other_id)  # 确实不是 1 号
        self.auth.backfill_migration_owner("realadmin1")
        rows = self.history.list_records(owner_user_id=admin_id)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["image_name"], "m3.jpg")


if __name__ == "__main__":
    unittest.main(verbosity=2)
