"""
AuditorAgent 单元测试

测试审计员的核心功能:
- 15维度章节审计
- AI味检测
- 审计报告生成
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
from agents.auditor import AuditorAgent, get_auditor_agent
import config


class TestAuditorAgent(unittest.TestCase):
    """AuditorAgent 测试类"""
    
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
    
    @patch('agents.auditor.get_llm_client')
    def test_initialization(self, mock_get_client):
        """测试初始化"""
        mock_get_client.return_value = MockLLMClient()
        auditor = AuditorAgent()
        self.assertIsNotNone(auditor.llm_client)
        self.assertIsNotNone(auditor.genre_knowledge_base)
        self.assertIsNotNone(auditor.truth_files)
    
    @patch('agents.auditor.get_llm_client')
    def test_get_auditor_agent_singleton(self, mock_get_client):
        """测试单例模式"""
        import agents.auditor as aud_module
        aud_module._auditor_agent = None
        
        mock_get_client.return_value = MockLLMClient()
        auditor1 = get_auditor_agent()
        auditor2 = get_auditor_agent()
        self.assertIs(auditor1, auditor2)
        
        # 清理
        aud_module._auditor_agent = None
    
    @patch('agents.auditor.get_llm_client')
    def test_ai_tics_patterns_defined(self, mock_get_client):
        """测试AI味模式定义"""
        mock_get_client.return_value = MockLLMClient()
        auditor = AuditorAgent()
        
        # 验证AI味模式数量（15种）
        self.assertEqual(len(auditor.AI_TICS_PATTERNS), 15)
        
        # 验证每个模式都是正则表达式字符串
        for name, pattern in auditor.AI_TICS_PATTERNS.items():
            self.assertIsInstance(name, str)
            self.assertIsInstance(pattern, str)
    
    @patch('agents.auditor.get_llm_client')
    def test_audit_chapter(self, mock_get_client):
        """测试章节审计"""
        mock_get_client.return_value = MockLLMClient()
        auditor = AuditorAgent()
        
        chapter_content = "测试章节内容"
        chapter_num = 1
        genre = "玄幻"
        
        audit_result = auditor.audit_chapter(chapter_content, chapter_num, genre)
        
        self.assertIsInstance(audit_result, dict)
        self.assertIn("chapter_num", audit_result)
        self.assertIn("audit_results", audit_result)
        self.assertIn("overall_pass", audit_result)
        self.assertIn("issues", audit_result)
        self.assertIn("suggestions", audit_result)
        # 验证15个维度的审计结果
        self.assertEqual(len(audit_result["audit_results"]), 15)
    
    @patch('agents.auditor.get_llm_client')
    def test_audit_chapter_with_style_guide(self, mock_get_client):
        """测试带风格指南的章节审计"""
        mock_get_client.return_value = MockLLMClient()
        auditor = AuditorAgent()
        
        chapter_content = "测试章节内容"
        style_guide = {"tone": "热血", "pacing": "快节奏"}
        
        audit_result = auditor.audit_chapter(
            chapter_content, chapter_num=1, genre="玄幻", style_guide=style_guide
        )
        
        self.assertIsInstance(audit_result, dict)
        self.assertIn("audit_results", audit_result)
    
    @patch('agents.auditor.get_llm_client')
    def test_generate_audit_report(self, mock_get_client):
        """测试生成审计报告"""
        mock_get_client.return_value = MockLLMClient()
        auditor = AuditorAgent()
        
        # 先执行审计获取结果
        audit_result = {
            "chapter_num": 1,
            "audit_results": [
                {"dimension": "角色OOC检查", "pass": True, "issues": [], "suggestions": []}
            ],
            "overall_pass": True,
            "issues": [],
            "suggestions": [],
            "audited_at": "2026-07-23T00:00:00"
        }
        
        report = auditor.generate_audit_report(audit_result)
        
        self.assertIsInstance(report, str)
        self.assertTrue(len(report) > 0)


if __name__ == '__main__':
    unittest.main()
