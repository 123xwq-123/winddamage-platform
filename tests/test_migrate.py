"""迁移测试：v2–v4 幂等、数据保全、回滚。"""
import os
import sys
import json
import shutil
import sqlite3
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import migrate  # noqa: E402


def _make_v1_db(path):
    """构造一个 v1 结构（原始 detections）并塞入 37 条样例记录。"""
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL, image_name TEXT NOT NULL, image_path TEXT,
            high_risk INTEGER DEFAULT 0, has_damage TEXT, damage_type TEXT,
            component TEXT, priority TEXT, confidence TEXT,
            json_report TEXT NOT NULL, infer_time REAL
        )
    """)
    for i in range(37):
        conn.execute(
            "INSERT INTO detections (timestamp, image_name, high_risk, json_report, infer_time)"
            " VALUES (?, ?, ?, ?, ?)",
            (f"2025-01-{(i % 28) + 1:02d} 10:00:00", f"blade_{i:03d}.jpg", i % 2,
             json.dumps({"t": i}), 1.5),
        )
    conn.commit()
    conn.close()


class TestMigrate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "history.db")
        os.environ["WD_DB_PATH"] = self.db
        _make_v1_db(self.db)

    def tearDown(self):
        os.environ.pop("WD_DB_PATH", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _snapshot(self):
        conn = sqlite3.connect(self.db)
        rows = conn.execute(
            "SELECT id, timestamp, image_name, high_risk, json_report FROM detections"
            " ORDER BY id").fetchall()
        conn.close()
        return rows

    def test_migrates_to_latest_and_preserves_records(self):
        applied = migrate.migrate()
        self.assertEqual(applied, [2, 3, 4])
        rows = self._snapshot()
        self.assertEqual(len(rows), 37)
        # 字段值一致
        self.assertEqual(rows[0][1], "2025-01-01 10:00:00")
        self.assertEqual(rows[0][2], "blade_000.jpg")
        # 旧记录标记 + 归属待认领
        conn = sqlite3.connect(self.db)
        n_mig = conn.execute(
            "SELECT COUNT(*) FROM detections WHERE source='migration'").fetchone()[0]
        n_null = conn.execute(
            "SELECT COUNT(*) FROM detections WHERE owner_user_id IS NULL").fetchone()[0]
        conn.close()
        self.assertEqual(n_mig, 37)
        self.assertEqual(n_null, 37)

    def test_idempotent(self):
        migrate.migrate()
        before = self._snapshot()
        applied = migrate.migrate()  # 重复执行
        self.assertEqual(applied, [])
        self.assertEqual(before, self._snapshot())

    def test_backup_and_rollback(self):
        migrate.migrate()
        bak = migrate.latest_backup(self.db)
        self.assertIsNotNone(bak)
        # 破坏后还原
        conn = sqlite3.connect(self.db)
        conn.execute("DELETE FROM detections")
        conn.commit()
        conn.close()
        migrate.restore_backup(self.db)
        self.assertEqual(len(self._snapshot()), 37)

    def test_v2_columns_exist(self):
        migrate.migrate(target=2)
        conn = sqlite3.connect(self.db)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(detections)")}
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        for c in ("note", "owner_user_id", "created_by", "source", "image_file_id"):
            self.assertIn(c, cols)
        self.assertIn("image_files", tables)


if __name__ == "__main__":
    unittest.main()
