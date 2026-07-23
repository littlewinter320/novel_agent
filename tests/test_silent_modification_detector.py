"""
SilentModificationDetector 单元测试

测试隐性修改检测器的核心功能:
- 文件变更检测
- 对话修改意图检测
- 一致性检查
- 同步操作
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
from core.silent_modification_detector import SilentModificationDetector, get_silent_modification_detector
import config


class TestSilentModificationDetector(unittest.TestCase):
    """SilentModificationDetector 测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.original_data_dir = config.DATA_DIR
        self.original_truth_dir = config.TRUTH_DIR
        config.DATA_DIR = self.test_dir
        config.TRUTH_DIR = self.test_dir
        
    def tearDown(self):
        """测试后清理"""
        config.DATA_DIR = self.original_data_dir
        config.TRUTH_DIR = self.original_truth_dir
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    @patch('core.silent_modification_detector.get_llm_client')
    def test_initialization(self, mock_get_client):
        """测试初始化"""
        mock_get_client.return_value = MockLLMClient()
        detector = SilentModificationDetector()
        self.assertIsNotNone(detector)
        self.assertIsNotNone(detector.llm_client)
        self.assertIsNotNone(detector.truth_files)
        # 文件快照应该是字典（可能为空，因为测试目录没有监控文件）
        self.assertIsInstance(detector.file_snapshots, dict)
    
    @patch('core.silent_modification_detector.get_llm_client')
    def test_get_detector_singleton(self, mock_get_client):
        """测试单例模式"""
        import core.silent_modification_detector as smd_module
        smd_module._silent_modification_detector = None
        
        mock_get_client.return_value = MockLLMClient()
        d1 = get_silent_modification_detector()
        d2 = get_silent_modification_detector()
        self.assertIs(d1, d2)
        
        # 清理
        smd_module._silent_modification_detector = None
    
    @patch('core.silent_modification_detector.get_llm_client')
    def test_check_file_changes_no_files(self, mock_get_client):
        """测试文件变更检测-无监控文件"""
        mock_get_client.return_value = MockLLMClient()
        detector = SilentModificationDetector()
        
        # 测试目录没有监控文件，应该返回未检测到变更
        result = detector.check_file_changes()
        
        self.assertIsInstance(result, dict)
        self.assertIn("detected", result)
        self.assertFalse(result["detected"])
        self.assertIn("changed_files", result)
    
    @patch('core.silent_modification_detector.get_llm_client')
    def test_detect_modification_intent_with_keywords(self, mock_get_client):
        """测试对话修改意图检测-包含修改关键词"""
        mock_get_client.return_value = MockLLMClient()
        detector = SilentModificationDetector()
        
        # 包含修改关键词的消息
        result = detector.detect_modification_intent("我想修改主角的性格")
        
        self.assertIsInstance(result, dict)
        self.assertIn("detected", result)
        # 包含修改关键词，应该检测到
        self.assertTrue(result["detected"])
        self.assertEqual(result["modification_type"], "dialogue_intent")
    
    @patch('core.silent_modification_detector.get_llm_client')
    def test_detect_modification_intent_without_keywords(self, mock_get_client):
        """测试对话修改意图检测-不包含修改关键词"""
        mock_get_client.return_value = MockLLMClient()
        detector = SilentModificationDetector()
        
        # 不包含修改关键词的消息
        result = detector.detect_modification_intent("今天天气真好")
        
        self.assertIsInstance(result, dict)
        self.assertFalse(result["detected"])
    
    @patch('core.silent_modification_detector.get_llm_client')
    def test_check_consistency(self, mock_get_client):
        """测试一致性检查"""
        mock_get_client.return_value = MockLLMClient()
        detector = SilentModificationDetector()
        
        # 无章节内容的一致性检查
        result = detector.check_consistency()
        
        self.assertIsInstance(result, dict)
        self.assertIn("detected", result)
    
    @patch('core.silent_modification_detector.get_llm_client')
    def test_sync_all(self, mock_get_client):
        """测试同步操作"""
        mock_get_client.return_value = MockLLMClient()
        detector = SilentModificationDetector()
        
        # 执行同步
        result = detector.sync_all("accept_all")
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result["synced"])
        self.assertEqual(result["sync_type"], "accept_all")
    
    @patch('core.silent_modification_detector.get_llm_client')
    def test_run_full_check(self, mock_get_client):
        """测试完整检查"""
        mock_get_client.return_value = MockLLMClient()
        detector = SilentModificationDetector()
        
        # 运行完整检查
        result = detector.run_full_check()
        
        self.assertIsInstance(result, dict)
        self.assertIn("detected", result)
        self.assertIn("check_results", result)


if __name__ == '__main__':
    unittest.main()
