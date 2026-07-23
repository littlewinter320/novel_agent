"""
RevisorAgent 单元测试

测试修订员的核心功能:
- 定点修复
- 循环审计
- 修订报告生成
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
from agents.revisor import RevisorAgent, get_revisor_agent
import config


class TestRevisorAgent(unittest.TestCase):
    """RevisorAgent 测试类"""
    
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
    
    @patch('agents.revisor.get_llm_client')
    @patch('agents.revisor.get_auditor_agent')
    def test_initialization(self, mock_get_auditor, mock_get_client):
        """测试初始化"""
        mock_get_client.return_value = MockLLMClient()
        mock_get_auditor.return_value = MagicMock()
        
        revisor = RevisorAgent()
        self.assertIsNotNone(revisor.llm_client)
        self.assertIsNotNone(revisor.auditor)
    
    @patch('agents.revisor.get_llm_client')
    @patch('agents.revisor.get_auditor_agent')
    def test_get_revisor_agent_singleton(self, mock_get_auditor, mock_get_client):
        """测试单例模式"""
        # 重置全局实例
        import agents.revisor as rev_module
        rev_module._revisor_agent = None
        
        mock_get_client.return_value = MockLLMClient()
        mock_get_auditor.return_value = MagicMock()
        
        revisor1 = get_revisor_agent()
        revisor2 = get_revisor_agent()
        self.assertIs(revisor1, revisor2)
        
        # 清理
        rev_module._revisor_agent = None
    
    @patch('agents.revisor.get_llm_client')
    @patch('agents.revisor.get_auditor_agent')
    def test_revise_chapter(self, mock_get_auditor, mock_get_client):
        """测试修订章节"""
        mock_get_client.return_value = MockLLMClient()
        mock_auditor = MagicMock()
        mock_get_auditor.return_value = mock_auditor
        
        revisor = RevisorAgent()
        
        chapter_content = "原始章节内容"
        chapter_num = 1
        genre = "玄幻"
        audit_report = {
            "issues": ["角色性格不一致"],
            "suggestions": ["修改角色对话"]
        }
        
        result = revisor.revise_chapter(
            chapter_content, 
            chapter_num, 
            genre, 
            audit_report
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn("chapter_num", result)
        self.assertIn("revised_content", result)
        self.assertIn("fixes_applied", result)
        self.assertIn("audit_rounds", result)
        self.assertIn("final_pass", result)
    
    @patch('agents.revisor.get_llm_client')
    @patch('agents.revisor.get_auditor_agent')
    def test_generate_revision_report(self, mock_get_auditor, mock_get_client):
        """测试生成修订报告"""
        mock_get_client.return_value = MockLLMClient()
        mock_get_auditor.return_value = MagicMock()
        
        revisor = RevisorAgent()
        
        revision_result = {
            "chapter_num": 1,
            "revised_content": "修订后内容",
            "fixes_applied": ["修复1", "修复2"],
            "audit_rounds": 2,
            "final_pass": True,
            "final_audit_report": {"issues": []}
        }
        
        report = revisor.generate_revision_report(revision_result)
        
        self.assertIsInstance(report, str)
        self.assertIn("修订报告", report)
        self.assertIn("第1章", report)


if __name__ == '__main__':
    unittest.main()
