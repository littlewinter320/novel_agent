"""
CheckpointManager 单元测试

测试断点管理器的核心功能:
- 保存checkpoint
- 列出checkpoint
- 恢复checkpoint
- 加载最新checkpoint
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
from core.checkpoint_manager import CheckpointManager, get_checkpoint_manager
import config


class TestCheckpointManager(unittest.TestCase):
    """CheckpointManager 测试类"""
    
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
        cm = CheckpointManager()
        self.assertIsNotNone(cm.checkpoint_dir)
        self.assertEqual(cm.checkpoints, [])
    
    def test_save_checkpoint(self):
        """测试保存checkpoint"""
        cm = CheckpointManager()
        
        state = {
            "chapter": 1,
            "progress": "completed"
        }
        
        result = cm.save_checkpoint(
            step="章节生成",
            state=state,
            is_manual=False
        )
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result["saved"])
        self.assertIn("checkpoint_id", result)
        self.assertIn("step", result)
        self.assertEqual(len(cm.checkpoints), 1)
    
    def test_save_manual_checkpoint(self):
        """测试手动保存checkpoint"""
        cm = CheckpointManager()
        
        result = cm.save_checkpoint(
            step="手动保存",
            state={"test": "data"},
            is_manual=True
        )
        
        self.assertTrue(result["saved"])
        self.assertTrue(cm.checkpoints[0]["is_manual"])
    
    def test_list_checkpoints(self):
        """测试列出checkpoint"""
        cm = CheckpointManager()
        
        # 保存几个checkpoint
        cm.save_checkpoint("步骤1", {"data": 1})
        cm.save_checkpoint("步骤2", {"data": 2})
        cm.save_checkpoint("步骤3", {"data": 3})
        
        checkpoints = cm.list_checkpoints()
        
        self.assertIsInstance(checkpoints, list)
        self.assertEqual(len(checkpoints), 3)
    
    def test_restore_checkpoint(self):
        """测试恢复checkpoint"""
        cm = CheckpointManager()
        
        state = {
            "chapter": 5,
            "status": "in_progress"
        }
        
        result = cm.save_checkpoint("章节生成", state)
        checkpoint_id = result["checkpoint_id"]
        
        # 恢复checkpoint
        restored_state = cm.restore_checkpoint(checkpoint_id)
        
        self.assertIsNotNone(restored_state)
        self.assertEqual(restored_state["chapter"], 5)
        self.assertEqual(restored_state["status"], "in_progress")
    
    def test_load_latest_checkpoint(self):
        """测试加载最新checkpoint"""
        cm = CheckpointManager()
        
        # 保存几个checkpoint
        cm.save_checkpoint("步骤1", {"version": 1})
        cm.save_checkpoint("步骤2", {"version": 2})
        cm.save_checkpoint("步骤3", {"version": 3})
        
        # 加载最新的
        latest = cm.load_latest_checkpoint()
        
        self.assertIsNotNone(latest)
        self.assertEqual(latest["version"], 3)
    
    def test_restore_nonexistent_checkpoint(self):
        """测试恢复不存在的checkpoint"""
        cm = CheckpointManager()
        
        result = cm.restore_checkpoint(999)
        
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
