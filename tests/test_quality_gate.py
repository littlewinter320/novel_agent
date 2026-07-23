"""
QualityGate 单元测试

测试质量门禁的核心功能:
- 6大维度检查
- PASS/FAIL判定
- 报告生成
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
from core.quality_gate import QualityGate, get_quality_gate
import config


class TestQualityGate(unittest.TestCase):
    """QualityGate 测试类"""
    
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
    
    @patch('core.quality_gate.get_llm_client')
    def test_initialization(self, mock_get_client):
        """测试初始化"""
        mock_get_client.return_value = MockLLMClient()
        qg = QualityGate()
        self.assertIsNotNone(qg.llm_client)
        self.assertEqual(qg.check_results, [])
    
    @patch('core.quality_gate.get_llm_client')
    def test_check_basic(self, mock_get_client):
        """测试基础检查功能"""
        mock_get_client.return_value = MockLLMClient()
        qg = QualityGate()
        
        # 准备测试数据
        output = {
            "content": "测试内容",
            "summary": "测试摘要",
            "details": "测试详情"
        }
        
        result = qg.check(output)
        
        self.assertIsInstance(result, dict)
        self.assertIn("pass", result)
        self.assertIn("dimensions", result)
        self.assertIn("issues", result)
        self.assertIn("suggestions", result)
        self.assertEqual(len(result["dimensions"]), 6)  # 6大维度
    
    @patch('core.quality_gate.get_llm_client')
    def test_check_with_context(self, mock_get_client):
        """测试带上下文的检查"""
        mock_get_client.return_value = MockLLMClient()
        qg = QualityGate()
        
        output = {
            "content": "测试内容",
            "summary": "测试摘要",
            "details": "测试详情"
        }
        context = {
            "user_modifications": ["修改1", "修改2"]
        }
        
        result = qg.check(output, context)
        
        self.assertIsInstance(result, dict)
        self.assertIn("dimensions", result)
    
    @patch('core.quality_gate.get_llm_client')
    def test_generate_report(self, mock_get_client):
        """测试生成报告"""
        mock_get_client.return_value = MockLLMClient()
        qg = QualityGate()
        
        # 先执行检查
        output = {
            "content": "测试内容",
            "summary": "测试摘要",
            "details": "测试详情"
        }
        check_result = qg.check(output)
        
        # 生成报告
        report = qg.generate_report(check_result)
        
        self.assertIsInstance(report, str)
        self.assertIn("质量检查报告", report)
        self.assertIn("总体结果", report)
    
    @patch('core.quality_gate.get_llm_client')
    def test_get_quality_gate_singleton(self, mock_get_client):
        """测试单例模式"""
        import core.quality_gate as qg_module
        qg_module._quality_gate = None
        
        mock_get_client.return_value = MockLLMClient()
        qg1 = get_quality_gate()
        qg2 = get_quality_gate()
        self.assertIs(qg1, qg2)
        
        # 清理
        qg_module._quality_gate = None


if __name__ == '__main__':
    unittest.main()
