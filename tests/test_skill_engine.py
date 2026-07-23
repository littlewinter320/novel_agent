"""
SkillEngine 单元测试

测试Skill引擎的核心功能:
- 自动创建Skill
- 检索匹配Skill
- 应用Skill
- 改进Skill
"""
import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# 添加项目路径
test_dir = os.path.dirname(os.path.abspath(__file__))
novel_agent_dir = os.path.dirname(test_dir)
sys.path.insert(0, novel_agent_dir)

from tests.test_utils import MockLLMClient
from core.skill_engine import SkillEngine, get_skill_engine
import config


class TestSkillEngine(unittest.TestCase):
    """SkillEngine 测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.original_data_dir = config.DATA_DIR
        config.DATA_DIR = self.test_dir
        
    def tearDown(self):
        """测试后清理"""
        config.DATA_DIR = self.original_data_dir
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    @patch('core.skill_engine.get_skill_library')
    def test_initialization(self, mock_get_skill_library):
        """测试初始化"""
        mock_skill_library = MagicMock()
        mock_get_skill_library.return_value = mock_skill_library
        
        engine = SkillEngine()
        self.assertIsNotNone(engine.skill_library)
    
    @patch('core.skill_engine.get_skill_library')
    def test_auto_create_skill(self, mock_get_skill_library):
        """测试自动创建Skill"""
        mock_skill_library = MagicMock()
        mock_skill_library.list_skills.return_value = []
        mock_skill_library.add_skill.return_value = True
        mock_get_skill_library.return_value = mock_skill_library
        
        engine = SkillEngine()
        
        task_result = {
            "task_description": "生成玄幻小说第一章",
            "steps": ["分析题材", "设计大纲", "生成内容"],
            "success": True
        }
        
        result = engine.auto_create_skill(task_result)
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result["created"])
        self.assertIn("skill_id", result)
        self.assertIn("skill_name", result)
    
    @patch('core.skill_engine.get_skill_library')
    def test_auto_create_skill_missing_fields(self, mock_get_skill_library):
        """测试自动创建Skill缺少必要字段"""
        mock_skill_library = MagicMock()
        mock_get_skill_library.return_value = mock_skill_library
        
        engine = SkillEngine()
        
        task_result = {
            "task_description": "生成玄幻小说第一章"
            # 缺少 steps
        }
        
        result = engine.auto_create_skill(task_result)
        
        self.assertFalse(result["created"])
        self.assertIn("error", result)
    
    @patch('core.skill_engine.get_skill_library')
    def test_search_matching_skill(self, mock_get_skill_library):
        """测试检索匹配Skill"""
        mock_skill_library = MagicMock()
        mock_skill_library.search_skills.return_value = [
            {
                "skill_id": "skill_1",
                "name": "玄幻生成",
                "success_rate": 0.9
            },
            {
                "skill_id": "skill_2",
                "name": "都市生成",
                "success_rate": 0.8
            }
        ]
        mock_get_skill_library.return_value = mock_skill_library
        
        engine = SkillEngine()
        
        result = engine.search_matching_skill("生成玄幻小说")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["skill_id"], "skill_1")
    
    @patch('core.skill_engine.get_skill_library')
    def test_apply_skill(self, mock_get_skill_library):
        """测试应用Skill"""
        mock_skill_library = MagicMock()
        mock_skill_library.get_skill.return_value = {
            "skill_id": "skill_1",
            "name": "玄幻生成",
            "steps": ["分析题材", "设计大纲", "生成内容"]
        }
        mock_skill_library.update_skill.return_value = True
        mock_get_skill_library.return_value = mock_skill_library
        
        engine = SkillEngine()
        
        result = engine.apply_skill("skill_1")
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result["applied"])
        self.assertIn("skill_id", result)
        self.assertIn("steps", result)
    
    @patch('core.skill_engine.get_skill_library')
    def test_improve_skill(self, mock_get_skill_library):
        """测试改进Skill"""
        mock_skill_library = MagicMock()
        mock_skill_library.get_skill.return_value = {
            "skill_id": "skill_1",
            "name": "玄幻生成",
            "user_feedback": [],
            "success_rate": 0.8,
            "version": 1
        }
        mock_skill_library.update_skill.return_value = True
        mock_get_skill_library.return_value = mock_skill_library
        
        engine = SkillEngine()
        
        feedback = {
            "satisfaction": 0.9,
            "comments": "效果很好"
        }
        
        result = engine.improve_skill("skill_1", feedback)
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result["improved"])
        self.assertIn("new_success_rate", result)
        self.assertIn("version", result)


if __name__ == '__main__':
    unittest.main()
