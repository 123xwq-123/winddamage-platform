"""history 数据层测试：筛选/排序/分页、删除分级、图片引用计数、权限判定。"""
import os
import sys
import json
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPORT_HIGH = {"1. 构件识别": {"构件名称": "叶片"},
               "2. 损伤判定": {"是否存在损伤": "是", "损伤类型": "裂纹"},
               "6. 结论建议": {"巡检优先级": "高", "本次判断的置信度": "高"}}
REPORT_LOW = {"1. 构件识别": {"构件名称": "塔筒"},
              "2. 损伤判定": {"是否存在损伤": "否", "损伤类型": "无"},
              "6. 结论建议": {"巡检优先级": "低", "本次判断的置信度": "高"}}


class TestHistory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "history.db")
        os.environ["WD_DB_PATH"] = self.db
        import history
        import migrate
        import image_store
        self.history, self.migrate, self.image_store = history, migrate, image_store
        history.init_db()  # 建 v1 表 + 迁移
        # 图片目录指到临时区，避免污染真实 persisted_images/
        self._orig_store = image_store.STORE_DIR
        image_store.STORE_DIR = os.path.join(self.tmp, "persisted_images")

    def tearDown(self):
        os.environ.pop("WD_DB_PATH", None)
        self.image_store.STORE_DIR = self._orig_store
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _img(self, name, content=b"fake-image-bytes-A"):
        p = os.path.join(self.tmp, name)
        with open(p, "wb") as f:
            f.write(content)
        return p

    def test_save_and_query_scoping(self):
        h = self.history
        h.save_record("a.jpg", REPORT_HIGH, 1.0, source="ui", owner_user_id=7)
        h.save_record("b.jpg", REPORT_LOW, 2.0, source="ui", owner_user_id=7)
        h.save_record("c.jpg", REPORT_HIGH, 3.0, source="ui", owner_user_id=9)
        rows, total = h.query_records(owner_user_id=7)
        self.assertEqual(total, 2)
        rows, total = h.query_records(owner_user_id=9)
        self.assertEqual(total, 1)
        rows, total = h.query_records()  # admin 视角全量
        self.assertEqual(total, 3)

    def test_filters_and_sort(self):
        h = self.history
        h.save_record("a.jpg", REPORT_HIGH, 1.0, source="ui", owner_user_id=7)
        h.save_record("b.jpg", REPORT_LOW, 5.0, source="ui", owner_user_id=7)
        rows, total = h.query_records(owner_user_id=7, risk="high")
        self.assertEqual(total, 1)
        self.assertEqual(rows[0]["image_name"], "a.jpg")
        rows, total = h.query_records(owner_user_id=7, search="b")
        self.assertEqual(total, 1)
        rows, total = h.query_records(owner_user_id=7, sort="infer_time_desc")
        self.assertEqual(rows[0]["image_name"], "b.jpg")

    def test_delete_releases_image_only_when_unref(self):
        h = self.history
        img = self._img("same.jpg")
        rid1 = h.save_record("r1.jpg", REPORT_HIGH, 1.0, img,
                             source="ui", owner_user_id=7, persist_image=True)
        rid2 = h.save_record("r2.jpg", REPORT_LOW, 1.0, img,
                             source="ui", owner_user_id=7, persist_image=True)
        r1 = h.get_record(rid1)
        fid = r1["image_file_id"]
        self.assertEqual(fid, h.get_record(rid2)["image_file_id"])  # sha 去重复用
        store = os.path.join(self.tmp, "persisted_images")
        files = os.listdir(store)
        self.assertEqual(len(files), 1)
        h.delete_record(rid1)
        self.assertEqual(len(os.listdir(store)), 1)  # 仍被 r2 引用
        h.delete_record(rid2)
        self.assertEqual(len(os.listdir(store)), 0)  # 归零物理删除
        self.assertIsNone(self.image_store.get_image_path(fid))

    def test_clear_user_scope_only(self):
        h = self.history
        h.save_record("a.jpg", REPORT_HIGH, 1.0, source="ui", owner_user_id=7)
        h.save_record("b.jpg", REPORT_LOW, 1.0, source="ui", owner_user_id=9)
        n = h.clear_user_records(7)
        self.assertEqual(n, 1)
        rows, total = h.query_records()
        self.assertEqual(total, 1)
        self.assertEqual(rows[0]["owner_user_id"], 9)

    def test_permission_can_access(self):
        h = self.history
        rec = {"owner_user_id": 7}
        self.assertTrue(h.can_access(rec, 7, is_admin=False))
        self.assertFalse(h.can_access(rec, 8, is_admin=False))
        self.assertTrue(h.can_access(rec, 8, is_admin=True))
        migrated = {"owner_user_id": None}
        self.assertFalse(h.can_access(migrated, 7, is_admin=False))
        self.assertTrue(h.can_access(migrated, None, is_admin=True))

    def test_update_note(self):
        h = self.history
        rid = h.save_record("a.jpg", REPORT_LOW, 1.0, source="ui", owner_user_id=7)
        self.assertTrue(h.update_note(rid, "复查过了"))
        self.assertEqual(h.get_record(rid)["note"], "复查过了")


if __name__ == "__main__":
    unittest.main()
