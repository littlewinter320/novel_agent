"""StyleEngineerAgent 单元测试"""
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
from agents.style_engineer import StyleEngineerAgent, get_style_engineer_agent
import config


class TestStyleEngineerAgent(unittest.TestCase):
    """StyleEngineerAgent 测试类"""
    
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
    
    @patch('agents.style_engineer.get_llm_client')
    def test_initialization(self, mock_get_client):
        """测试初始化"""
        mock_get_client.return_value = MockLLMClient()
        style_engineer = StyleEngineerAgent()
        self.assertIsNotNone(style_engineer)
        self.assertIsNotNone(style_engineer.llm_client)
    
    @patch('agents.style_engineer.get_llm_client')
    def test_get_style_engineer_agent_singleton(self, mock_get_client):
        """测试单例模式"""
        mock_get_client.return_value = MockLLMClient()
        engineer1 = get_style_engineer_agent()
        engineer2 = get_style_engineer_agent()
        self.assertIs(engineer1, engineer2)
    
    @patch('agents.style_engineer.get_llm_client')
    def test_analyze_writing_style(self, mock_get_client):
        """测试分析写作风格"""
        mock_get_client.return_value = MockLLMClient()
        style_engineer = StyleEngineerAgent()
        
        sample_text = """
        这是一个测试文本。主角走进了房间，看到了桌上的信件。
        他拿起信件，仔细阅读。信中写着一个秘密，让他震惊不已。
        """
        
        style_analysis = style_engineer.analyze_writing_style(sample_text)
        
        self.assertIsInstance(style_analysis, dict)
        # 实际返回结构包含fingerprint和style_guide
        self.assertIn("fingerprint", style_analysis)
        self.assertIn("style_guide", style_analysis)
    
    @patch('agents.style_engineer.get_llm_client')
    def test_generate_style_guide(self, mock_get_client):
        """测试生成风格指南"""
        mock_get_client.return_value = MockLLMClient()
        style_engineer = StyleEngineerAgent()
        
        # 实际方法签名需要fingerprint和style_analysis两个参数
        fingerprint = {
            "sentence_length": {"average": 20},
            "dialogue_ratio": 0.2,
            "top_words": [{"word": "测试", "count": 5}]
        }
        
        style_analysis = {
            "narrative_pov": "第三人称",
            "language_style": "简洁",
            "other_features": ["幽默元素"]
        }
        
        style_guide = style_engineer.generate_style_guide(fingerprint, style_analysis)
        
        self.assertIsInstance(style_guide, dict)
        # 检查基本结构存在
        self.assertIn("tone", style_guide)
        self.assertIn("pov", style_guide)
        self.assertIn("must_do", style_guide)
        self.assertIn("forbidden_patterns", style_guide)
    
    @patch('agents.style_engineer.get_llm_client')
    def test_extract_fingerprint(self, mock_get_client):
        """测试提取文笔指纹（替代不存在的check_style_consistency方法）"""
        mock_get_client.return_value = MockLLMClient()
        style_engineer = StyleEngineerAgent()
        
        text = "这是一个测试文本。主角走进了房间，看到了桌上的信件。他拿起信件，仔细阅读。"
        
        fingerprint = style_engineer.extract_fingerprint(text)
        
        self.assertIsInstance(fingerprint, dict)
        # 检查基本结构存在
        self.assertIn("sentence_length", fingerprint)
        self.assertIn("dialogue_ratio", fingerprint)
        self.assertIn("top_words", fingerprint)


if __name__ == '__main__':
    unittest.main()
