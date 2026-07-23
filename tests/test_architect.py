"""
ArchitectAgent 单元测试

测试架构师的核心功能:
- 需求澄清
- 分层大纲生成
- Compass滚动规划
- 伏笔规划
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
from agents.architect import ArchitectAgent, get_architect_agent
import config


class TestArchitectAgent(unittest.TestCase):
    """ArchitectAgent 测试类"""
    
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
    
    @patch('agents.architect.get_llm_client')
    def test_initialization(self, mock_get_client):
        """测试初始化"""
        mock_get_client.return_value = MockLLMClient()
        architect = ArchitectAgent()
        self.assertIsNotNone(architect.llm_client)
        self.assertIsNotNone(architect.genre_knowledge_base)
        # 验证规划状态初始化
        self.assertIsNotNone(architect._planning_state)
        self.assertIn("current_level", architect._planning_state)
    
    @patch('agents.architect.get_llm_client')
    def test_get_architect_agent_singleton(self, mock_get_client):
        """测试单例模式"""
        # 重置全局实例
        import agents.architect as arch_module
        arch_module._architect_agent = None
        
        mock_get_client.return_value = MockLLMClient()
        architect1 = get_architect_agent()
        architect2 = get_architect_agent()
        self.assertIs(architect1, architect2)
        
        # 清理
        arch_module._architect_agent = None
    
    @patch('agents.architect.get_llm_client')
    def test_clarify_requirements_complete(self, mock_get_client):
        """测试需求澄清-参数完整"""
        mock_get_client.return_value = MockLLMClient()
        architect = ArchitectAgent()
        
        user_input = "帮我写一个玄幻小说，主角是废柴逆袭，核心冲突是复仇，目标读者男频，基调热血，预计100章"
        genre = "玄幻"
        
        result = architect.clarify_requirements(user_input, genre)
        
        self.assertIsInstance(result, dict)
        self.assertIn("complete", result)
        self.assertIn("extracted_params", result)
        self.assertIn("missing_params", result)
        self.assertIn("questions", result)
    
    @patch('agents.architect.get_llm_client')
    def test_clarify_requirements_incomplete(self, mock_get_client):
        """测试需求澄清-参数不完整"""
        mock_get_client.return_value = MockLLMClient()
        architect = ArchitectAgent()
        
        user_input = "帮我写一个故事"
        genre = "玄幻"
        
        result = architect.clarify_requirements(user_input, genre)
        
        self.assertIsInstance(result, dict)
        self.assertFalse(result["complete"])
        self.assertTrue(len(result["missing_params"]) > 0)
        self.assertTrue(len(result["questions"]) > 0)
    
    @patch('agents.architect.get_llm_client')
    def test_generate_master_outline(self, mock_get_client):
        """测试生成总纲"""
        mock_get_client.return_value = MockLLMClient()
        architect = ArchitectAgent()
        
        requirements = {
            "genre": "玄幻",
            "protagonist_type": "废柴逆袭",
            "core_conflict": "复仇",
            "target_audience": "男频",
            "tone": "热血",
            "estimated_chapters": 100
        }
        
        outline = architect.generate_master_outline(requirements)
        
        self.assertIsInstance(outline, dict)
        # 验证规划状态更新
        self.assertEqual(architect._planning_state["current_level"], "master")
    
    @patch('agents.architect.get_llm_client')
    def test_generate_volume_outlines(self, mock_get_client):
        """测试生成卷纲"""
        mock_get_client.return_value = MockLLMClient()
        architect = ArchitectAgent()
        
        master_outline = {
            "core_setting": "修仙世界",
            "main_plot": {
                "act_1_start": "主角入门",
                "act_2_develop": "逐步成长",
                "act_3_turn": "重大危机",
                "act_4_end": "最终决战"
            }
        }
        
        volume_outlines = architect.generate_volume_outlines(master_outline, total_volumes=3)
        
        self.assertIsInstance(volume_outlines, list)
        # 验证规划状态更新
        self.assertEqual(architect._planning_state["current_level"], "volume")
    
    @patch('agents.architect.get_llm_client')
    def test_generate_chapter_plans(self, mock_get_client):
        """测试生成章节规划"""
        mock_get_client.return_value = MockLLMClient()
        architect = ArchitectAgent()
        
        arc_outline = {
            "arc_name": "初入江湖",
            "core_events": ["入门测试", "首次任务"],
            "estimated_chapters": 10
        }
        
        chapter_plans = architect.generate_chapter_plans(arc_outline)
        
        self.assertIsInstance(chapter_plans, list)
        # 验证规划状态更新
        self.assertEqual(architect._planning_state["current_level"], "chapter")
    
    @patch('agents.architect.get_llm_client')
    def test_get_planning_state(self, mock_get_client):
        """测试获取规划状态"""
        mock_get_client.return_value = MockLLMClient()
        architect = ArchitectAgent()
        
        state = architect.get_planning_state()
        
        self.assertIsInstance(state, dict)
        self.assertIn("current_level", state)
        self.assertIn("requirements", state)
    
    @patch('agents.architect.get_llm_client')
    def test_generate_planning_report(self, mock_get_client):
        """测试生成规划报告"""
        mock_get_client.return_value = MockLLMClient()
        architect = ArchitectAgent()
        
        report = architect.generate_planning_report()
        
        self.assertIsInstance(report, str)
        self.assertTrue(len(report) > 0)


if __name__ == '__main__':
    unittest.main()
