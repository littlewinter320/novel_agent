"""VersionManager 单元测试"""
import os
import sys
import json
import shutil
import tempfile
import unittest

# 确保可以导入项目模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.version_manager import VersionManager


class TestVersionManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.vm = VersionManager(versions_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # ---------- create_snapshot / list_versions ----------
    def test_create_and_list(self):
        v1 = self.vm.create_snapshot("outline", {"title": "测试小说"}, "初始大纲")
        self.assertEqual(v1, "v1")

        v2 = self.vm.create_snapshot("outline", {"title": "测试小说v2"}, "修改大纲")
        self.assertEqual(v2, "v2")

        versions = self.vm.list_versions("outline")
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0]["version"], "v1")
        self.assertEqual(versions[1]["version"], "v2")

    def test_sub_version(self):
        self.vm.create_snapshot("outline", {"title": "v1"}, "初始")
        v1_1 = self.vm.create_snapshot(
            "outline", {"title": "v1.1"}, "小修改", parent_version="v1"
        )
        self.assertEqual(v1_1, "v1.1")

        v1_2 = self.vm.create_snapshot(
            "outline", {"title": "v1.2"}, "再次修改", parent_version="v1"
        )
        self.assertEqual(v1_2, "v1.2")

    def test_different_content_types(self):
        v1 = self.vm.create_snapshot("outline", {"a": 1}, "大纲")
        v2 = self.vm.create_snapshot("chapter", {"b": 2}, "章节")
        # 不同类型独立编号
        self.assertEqual(v1, "v1")
        self.assertEqual(v2, "v1")

        all_versions = self.vm.list_versions()
        self.assertEqual(len(all_versions), 2)

        outline_versions = self.vm.list_versions("outline")
        self.assertEqual(len(outline_versions), 1)

    # ---------- load_version ----------
    def test_load_version(self):
        self.vm.create_snapshot("outline", {"title": "hello"}, "初始")
        loaded = self.vm.load_version("v1")
        self.assertEqual(loaded["content"]["title"], "hello")
        self.assertEqual(loaded["version"], "v1")

    def test_load_nonexistent(self):
        with self.assertRaises(ValueError):
            self.vm.load_version("v999")

    # ---------- compare ----------
    def test_compare_modified(self):
        self.vm.create_snapshot("outline", {"title": "A", "desc": "same"}, "v1")
        self.vm.create_snapshot("outline", {"title": "B", "desc": "same"}, "v2")
        result = self.vm.compare("v1", "v2")
        self.assertIn("title", result["changes"])
        self.assertEqual(result["changes"]["title"]["type"], "modified")
        self.assertNotIn("desc", result["changes"])

    def test_compare_added_removed(self):
        self.vm.create_snapshot("outline", {"a": 1}, "v1")
        self.vm.create_snapshot("outline", {"a": 1, "b": 2}, "v2")
        result = self.vm.compare("v1", "v2")
        self.assertEqual(result["changes"]["b"]["type"], "added")

    def test_compare_text_diff(self):
        text1 = "第一行\n第二行\n第三行"
        text2 = "第一行\n修改行\n第三行\n第四行"
        self.vm.create_snapshot("chapter", {"text": text1}, "v1")
        self.vm.create_snapshot("chapter", {"text": text2}, "v2")
        result = self.vm.compare("v1", "v2")
        self.assertIn("text", result["changes"])
        self.assertTrue(len(result["changes"]["text"]["diff"]) > 0)

    def test_compare_summary(self):
        self.vm.create_snapshot("outline", {"a": 1}, "v1")
        self.vm.create_snapshot("outline", {"b": 2}, "v2")
        result = self.vm.compare("v1", "v2")
        # a removed, b added
        self.assertIn("新增", result["summary"])
        self.assertIn("删除", result["summary"])

    # ---------- rollback ----------
    def test_rollback(self):
        self.vm.create_snapshot("outline", {"title": "v1"}, "初始")
        self.vm.create_snapshot("outline", {"title": "v2"}, "修改")
        content = self.vm.rollback("v1")
        self.assertEqual(content["title"], "v1")

        # 回滚后会创建新版本
        versions = self.vm.list_versions("outline")
        self.assertEqual(len(versions), 3)

    # ---------- partial_rollback ----------
    def test_partial_rollback(self):
        self.vm.create_snapshot("outline", {"title": "v1", "chars": "角色A"}, "v1")
        self.vm.create_snapshot("outline", {"title": "v2", "chars": "角色B"}, "v2")
        # 部分回滚到 v1，但保留 chars 字段（来自最新 v2）
        new_ver = self.vm.partial_rollback("v1", ["chars"])
        loaded = self.vm.load_version(new_ver)
        self.assertEqual(loaded["content"]["title"], "v1")
        self.assertEqual(loaded["content"]["chars"], "角色B")

    # ---------- mixed version ----------
    def test_mixed_version(self):
        self.vm.create_snapshot("outline", {"structure": "三幕", "chars": "旧角色"}, "v1")
        self.vm.create_snapshot("outline", {"structure": "五幕", "chars": "新角色"}, "v2")
        # 混合：v1 的结构 + v2 的角色
        ver = self.vm.create_mixed_version(
            sources={"v1": ["structure"], "v2": ["chars"]},
            content_type="outline",
            change_summary="混合版本",
        )
        loaded = self.vm.load_version(ver)
        self.assertEqual(loaded["content"]["structure"], "三幕")
        self.assertEqual(loaded["content"]["chars"], "新角色")
        self.assertIn("mixed", ver)

    # ---------- 文件持久化 ----------
    def test_file_persistence(self):
        self.vm.create_snapshot("outline", {"title": "test"}, "初始")
        # 检查文件存在
        files = [f for f in os.listdir(self.test_dir) if f.endswith(".json") and f != "_index.json"]
        self.assertEqual(len(files), 1)
        self.assertIn("v1", files[0])
        self.assertIn("outline", files[0])

        # 检查索引文件
        with open(os.path.join(self.test_dir, "_index.json"), "r", encoding="utf-8") as f:
            idx = json.load(f)
        self.assertEqual(len(idx["versions"]), 1)

    # ---------- 重新加载 ----------
    def test_reload_from_disk(self):
        self.vm.create_snapshot("outline", {"title": "test"}, "初始")
        # 创建新的 VersionManager 实例，应该能从磁盘加载索引
        vm2 = VersionManager(versions_dir=self.test_dir)
        versions = vm2.list_versions()
        self.assertEqual(len(versions), 1)
        loaded = vm2.load_version("v1")
        self.assertEqual(loaded["content"]["title"], "test")


if __name__ == "__main__":
    unittest.main()
