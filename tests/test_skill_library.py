"""Skill存储框架单元测试"""
import unittest
import tempfile
import shutil
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.skill_library import SkillLibrary


class TestSkillLibrary(unittest.TestCase):
    """Skill库测试"""
    
    def setUp(self):
        """测试前准备：使用临时目录"""
        self.test_dir = tempfile.mkdtemp()
        # 修改 config 中的路径
        import config
        config.SKILLS_DIR = self.test_dir
        self.library = SkillLibrary()
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    # ========== 添加Skill测试 ==========
    
    def test_add_skill(self):
        """测试添加新Skill"""
        skill_id = self.library.add_skill(
            name="大纲生成",
            trigger="生成大纲",
            steps=["确定题材", "设计主线", "规划章节"],
            description="生成小说大纲",
            category="outline"
        )
        
        self.assertIsNotNone(skill_id)
        self.assertTrue(skill_id.startswith("skill_"))
    
    def test_add_skill_minimal(self):
        """测试添加最小化Skill"""
        skill_id = self.library.add_skill(
            name="简单技能",
            trigger="触发",
            steps=["步骤1"]
        )
        
        skill = self.library.get_skill(skill_id)
        self.assertIsNotNone(skill)
        self.assertEqual(skill["name"], "简单技能")
        self.assertEqual(skill["version"], 1)
        self.assertEqual(skill["usage_count"], 0)
    
    # ========== 获取Skill测试 ==========
    
    def test_get_skill(self):
        """测试获取Skill详情"""
        skill_id = self.library.add_skill(
            name="角色设计",
            trigger="设计角色",
            steps=["确定性格", "设计背景"]
        )
        
        skill = self.library.get_skill(skill_id)
        
        self.assertIsNotNone(skill)
        self.assertEqual(skill["name"], "角色设计")
        self.assertEqual(skill["trigger"], "设计角色")
        self.assertEqual(skill["steps"], ["确定性格", "设计背景"])
    
    def test_get_skill_nonexistent(self):
        """测试获取不存在的Skill"""
        skill = self.library.get_skill("nonexistent_skill_id")
        self.assertIsNone(skill)
    
    # ========== 更新Skill测试 ==========
    
    def test_update_skill(self):
        """测试更新Skill"""
        skill_id = self.library.add_skill(
            name="旧名称",
            trigger="旧触发",
            steps=["旧步骤"]
        )
        
        success = self.library.update_skill(
            skill_id,
            name="新名称",
            trigger="新触发",
            steps=["新步骤1", "新步骤2"]
        )
        
        self.assertTrue(success)
        
        skill = self.library.get_skill(skill_id)
        self.assertEqual(skill["name"], "新名称")
        self.assertEqual(skill["trigger"], "新触发")
        self.assertEqual(skill["steps"], ["新步骤1", "新步骤2"])
        self.assertEqual(skill["version"], 2)
    
    def test_update_skill_nonexistent(self):
        """测试更新不存在的Skill"""
        success = self.library.update_skill("nonexistent", name="新名称")
        self.assertFalse(success)
    
    def test_update_skill_partial(self):
        """测试部分更新Skill"""
        skill_id = self.library.add_skill(
            name="原名",
            trigger="触发",
            steps=["步骤"]
        )
        
        # 只更新名称
        self.library.update_skill(skill_id, name="新名")
        
        skill = self.library.get_skill(skill_id)
        self.assertEqual(skill["name"], "新名")
        self.assertEqual(skill["trigger"], "触发")  # 未变
    
    # ========== 删除Skill测试 ==========
    
    def test_delete_skill(self):
        """测试删除Skill"""
        skill_id = self.library.add_skill(
            name="待删除",
            trigger="触发",
            steps=["步骤"]
        )
        
        success = self.library.delete_skill(skill_id)
        self.assertTrue(success)
        
        skill = self.library.get_skill(skill_id)
        self.assertIsNone(skill)
    
    def test_delete_skill_nonexistent(self):
        """测试删除不存在的Skill"""
        success = self.library.delete_skill("nonexistent")
        self.assertFalse(success)
    
    # ========== 搜索Skill测试 ==========
    
    def test_search_skills_by_trigger(self):
        """测试按触发条件搜索"""
        self.library.add_skill("大纲生成", "生成大纲", ["步骤1"])
        self.library.add_skill("角色设计", "设计角色", ["步骤2"])
        self.library.add_skill("情节规划", "生成情节", ["步骤3"])
        
        results = self.library.search_skills("生成")
        
        self.assertEqual(len(results), 2)
        names = [s["name"] for s in results]
        self.assertIn("大纲生成", names)
        self.assertIn("情节规划", names)
    
    def test_search_skills_by_category(self):
        """测试按分类搜索"""
        self.library.add_skill("大纲1", "触发", ["步骤"], category="outline")
        self.library.add_skill("大纲2", "触发", ["步骤"], category="outline")
        self.library.add_skill("角色1", "触发", ["步骤"], category="character")
        
        results = self.library.search_skills("触发", category="outline")
        
        self.assertEqual(len(results), 2)
    
    def test_search_skills_no_match(self):
        """测试搜索无匹配结果"""
        self.library.add_skill("大纲生成", "生成大纲", ["步骤"])
        
        results = self.library.search_skills("不存在的关键词")
        
        self.assertEqual(len(results), 0)
    
    # ========== 列出Skill测试 ==========
    
    def test_list_skills(self):
        """测试列出所有Skill"""
        self.library.add_skill("技能1", "触发1", ["步骤1"])
        self.library.add_skill("技能2", "触发2", ["步骤2"])
        self.library.add_skill("技能3", "触发3", ["步骤3"])
        
        skills = self.library.list_skills()
        
        self.assertEqual(len(skills), 3)
    
    def test_list_skills_by_category(self):
        """测试按分类列出Skill"""
        self.library.add_skill("大纲1", "触发", ["步骤"], category="outline")
        self.library.add_skill("大纲2", "触发", ["步骤"], category="outline")
        self.library.add_skill("角色1", "触发", ["步骤"], category="character")
        
        outline_skills = self.library.list_skills(category="outline")
        
        self.assertEqual(len(outline_skills), 2)
    
    def test_list_skills_empty(self):
        """测试空库列出"""
        skills = self.library.list_skills()
        self.assertEqual(len(skills), 0)
    
    # ========== 使用记录测试 ==========
    
    def test_record_usage_success(self):
        """测试记录成功使用"""
        skill_id = self.library.add_skill("测试技能", "触发", ["步骤"])
        
        success = self.library.record_usage(skill_id, success=True, feedback="很好用")
        
        self.assertTrue(success)
        
        stats = self.library.get_skill_stats(skill_id)
        self.assertEqual(stats["usage_count"], 1)
        self.assertEqual(stats["success_count"], 1)
        self.assertEqual(stats["success_rate"], 1.0)
        self.assertEqual(stats["feedback_count"], 1)
    
    def test_record_usage_failure(self):
        """测试记录失败使用"""
        skill_id = self.library.add_skill("测试技能", "触发", ["步骤"])
        
        self.library.record_usage(skill_id, success=False, feedback="不太好用")
        
        stats = self.library.get_skill_stats(skill_id)
        self.assertEqual(stats["usage_count"], 1)
        self.assertEqual(stats["success_count"], 0)
        self.assertEqual(stats["success_rate"], 0.0)
    
    def test_record_usage_multiple(self):
        """测试多次使用记录"""
        skill_id = self.library.add_skill("测试技能", "触发", ["步骤"])
        
        self.library.record_usage(skill_id, success=True)
        self.library.record_usage(skill_id, success=True)
        self.library.record_usage(skill_id, success=False)
        
        stats = self.library.get_skill_stats(skill_id)
        self.assertEqual(stats["usage_count"], 3)
        self.assertEqual(stats["success_count"], 2)
        self.assertAlmostEqual(stats["success_rate"], 0.667, places=2)
    
    def test_record_usage_feedback_limit(self):
        """测试反馈数量限制"""
        skill_id = self.library.add_skill("测试技能", "触发", ["步骤"])
        
        # 添加30条反馈
        for i in range(30):
            self.library.record_usage(skill_id, success=True, feedback=f"反馈{i}")
        
        skill = self.library.get_skill(skill_id)
        # 应该被限制到20条
        self.assertLessEqual(len(skill["user_feedback"]), 20)
    
    def test_record_usage_nonexistent(self):
        """测试记录不存在Skill的使用"""
        success = self.library.record_usage("nonexistent", success=True)
        self.assertFalse(success)
    
    # ========== 统计信息测试 ==========
    
    def test_get_skill_stats(self):
        """测试获取Skill统计"""
        skill_id = self.library.add_skill("测试技能", "触发", ["步骤"])
        self.library.record_usage(skill_id, success=True)
        self.library.record_usage(skill_id, success=True, feedback="好")
        
        stats = self.library.get_skill_stats(skill_id)
        
        self.assertEqual(stats["skill_id"], skill_id)
        self.assertEqual(stats["name"], "测试技能")
        self.assertEqual(stats["usage_count"], 2)
        self.assertEqual(stats["success_count"], 2)
        self.assertEqual(stats["success_rate"], 1.0)
        self.assertEqual(stats["version"], 1)
        self.assertEqual(stats["feedback_count"], 1)
    
    def test_get_skill_stats_nonexistent(self):
        """测试获取不存在Skill的统计"""
        stats = self.library.get_skill_stats("nonexistent")
        self.assertIsNone(stats)
    
    def test_get_library_stats(self):
        """测试获取Skill库整体统计"""
        self.library.add_skill("技能1", "触发", ["步骤"], category="outline")
        self.library.add_skill("技能2", "触发", ["步骤"], category="outline")
        self.library.add_skill("技能3", "触发", ["步骤"], category="character")
        
        skill_id = self.library.list_skills()[0]["skill_id"]
        self.library.record_usage(skill_id, success=True)
        
        stats = self.library.get_library_stats()
        
        self.assertEqual(stats["total_skills"], 3)
        self.assertEqual(stats["total_usage"], 1)
        self.assertEqual(stats["total_success"], 1)
        self.assertEqual(stats["avg_success_rate"], 1.0)
        self.assertEqual(stats["category_counts"]["outline"], 2)
        self.assertEqual(stats["category_counts"]["character"], 1)
    
    def test_get_library_stats_empty(self):
        """测试空库统计"""
        stats = self.library.get_library_stats()
        
        self.assertEqual(stats["total_skills"], 0)
        self.assertEqual(stats["total_usage"], 0)
        self.assertEqual(stats["total_success"], 0)
        self.assertEqual(stats["avg_success_rate"], 0)
    
    # ========== 持久化测试 ==========
    
    def test_persistence(self):
        """测试数据持久化"""
        skill_id = self.library.add_skill("持久化测试", "触发", ["步骤"])
        self.library.record_usage(skill_id, success=True, feedback="好")
        
        # 创建新实例，应该从文件加载数据
        new_library = SkillLibrary()
        
        skill = new_library.get_skill(skill_id)
        self.assertIsNotNone(skill)
        self.assertEqual(skill["name"], "持久化测试")
        self.assertEqual(skill["usage_count"], 1)
        self.assertEqual(skill["success_count"], 1)


if __name__ == '__main__':
    unittest.main()
