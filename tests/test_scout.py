"""
ScoutAgent 单元测试

测试扫榜分析师的核心功能:
- 题材分析（analyze_genre）
- 热门作品搜索
- 写作建议生成
- 缓存功能
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
from agents.scout import ScoutAgent, get_scout_agent
import config


class TestScoutAgent(unittest.TestCase):
    """ScoutAgent 测试类"""
    
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
    
    @patch('agents.scout.get_llm_client')
    def test_initialization(self, mock_get_client):
        """测试初始化"""
        mock_get_client.return_value = MockLLMClient()
        scout = ScoutAgent()
        self.assertIsNotNone(scout.llm_client)
        self.assertIsNotNone(scout.genre_knowledge_base)
        self.assertEqual(scout._analysis_cache, {})
    
    @patch('agents.scout.get_llm_client')
    def test_get_scout_agent_singleton(self, mock_get_client):
        """测试单例模式"""
        import agents.scout as scout_module
        scout_module._scout_agent = None
        
        mock_get_client.return_value = MockLLMClient()
        scout1 = get_scout_agent()
        scout2 = get_scout_agent()
        self.assertIs(scout1, scout2)
        
        # 清理
        scout_module._scout_agent = None
    
    @patch('agents.scout.get_llm_client')
    def test_analyze_genre(self, mock_get_client):
        """测试分析题材（核心方法）"""
        mock_get_client.return_value = MockLLMClient()
        scout = ScoutAgent()
        
        # 分析玄幻题材
        result = scout.analyze_genre("玄幻")
        
        self.assertIsInstance(result, dict)
        self.assertIn("genre", result)
        self.assertEqual(result["genre"], "玄幻")
        self.assertIn("hot_novels", result)
        self.assertIn("suggestions", result)
        self.assertIn("recommended_outline", result)
    
    @patch('agents.scout.get_llm_client')
    def test_analyze_genre_with_constraints(self, mock_get_client):
        """测试带约束条件的题材分析"""
        mock_get_client.return_value = MockLLMClient()
        scout = ScoutAgent()
        
        constraints = {"target_audience": "男频", "tone": "热血"}
        result = scout.analyze_genre("玄幻", constraints)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result["genre"], "玄幻")
    
    @patch('agents.scout.get_llm_client')
    def test_generate_suggestions(self, mock_get_client):
        """测试生成写作建议"""
        mock_get_client.return_value = MockLLMClient()
        scout = ScoutAgent()
        
        common_features = {
            "success_factors": ["快节奏", "爽点密集"],
            "common_opening_hooks": ["悬念开篇"],
            "reader_preferences": {"likes": ["节奏快"]}
        }
        
        suggestions = scout.generate_suggestions(common_features, "玄幻")
        
        self.assertIsInstance(suggestions, list)
        self.assertTrue(len(suggestions) > 0)
    
    @patch('agents.scout.get_llm_client')
    def test_cache_functionality(self, mock_get_client):
        """测试缓存功能"""
        mock_get_client.return_value = MockLLMClient()
        scout = ScoutAgent()
        
        # 第一次分析（会调用LLM）
        result1 = scout.analyze_genre("玄幻")
        call_count_1 = scout.llm_client.call_count
        
        # 第二次分析相同题材（应该使用缓存）
        result2 = scout.analyze_genre("玄幻")
        call_count_2 = scout.llm_client.call_count
        
        # 缓存命中，LLM调用次数不应增加
        self.assertEqual(call_count_1, call_count_2)
        self.assertEqual(result1["genre"], result2["genre"])
    
    def test_cache_manual(self):
        """测试手动缓存操作"""
        scout = ScoutAgent.__new__(ScoutAgent)
        scout._analysis_cache = {}
        
        # 模拟缓存数据
        cache_key = "test_cache_key"
        cache_data = {"test": "data"}
        
        scout._analysis_cache[cache_key] = cache_data
        
        # 验证缓存存在
        self.assertEqual(scout._analysis_cache[cache_key], cache_data)
        
        # 清除缓存
        scout._analysis_cache.clear()
        self.assertEqual(len(scout._analysis_cache), 0)


if __name__ == '__main__':
    unittest.main()
