"""
ModificationTracker 单元测试

测试修改追踪系统的核心功能:
- 记录修改
- 评估影响
- 应用修改
- 部分回滚
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
from core.modification_tracker import ModificationTracker, get_modification_tracker
import config


class TestModificationTracker(unittest.TestCase):
    """ModificationTracker 测试类"""
    
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
    
    def test_initialization(self):
        """测试初始化"""
        tracker = ModificationTracker()
        self.assertEqual(tracker.modifications, [])
    
    def test_record_modification(self):
        """测试记录修改"""
        tracker = ModificationTracker()
        
        mod = {
            "content": "修改内容",
            "reason": "修改原因",
            "type": "character"
        }
        
        result = tracker.record_modification(mod)
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result["recorded"])
        self.assertIn("mod_id", result)
        self.assertEqual(len(tracker.modifications), 1)
    
    def test_record_modification_missing_fields(self):
        """测试记录修改缺少必要字段"""
        tracker = ModificationTracker()
        
        mod = {
            "content": "修改内容"
            # 缺少 reason
        }
        
        result = tracker.record_modification(mod)
        
        self.assertFalse(result["recorded"])
        self.assertIn("error", result)
    
    def test_assess_impact(self):
        """测试评估影响"""
        tracker = ModificationTracker()
        
        mod = {
            "content": "修改角色性格",
            "type": "character",
            "target": "protagonist"
        }
        
        impact = tracker.assess_impact(mod)
        
        self.assertIsInstance(impact, dict)
        self.assertIn("affected_chapters", impact)
        self.assertIn("affected_characters", impact)
        self.assertIn("severity", impact)
    
    def test_apply_modifications(self):
        """测试应用修改"""
        tracker = ModificationTracker()
        
        # 添加几个修改
        tracker.record_modification({
            "content": "修改1",
            "reason": "原因1"
        })
        tracker.record_modification({
            "content": "修改2",
            "reason": "原因2"
        })
        
        result = tracker.apply_modifications()
        
        self.assertIsInstance(result, dict)
        self.assertIn("applied_count", result)
        self.assertEqual(result["applied_count"], 2)
    
    def test_partial_rollback(self):
        """测试部分回滚"""
        tracker = ModificationTracker()
        
        # 添加几个修改
        tracker.record_modification({
            "content": "修改1",
            "reason": "原因1",
            "type": "character"
        })
        tracker.record_modification({
            "content": "修改2",
            "reason": "原因2",
            "type": "plot"
        })
        tracker.record_modification({
            "content": "修改3",
            "reason": "原因3",
            "type": "character"
        })
        
        # 回滚到版本1，保留character类型
        result = tracker.partial_rollback(target_version=1, keep_elements=["character"])
        
        self.assertIsInstance(result, dict)
        self.assertIn("rolled_back_count", result)
        self.assertIn("kept_elements", result)


if __name__ == '__main__':
    unittest.main()
