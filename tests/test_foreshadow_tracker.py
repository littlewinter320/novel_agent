"""
ForeshadowTracker 单元测试

测试伏笔追踪系统的核心功能:
- 伏笔状态检查
- 伏笔状态更新
- 健康度检查
- 添加伏笔
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
from core.foreshadow_tracker import ForeshadowTracker, get_foreshadow_tracker
import config


class TestForeshadowTracker(unittest.TestCase):
    """ForeshadowTracker 测试类"""
    
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
    
    @patch('core.foreshadow_tracker.TruthFiles')
    def test_initialization(self, mock_truth_files):
        """测试初始化"""
        mock_tf_instance = MagicMock()
        mock_tf_instance.get_file.return_value = {"foreshadows": []}
        mock_truth_files.return_value = mock_tf_instance
        
        tracker = ForeshadowTracker()
        self.assertIsNotNone(tracker.truth_files)
        self.assertEqual(tracker.foreshadows, [])
    
    @patch('core.foreshadow_tracker.TruthFiles')
    def test_check_foreshadow_status(self, mock_truth_files):
        """测试伏笔状态检查"""
        mock_tf_instance = MagicMock()
        mock_tf_instance.get_file.return_value = {
            "foreshadows": [
                {
                    "foreshadow_name": "神秘老者",
                    "status": "已埋设",
                    "plant_chapter": 1,
                    "trigger_chapter": 5,
                    "resolve_chapter_range": "10-15"
                }
            ]
        }
        mock_truth_files.return_value = mock_tf_instance
        
        tracker = ForeshadowTracker()
        result = tracker.check_foreshadow_status(current_chapter=5)
        
        self.assertIsInstance(result, dict)
        self.assertIn("should_trigger", result)
        self.assertIn("should_resolve", result)
        self.assertIn("overdue", result)
        self.assertIn("active_count", result)
    
    @patch('core.foreshadow_tracker.TruthFiles')
    def test_update_foreshadow_status(self, mock_truth_files):
        """测试伏笔状态更新"""
        mock_tf_instance = MagicMock()
        mock_tf_instance.get_file.return_value = {
            "foreshadows": [
                {
                    "foreshadow_name": "神秘老者",
                    "status": "未埋设"
                }
            ]
        }
        mock_truth_files.return_value = mock_tf_instance
        
        tracker = ForeshadowTracker()
        result = tracker.update_foreshadow_status(
            chapter_content="神秘老者出现在主角面前",
            current_chapter=1
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn("updated_count", result)
        self.assertIn("updates", result)
    
    @patch('core.foreshadow_tracker.TruthFiles')
    def test_add_foreshadow(self, mock_truth_files):
        """测试添加伏笔"""
        mock_tf_instance = MagicMock()
        mock_tf_instance.get_file.return_value = {"foreshadows": []}
        mock_truth_files.return_value = mock_tf_instance
        
        tracker = ForeshadowTracker()
        
        foreshadow = {
            "foreshadow_name": "神秘宝剑",
            "plant_chapter": 1,
            "trigger_chapter": 10
        }
        
        result = tracker.add_foreshadow(foreshadow)
        self.assertTrue(result)
        self.assertEqual(len(tracker.foreshadows), 1)
    
    @patch('core.foreshadow_tracker.TruthFiles')
    def test_health_check(self, mock_truth_files):
        """测试健康度检查"""
        mock_tf_instance = MagicMock()
        mock_tf_instance.get_file.return_value = {
            "foreshadows": [
                {
                    "foreshadow_name": "神秘老者",
                    "status": "已埋设",
                    "plant_chapter": 1
                }
            ]
        }
        mock_truth_files.return_value = mock_tf_instance
        
        tracker = ForeshadowTracker()
        result = tracker.health_check()
        
        self.assertIsInstance(result, dict)
        self.assertIn("status_counts", result)
        self.assertIn("active_count", result)
        self.assertIn("warnings", result)
        self.assertIn("healthy", result)


if __name__ == '__main__':
    unittest.main()
