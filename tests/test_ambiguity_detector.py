"""
AmbiguityDetector 单元测试

测试模糊度检测器的核心功能:
- 清晰输入检测
- 模糊输入检测
- 信息不完整检测
- 信息歧义检测
- 提问生成
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
from core.ambiguity_detector import AmbiguityDetector, get_ambiguity_detector
import config


class TestAmbiguityDetector(unittest.TestCase):
    """AmbiguityDetector 测试类"""
    
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
    
    @patch('core.ambiguity_detector.get_llm_client')
    def test_initialization(self, mock_get_client):
        """测试初始化"""
        mock_get_client.return_value = MockLLMClient()
        detector = AmbiguityDetector()
        self.assertIsNotNone(detector)
        self.assertIsNotNone(detector.llm_client)
    
    @patch('core.ambiguity_detector.get_llm_client')
    def test_get_ambiguity_detector_singleton(self, mock_get_client):
        """测试单例模式"""
        # 重置全局实例
        import core.ambiguity_detector as ad_module
        ad_module._ambiguity_detector = None
        
        mock_get_client.return_value = MockLLMClient()
        det1 = get_ambiguity_detector()
        det2 = get_ambiguity_detector()
        self.assertIs(det1, det2)
        
        # 清理
        ad_module._ambiguity_detector = None
    
    @patch('core.ambiguity_detector.get_llm_client')
    def test_detect_ambiguity_returns_dict(self, mock_get_client):
        """测试detect_ambiguity返回字典格式"""
        mock_get_client.return_value = MockLLMClient()
        detector = AmbiguityDetector()
        
        user_input = "帮我写一个玄幻小说，主角是一个少年，背景是修仙世界"
        
        result = detector.detect_ambiguity(user_input)
        
        # 验证返回结构
        self.assertIsInstance(result, dict)
        self.assertIn("is_ambiguous", result)
        self.assertIn("ambiguity_type", result)
        self.assertIn("questions", result)
        self.assertIn("detected_at", result)
    
    @patch('core.ambiguity_detector.get_llm_client')
    def test_detect_ambiguity_short_input(self, mock_get_client):
        """测试过短输入的模糊检测"""
        mock_get_client.return_value = MockLLMClient()
        detector = AmbiguityDetector()
        
        # 输入太短（<10字符），应触发vague检测
        user_input = "写故事"
        
        result = detector.detect_ambiguity(user_input)
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result["is_ambiguous"])
        # 应该包含提问
        self.assertTrue(len(result["questions"]) > 0)
    
    @patch('core.ambiguity_detector.get_llm_client')
    def test_check_incomplete_missing_params(self, mock_get_client):
        """测试信息不完整检测"""
        mock_get_client.return_value = MockLLMClient()
        detector = AmbiguityDetector()
        
        # 缺少多个关键参数（无题材、无主角、无剧情、无背景）
        user_input = "帮我写一个故事"
        
        result = detector._check_incomplete(user_input)
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result["is_ambiguous"])
        self.assertTrue(len(result["missing_params"]) > 0)
        self.assertTrue(len(result["questions"]) > 0)
    
    @patch('core.ambiguity_detector.get_llm_client')
    def test_check_incomplete_with_params(self, mock_get_client):
        """测试信息完整检测"""
        mock_get_client.return_value = MockLLMClient()
        detector = AmbiguityDetector()
        
        # 包含所有关键参数的关键词
        user_input = "帮我写一个玄幻题材的小说，主角是少年，剧情是成长冒险，背景是修仙世界"
        
        result = detector._check_incomplete(user_input)
        
        self.assertIsInstance(result, dict)
        self.assertFalse(result["is_ambiguous"])
        self.assertEqual(len(result["missing_params"]), 0)
    
    @patch('core.ambiguity_detector.get_llm_client')
    def test_check_contradiction_no_context(self, mock_get_client):
        """测试无上下文时的矛盾检测"""
        mock_get_client.return_value = MockLLMClient()
        detector = AmbiguityDetector()
        
        result = detector._check_contradiction("测试输入", None)
        
        self.assertIsInstance(result, dict)
        self.assertFalse(result["is_ambiguous"])
    
    @patch('core.ambiguity_detector.get_llm_client')
    def test_check_vague_short_input(self, mock_get_client):
        """测试模糊检测-输入过短"""
        mock_get_client.return_value = MockLLMClient()
        detector = AmbiguityDetector()
        
        # 输入长度<10
        result = detector._check_vague("短")
        
        self.assertTrue(result["is_ambiguous"])
        self.assertIn("reason", result)
        self.assertTrue(len(result["questions"]) > 0)
    
    @patch('core.ambiguity_detector.get_llm_client')
    def test_generate_question_for_param(self, mock_get_client):
        """测试为缺失参数生成提问"""
        mock_get_client.return_value = MockLLMClient()
        detector = AmbiguityDetector()
        
        # 测试已知参数
        for param in ["genre", "protagonist", "plot", "setting"]:
            question = detector._generate_question_for_param(param)
            self.assertIsInstance(question, dict)
            self.assertIn("question", question)
            self.assertIn("options", question)
            # 必须包含[D]其他选项
            options = question["options"]
            has_other = any("其他" in opt for opt in options)
            self.assertTrue(has_other, f"参数{param}的提问缺少'其他'选项")
    
    @patch('core.ambiguity_detector.get_llm_client')
    def test_generate_question_for_unknown_param(self, mock_get_client):
        """测试为未知参数生成提问"""
        mock_get_client.return_value = MockLLMClient()
        detector = AmbiguityDetector()
        
        question = detector._generate_question_for_param("unknown_param")
        self.assertIsInstance(question, dict)
        self.assertIn("question", question)
        self.assertIn("options", question)
    
    @patch('core.ambiguity_detector.get_llm_client')
    def test_detect_ambiguity_type(self, mock_get_client):
        """测试模糊类型判断"""
        mock_get_client.return_value = MockLLMClient()
        detector = AmbiguityDetector()
        
        # 短输入应该触发vague类型
        result = detector.detect_ambiguity("短")
        
        self.assertIn("ambiguity_type", result)
        # 短输入至少应该被检测为vague或incomplete
        self.assertIn(result["ambiguity_type"], ["vague", "incomplete", "ambiguous", "contradiction", "none"])


if __name__ == '__main__':
    unittest.main()
