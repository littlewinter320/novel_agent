"""
BatchCoordinator 单元测试

测试批量生成协调器的核心功能:
- 批量生成章节
- 跨章一致性检查
- 生成批量报告
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
from core.batch_coordinator import BatchCoordinator, get_batch_coordinator
import config


class TestBatchCoordinator(unittest.TestCase):
    """BatchCoordinator 测试类"""
    
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
    
    @patch('core.batch_coordinator.get_llm_client')
    def test_initialization(self, mock_get_client):
        """测试初始化"""
        mock_get_client.return_value = MockLLMClient()
        coordinator = BatchCoordinator()
        self.assertIsNotNone(coordinator)
        self.assertIsNotNone(coordinator.llm_client)
        self.assertIsNotNone(coordinator.writer)
        self.assertIsNotNone(coordinator.auditor)
        self.assertIsNotNone(coordinator.revisor)
        self.assertIsNotNone(coordinator.truth_files)
    
    @patch('core.batch_coordinator.get_llm_client')
    def test_get_batch_coordinator_singleton(self, mock_get_client):
        """测试单例模式"""
        import core.batch_coordinator as bc_module
        bc_module._batch_coordinator = None
        
        mock_get_client.return_value = MockLLMClient()
        coord1 = get_batch_coordinator()
        coord2 = get_batch_coordinator()
        self.assertIs(coord1, coord2)
        
        # 清理
        bc_module._batch_coordinator = None
    
    @patch('core.batch_coordinator.get_llm_client')
    def test_check_cross_chapter_consistency_single_chapter(self, mock_get_client):
        """测试跨章一致性检查-单章"""
        mock_get_client.return_value = MockLLMClient()
        coordinator = BatchCoordinator()
        
        chapters = [
            {"chapter_num": 1, "chapter_content": "第一章内容"}
        ]
        
        result = coordinator.check_cross_chapter_consistency(chapters, "玄幻")
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result["pass"])
        self.assertIn("note", result)
    
    @patch('core.batch_coordinator.get_llm_client')
    def test_check_cross_chapter_consistency_multiple_chapters(self, mock_get_client):
        """测试跨章一致性检查-多章"""
        mock_get_client.return_value = MockLLMClient()
        coordinator = BatchCoordinator()
        
        chapters = [
            {"chapter_num": 1, "chapter_content": "第一章内容"},
            {"chapter_num": 2, "chapter_content": "第二章内容"}
        ]
        
        result = coordinator.check_cross_chapter_consistency(chapters, "玄幻")
        
        self.assertIsInstance(result, dict)
        self.assertIn("pass", result)
        self.assertIn("issues", result)
        self.assertIn("checked_at", result)
    
    @patch('core.batch_coordinator.get_llm_client')
    def test_check_cross_chapter_consistency_discontinuous(self, mock_get_client):
        """测试跨章一致性检查-章节号不连续"""
        mock_get_client.return_value = MockLLMClient()
        coordinator = BatchCoordinator()
        
        chapters = [
            {"chapter_num": 1, "chapter_content": "第一章内容"},
            {"chapter_num": 3, "chapter_content": "第三章内容"}
        ]
        
        result = coordinator.check_cross_chapter_consistency(chapters, "玄幻")
        
        self.assertIsInstance(result, dict)
        # 章节号不连续应该产生问题
        self.assertTrue(len(result["issues"]) > 0)
    
    @patch('core.batch_coordinator.get_llm_client')
    def test_generate_batch_report(self, mock_get_client):
        """测试生成批量报告"""
        mock_get_client.return_value = MockLLMClient()
        coordinator = BatchCoordinator()
        
        batch_result = {
            "success_count": 2,
            "total_count": 3,
            "chapters": [
                {"chapter_num": 1, "chapter_title": "第一章", "word_count": 3000},
                {"chapter_num": 2, "chapter_title": "第二章", "word_count": 2800}
            ],
            "cross_chapter_check": {
                "pass": True,
                "issues": []
            }
        }
        
        report = coordinator.generate_batch_report(batch_result)
        
        self.assertIsInstance(report, str)
        self.assertIn("批量生成报告", report)
        self.assertIn("2/3", report)


if __name__ == '__main__':
    unittest.main()
