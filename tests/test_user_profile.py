"""用户画像系统单元测试"""
import unittest
import tempfile
import shutil
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.user_profile import UserProfile


class TestUserProfile(unittest.TestCase):
    """用户画像系统测试"""
    
    def setUp(self):
        """测试前准备：使用临时目录"""
        self.test_dir = tempfile.mkdtemp()
        # 修改 config 中的路径
        import config
        self.profile_file = os.path.join(self.test_dir, "user_profile.json")
        config.USER_PROFILE_FILE = self.profile_file
        self.profile = UserProfile()
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    # ========== 偏好管理测试 ==========
    
    def test_update_preference_new(self):
        """测试更新新偏好"""
        self.profile.update_preference("genre", "玄幻", weight=0.8)
        
        pref = self.profile.get_preference("genre")
        self.assertEqual(pref, "玄幻")
    
    def test_update_preference_existing(self):
        """测试更新已有偏好"""
        self.profile.update_preference("genre", "玄幻", weight=0.8)
        self.profile.update_preference("genre", "都市", weight=0.9)
        
        pref = self.profile.get_preference("genre")
        self.assertEqual(pref, "都市")
    
    def test_get_preference_default(self):
        """测试获取不存在的偏好返回默认值"""
        pref = self.profile.get_preference("nonexistent", "默认值")
        self.assertEqual(pref, "默认值")
    
    def test_get_all_preferences(self):
        """测试获取所有偏好"""
        self.profile.update_preference("genre", "玄幻")
        self.profile.update_preference("style", "轻松")
        
        prefs = self.profile.get_all_preferences()
        self.assertEqual(len(prefs), 2)
        self.assertEqual(prefs["genre"], "玄幻")
        self.assertEqual(prefs["style"], "轻松")
    
    # ========== 写作习惯测试 ==========
    
    def test_update_habit_new(self):
        """测试更新新习惯"""
        habit_data = {
            "common_words": ["突然", "竟然"],
            "avg_sentence_length": 15
        }
        self.profile.update_habit("vocabulary", habit_data)
        
        habit = self.profile.get_habit("vocabulary")
        self.assertIsNotNone(habit)
        self.assertEqual(habit["common_words"], ["突然", "竟然"])
        self.assertEqual(habit["avg_sentence_length"], 15)
    
    def test_update_habit_existing(self):
        """测试更新已有习惯"""
        self.profile.update_habit("vocabulary", {"words": ["突然"]})
        self.profile.update_habit("vocabulary", {"words": ["突然", "竟然"]})
        
        habit = self.profile.get_habit("vocabulary")
        self.assertEqual(len(habit["words"]), 2)
    
    def test_get_habit_nonexistent(self):
        """测试获取不存在的习惯"""
        habit = self.profile.get_habit("nonexistent")
        self.assertIsNone(habit)
    
    def test_get_all_habits(self):
        """测试获取所有习惯"""
        self.profile.update_habit("vocabulary", {"words": ["突然"]})
        self.profile.update_habit("sentence", {"avg_length": 15})
        
        habits = self.profile.get_all_habits()
        self.assertEqual(len(habits), 2)
        self.assertIn("vocabulary", habits)
        self.assertIn("sentence", habits)
    
    # ========== 修改历史测试 ==========
    
    def test_record_modification(self):
        """测试记录修改"""
        self.profile.record_modification(
            chapter_num=1,
            original="他走进了房间",
            modified="他缓缓地走进了房间",
            reason="增加细节描写",
            context="环境描写"
        )
        
        mods = self.profile.get_modifications()
        self.assertEqual(len(mods), 1)
        self.assertEqual(mods[0]["chapter_num"], 1)
        self.assertEqual(mods[0]["reason"], "增加细节描写")
    
    def test_record_modification_truncation(self):
        """测试修改记录截断"""
        long_text = "a" * 500
        self.profile.record_modification(1, long_text, long_text)
        
        mods = self.profile.get_modifications()
        # 应该被截断到200字符
        self.assertLessEqual(len(mods[0]["original"]), 200)
        self.assertLessEqual(len(mods[0]["modified"]), 200)
    
    def test_record_multiple_modifications(self):
        """测试记录多次修改"""
        for i in range(1, 6):
            self.profile.record_modification(i, f"原文{i}", f"修改{i}")
        
        mods = self.profile.get_modifications()
        self.assertEqual(len(mods), 5)
    
    def test_get_modifications_by_chapter(self):
        """测试按章节获取修改记录"""
        self.profile.record_modification(1, "原文1", "修改1")
        self.profile.record_modification(1, "原文1b", "修改1b")
        self.profile.record_modification(2, "原文2", "修改2")
        
        mods = self.profile.get_modifications(chapter_num=1)
        self.assertEqual(len(mods), 2)
        self.assertTrue(all(m["chapter_num"] == 1 for m in mods))
    
    def test_get_modifications_limit(self):
        """测试修改记录限制"""
        for i in range(1, 20):
            self.profile.record_modification(i, f"原文{i}", f"修改{i}")
        
        mods = self.profile.get_modifications(limit=5)
        self.assertEqual(len(mods), 5)
    
    def test_get_modification_patterns(self):
        """测试获取修改模式"""
        self.profile.record_modification(1, "原文", "修改", reason="增加细节")
        self.profile.record_modification(2, "原文", "修改", reason="增加细节")
        self.profile.record_modification(3, "原文", "修改", reason="修正逻辑")
        
        patterns = self.profile.get_modification_patterns()
        self.assertEqual(patterns["增加细节"], 2)
        self.assertEqual(patterns["修正逻辑"], 1)
    
    # ========== 满意度日志测试 ==========
    
    def test_record_satisfaction(self):
        """测试记录满意度"""
        self.profile.record_satisfaction(
            chapter_num=1,
            satisfaction=0.8,
            feedback="写得不错",
            aspects={"plot": 0.9, "character": 0.7}
        )
        
        stats = self.profile.get_satisfaction_stats()
        self.assertEqual(stats["total_records"], 1)
        self.assertAlmostEqual(stats["avg_satisfaction"], 0.8)
    
    def test_record_multiple_satisfaction(self):
        """测试记录多次满意度"""
        self.profile.record_satisfaction(1, 0.8)
        self.profile.record_satisfaction(2, 0.6)
        self.profile.record_satisfaction(3, 0.9)
        
        stats = self.profile.get_satisfaction_stats()
        self.assertEqual(stats["total_records"], 3)
        self.assertAlmostEqual(stats["avg_satisfaction"], 0.766, places=2)
    
    def test_get_satisfaction_stats_recent(self):
        """测试获取最近满意度统计"""
        for i in range(1, 20):
            self.profile.record_satisfaction(i, 0.5)
        
        # 只统计最近10章
        stats = self.profile.get_satisfaction_stats(recent_n=10)
        self.assertEqual(stats["total_records"], 10)
    
    def test_get_satisfaction_stats_aspects(self):
        """测试满意度各方面统计"""
        self.profile.record_satisfaction(
            1, 0.8,
            aspects={"plot": 0.9, "character": 0.7}
        )
        self.profile.record_satisfaction(
            2, 0.6,
            aspects={"plot": 0.5, "character": 0.8}
        )
        
        stats = self.profile.get_satisfaction_stats()
        self.assertIn("aspect_averages", stats)
        self.assertAlmostEqual(stats["aspect_averages"]["plot"], 0.7)
        self.assertAlmostEqual(stats["aspect_averages"]["character"], 0.75)
    
    def test_get_satisfaction_stats_empty(self):
        """测试空满意度统计"""
        stats = self.profile.get_satisfaction_stats()
        self.assertEqual(stats["total_records"], 0)
        self.assertEqual(stats["avg_satisfaction"], 0)
    
    # ========== 综合查询测试 ==========
    
    def test_get_profile(self):
        """测试获取完整画像"""
        self.profile.update_preference("genre", "玄幻")
        self.profile.update_habit("vocabulary", {"words": ["突然"]})
        self.profile.record_modification(1, "原文", "修改")
        self.profile.record_satisfaction(1, 0.8)
        
        profile = self.profile.get_profile()
        
        self.assertIn("preferences", profile)
        self.assertIn("writing_habits", profile)
        self.assertIn("recent_modifications", profile)
        self.assertIn("satisfaction_stats", profile)
        self.assertIn("modification_patterns", profile)
    
    def test_get_learning_summary(self):
        """测试获取学习摘要"""
        self.profile.update_preference("genre", "玄幻")
        self.profile.update_preference("style", "轻松")
        self.profile.record_modification(1, "原文", "修改", reason="增加细节")
        self.profile.record_satisfaction(1, 0.8)
        
        summary = self.profile.get_learning_summary()
        
        self.assertIn("preferred_genres", summary)
        self.assertIn("preferred_styles", summary)
        self.assertIn("common_modifications", summary)
        self.assertIn("avg_satisfaction", summary)
        self.assertIn("writing_habits", summary)
        
        self.assertEqual(summary["preferred_genres"], ["玄幻"])
        self.assertEqual(summary["preferred_styles"], ["轻松"])
    
    def test_reset(self):
        """测试重置画像"""
        self.profile.update_preference("genre", "玄幻")
        self.profile.record_modification(1, "原文", "修改")
        self.profile.record_satisfaction(1, 0.8)
        
        self.profile.reset()
        
        prefs = self.profile.get_all_preferences()
        self.assertEqual(len(prefs), 0)
        
        mods = self.profile.get_modifications()
        self.assertEqual(len(mods), 0)
        
        stats = self.profile.get_satisfaction_stats()
        self.assertEqual(stats["total_records"], 0)
    
    # ========== 持久化测试 ==========
    
    def test_persistence(self):
        """测试数据持久化"""
        self.profile.update_preference("genre", "玄幻")
        self.profile.update_habit("vocabulary", {"words": ["突然"]})
        self.profile.record_modification(1, "原文", "修改")
        self.profile.record_satisfaction(1, 0.8)
        
        # 创建新实例，应该从文件加载数据
        new_profile = UserProfile()
        
        self.assertEqual(new_profile.get_preference("genre"), "玄幻")
        self.assertIsNotNone(new_profile.get_habit("vocabulary"))
        self.assertEqual(len(new_profile.get_modifications()), 1)
        self.assertEqual(new_profile.get_satisfaction_stats()["total_records"], 1)
    
    def test_persistence_file_creation(self):
        """测试文件创建"""
        self.assertFalse(os.path.exists(self.profile_file))
        
        self.profile.update_preference("genre", "玄幻")
        
        self.assertTrue(os.path.exists(self.profile_file))


if __name__ == '__main__':
    unittest.main()
