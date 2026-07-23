"""三层记忆系统单元测试"""
import unittest
import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from core.memory_system import MemorySystem


class TestMemorySystem(unittest.TestCase):
    """MemorySystem 测试类"""

    def setUp(self):
        """测试前准备：使用临时目录"""
        self.test_dir = tempfile.mkdtemp()
        # 覆盖配置路径
        config.WARM_MEMORY_FILE = os.path.join(self.test_dir, "warm_memory.json")
        config.COLD_MEMORY_DIR = os.path.join(self.test_dir, "cold_memory")
        self.memory = MemorySystem()

    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # ===== 热记忆测试 =====

    def test_add_hot_memory(self):
        """测试添加热记忆"""
        self.memory.add_hot_memory("用户说要写玄幻小说", "dialogue")
        self.memory.add_hot_memory("确定了主角名字", "decision")

        hot = self.memory.get_hot_memory()
        self.assertEqual(len(hot), 2)
        self.assertEqual(hot[0]["content"], "用户说要写玄幻小说")
        self.assertEqual(hot[0]["type"], "dialogue")
        self.assertEqual(hot[1]["type"], "decision")

    def test_hot_memory_limit(self):
        """测试热记忆上限（100条）"""
        for i in range(120):
            self.memory.add_hot_memory(f"记忆{i}")

        hot = self.memory.get_hot_memory()
        self.assertLessEqual(len(hot), 100)
        # 最后一条应该是 记忆119
        self.assertEqual(hot[-1]["content"], "记忆119")

    def test_get_hot_memory_limit(self):
        """测试获取指定数量热记忆"""
        for i in range(20):
            self.memory.add_hot_memory(f"记忆{i}")

        hot = self.memory.get_hot_memory(limit=5)
        self.assertEqual(len(hot), 5)

    def test_clear_hot_memory(self):
        """测试清空热记忆"""
        self.memory.add_hot_memory("测试内容")
        self.memory.clear_hot_memory()
        self.assertEqual(len(self.memory.hot_memory), 0)

    # ===== 温记忆测试 =====

    def test_user_profile(self):
        """测试用户画像读写"""
        self.memory.update_user_profile("preferred_genre", "玄幻")
        self.memory.update_user_profile("writing_style", "简洁")

        profile = self.memory.get_user_profile()
        self.assertEqual(profile["preferred_genre"], "玄幻")
        self.assertEqual(profile["writing_style"], "简洁")

    def test_user_profile_persistence(self):
        """测试用户画像持久化"""
        self.memory.update_user_profile("preferred_genre", "都市")

        # 重新创建实例，验证持久化
        new_memory = MemorySystem()
        profile = new_memory.get_user_profile()
        self.assertEqual(profile["preferred_genre"], "都市")

    def test_knowledge_index(self):
        """测试知识库索引"""
        self.memory.update_knowledge_index("玄幻", ["升级", "打脸", "宗门"])

        idx = self.memory.get_knowledge_index("玄幻")
        self.assertIn("keywords", idx)
        self.assertIn("升级", idx["keywords"])

    def test_knowledge_index_all(self):
        """测试获取全部知识库索引"""
        self.memory.update_knowledge_index("玄幻", ["升级"])
        self.memory.update_knowledge_index("都市", ["装逼"])

        all_idx = self.memory.get_knowledge_index()
        self.assertIn("玄幻", all_idx)
        self.assertIn("都市", all_idx)

    def test_skill_index(self):
        """测试Skill索引"""
        self.memory.update_skill_index("skill_001", {
            "name": "大纲生成",
            "trigger": "用户要求生成大纲"
        })

        skill = self.memory.get_skill_index("skill_001")
        self.assertEqual(skill["name"], "大纲生成")

    def test_important_decisions(self):
        """测试重要决策记录"""
        self.memory.add_important_decision("选择玄幻题材", "用户偏好")
        self.memory.add_important_decision("主角为男性", "用户指定")

        decisions = self.memory.get_important_decisions()
        self.assertEqual(len(decisions), 2)
        self.assertEqual(decisions[0]["decision"], "选择玄幻题材")

    def test_important_decisions_limit(self):
        """测试决策记录上限（50条）"""
        for i in range(60):
            self.memory.add_important_decision(f"决策{i}")

        decisions = self.memory.get_important_decisions()
        self.assertLessEqual(len(decisions), 50)

    # ===== 冷记忆测试 =====

    def test_add_and_get_cold_memory(self):
        """测试添加和获取冷记忆"""
        self.memory.add_cold_memory(
            chapter_num=1,
            summary="第一章：主角觉醒，获得系统",
            key_events=["觉醒", "系统激活"]
        )

        data = self.memory.get_cold_memory(1)
        self.assertIsNotNone(data)
        self.assertEqual(data["chapter_num"], 1)
        self.assertIn("觉醒", data["summary"])
        self.assertIn("觉醒", data["key_events"])

    def test_get_nonexistent_cold_memory(self):
        """测试获取不存在的冷记忆"""
        data = self.memory.get_cold_memory(999)
        self.assertIsNone(data)

    def test_search_cold_memory(self):
        """测试搜索冷记忆"""
        self.memory.add_cold_memory(1, "主角在宗门觉醒", ["觉醒"])
        self.memory.add_cold_memory(2, "主角参加比赛", ["比赛"])
        self.memory.add_cold_memory(3, "主角突破境界", ["突破"])

        results = self.memory.search_cold_memory("觉醒")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["chapter_num"], 1)

    def test_search_cold_memory_by_event(self):
        """测试通过关键事件搜索冷记忆"""
        self.memory.add_cold_memory(1, "第一章内容", ["觉醒", "系统"])
        self.memory.add_cold_memory(2, "第二章内容", ["比赛"])

        results = self.memory.search_cold_memory("系统")
        self.assertEqual(len(results), 1)

    def test_get_recent_cold_memory(self):
        """测试获取最近冷记忆"""
        for i in range(1, 11):
            self.memory.add_cold_memory(i, f"第{i}章摘要")

        recent = self.memory.get_recent_cold_memory(limit=3)
        self.assertEqual(len(recent), 3)
        # 最近的应该在前面
        self.assertEqual(recent[0]["chapter_num"], 10)

    # ===== 记忆沉淀测试 =====

    def test_settle_memories(self):
        """测试记忆沉淀"""
        self.memory.add_hot_memory("用户决定写玄幻", "decision")
        self.memory.add_hot_memory("普通对话", "dialogue")

        self.memory.settle_memories()

        # 热记忆应被清空
        self.assertEqual(len(self.memory.hot_memory), 0)

        # 决策应转入温记忆
        decisions = self.memory.get_important_decisions()
        self.assertGreaterEqual(len(decisions), 1)

    def test_settle_empty_memories(self):
        """测试空热记忆沉淀"""
        self.memory.settle_memories()
        # 不应报错
        self.assertEqual(len(self.memory.hot_memory), 0)

    # ===== 综合查询测试 =====

    def test_get_context_for_generation(self):
        """测试生成上下文"""
        self.memory.add_hot_memory("测试对话", "dialogue")
        self.memory.update_user_profile("genre", "玄幻")
        self.memory.add_cold_memory(1, "第一章摘要")

        context = self.memory.get_context_for_generation(2)

        self.assertIn("hot_memory", context)
        self.assertIn("user_profile", context)
        self.assertIn("previous_chapter", context)
        self.assertEqual(context["previous_chapter"]["chapter_num"], 1)

    def test_get_context_no_previous(self):
        """测试第一章无前一章上下文"""
        context = self.memory.get_context_for_generation(1)
        self.assertNotIn("previous_chapter", context)

    # ===== 统计信息测试 =====

    def test_get_memory_stats(self):
        """测试记忆统计"""
        self.memory.add_hot_memory("测试")
        self.memory.add_cold_memory(1, "摘要")
        self.memory.add_important_decision("决策")

        stats = self.memory.get_memory_stats()
        self.assertIn("hot_memory_count", stats)
        self.assertIn("cold_memory_count", stats)
        self.assertIn("important_decisions_count", stats)
        self.assertEqual(stats["hot_memory_count"], 1)
        self.assertEqual(stats["cold_memory_count"], 1)


if __name__ == '__main__':
    unittest.main()
