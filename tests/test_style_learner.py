"""StyleLearner 单元测试"""
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
from core.style_learner import StyleLearner, get_style_learner
import config


class TestStyleLearner(unittest.TestCase):
    """StyleLearner 测试类"""
    
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
    
    @patch('core.style_learner.get_llm_client')
    @patch('core.style_learner.get_style_engineer_agent')
    def test_initialization(self, mock_get_style_engineer_agent, mock_get_llm_client):
        """测试初始化"""
        mock_get_llm_client.return_value = MockLLMClient()
        mock_get_style_engineer_agent.return_value = MockLLMClient()
        learner = StyleLearner()
        self.assertIsNotNone(learner)
        self.assertIsNotNone(learner.llm_client)
        # 实际是learning_data字典，不是learning_samples列表
        self.assertIsInstance(learner.learning_data, dict)
    
    @patch('core.style_learner.get_llm_client')
    def test_get_style_learner_singleton(self, mock_get_client):
        """测试单例模式"""
        mock_get_client.return_value = MockLLMClient()
        l1 = get_style_learner()
        l2 = get_style_learner()
        self.assertIs(l1, l2)
    
    @patch('core.style_learner.get_llm_client')
    @patch('core.style_learner.get_style_engineer_agent')
    def test_learn_from_reference(self, mock_get_style_engineer_agent, mock_get_llm_client):
        """测试从参考文本学习（替代不存在的add_learning_sample方法）"""
        mock_get_llm_client.return_value = MockLLMClient()
        # style_engineer 需要有 analyze_writing_style 方法，不能用 MockLLMClient
        mock_engineer = MagicMock()
        mock_engineer.analyze_writing_style.return_value = {
            "fingerprint": {
                "top_words": [{"word": "轻松", "count": 5}, {"word": "幽默", "count": 3}],
                "sentence_length": {"average": 18},
                "dialogue_ratio": 0.2
            },
            "style_guide": {
                "must_do": ["保持幽默"],
                "forbidden_patterns": ["避免冗长"]
            }
        }
        mock_get_style_engineer_agent.return_value = mock_engineer
        learner = StyleLearner()
        
        reference_text = "这是一个轻松幽默的参考文本，充满了俏皮话。"
        
        result = learner.learn_from_reference(reference_text)
        
        self.assertIsInstance(result, dict)
        self.assertIn("learned", result)
        self.assertTrue(result["learned"])
    
    @patch('core.style_learner.get_llm_client')
    @patch('core.style_learner.get_style_engineer_agent')
    def test_learn_from_modification(self, mock_get_style_engineer_agent, mock_get_llm_client):
        """测试从修改中学习（替代不存在的learn_style方法）"""
        mock_get_llm_client.return_value = MockLLMClient()
        mock_get_style_engineer_agent.return_value = MockLLMClient()
        learner = StyleLearner()
        
        old_content = "这是一个正式的文本。"
        new_content = "这是一个轻松幽默的文本，充满了俏皮话。"
        
        result = learner.learn_from_modification(old_content, new_content)
        
        self.assertIsInstance(result, dict)
        self.assertIn("learned", result)
    
    @patch('core.style_learner.get_llm_client')
    @patch('core.style_learner.get_style_engineer_agent')
    def test_get_style_guide(self, mock_get_style_engineer_agent, mock_get_llm_client):
        """测试获取风格指南（替代不存在的adapt_style_guide方法）"""
        mock_get_llm_client.return_value = MockLLMClient()
        mock_get_style_engineer_agent.return_value = MockLLMClient()
        learner = StyleLearner()
        
        style_guide = learner.get_style_guide()
        
        self.assertIsInstance(style_guide, dict)
        # 检查基本结构存在
        self.assertIn("tone", style_guide)
        self.assertIn("pov", style_guide)
        self.assertIn("must_do", style_guide)
    
    @patch('core.style_learner.get_llm_client')
    @patch('core.style_learner.get_style_engineer_agent')
    def test_get_learning_report(self, mock_get_style_engineer_agent, mock_get_llm_client):
        """测试获取学习报告"""
        mock_get_llm_client.return_value = MockLLMClient()
        mock_get_style_engineer_agent.return_value = MockLLMClient()
        learner = StyleLearner()
        
        # 实际返回的是字符串（Markdown格式），不是字典
        report = learner.get_learning_report()
        
        self.assertIsInstance(report, str)
        self.assertIn("风格学习报告", report)


if __name__ == '__main__':
    unittest.main()
