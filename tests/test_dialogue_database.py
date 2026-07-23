"""
DialogueDatabase 单元测试

测试对话数据库的核心功能:
- 对话记录
- 对话分析
- 叙事逻辑提取
- 推理报告生成
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
from core.dialogue_database import DialogueDatabase
import config


class TestDialogueDatabase(unittest.TestCase):
    """DialogueDatabase 测试类"""
    
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
    
    @patch('core.dialogue_database.get_llm_client')
    def test_initialization(self, mock_get_client):
        """测试初始化"""
        mock_get_client.return_value = MockLLMClient()
        db = DialogueDatabase()
        self.assertIsNotNone(db)
        self.assertIsNotNone(db.llm_client)
        self.assertIsInstance(db.dialogues, list)
        self.assertIsInstance(db.analysis_results, list)
    
    @patch('core.dialogue_database.get_llm_client')
    def test_record_dialogue(self, mock_get_client):
        """测试记录对话"""
        mock_get_client.return_value = MockLLMClient()
        db = DialogueDatabase()
        
        db.record_dialogue(
            user_message="帮我写一个玄幻小说",
            assistant_response="好的，我来帮你创作一个玄幻小说"
        )
        
        self.assertEqual(len(db.dialogues), 1)
        self.assertEqual(db.dialogues[0]["user_message"], "帮我写一个玄幻小说")
        self.assertIn("timestamp", db.dialogues[0])
    
    @patch('core.dialogue_database.get_llm_client')
    def test_record_multiple_dialogues(self, mock_get_client):
        """测试记录多条对话"""
        mock_get_client.return_value = MockLLMClient()
        db = DialogueDatabase()
        
        db.record_dialogue(user_message="消息1", assistant_response="回复1")
        db.record_dialogue(user_message="消息2", assistant_response="回复2")
        db.record_dialogue(user_message="消息3", assistant_response="回复3")
        
        self.assertEqual(len(db.dialogues), 3)
    
    @patch('core.dialogue_database.get_llm_client')
    def test_get_dialogue_history(self, mock_get_client):
        """测试获取对话历史"""
        mock_get_client.return_value = MockLLMClient()
        db = DialogueDatabase()
        
        # 添加5条对话
        for i in range(5):
            db.record_dialogue(
                user_message=f"消息{i}",
                assistant_response=f"回复{i}"
            )
        
        # 获取最近3条
        recent = db.get_dialogue_history(limit=3)
        
        self.assertEqual(len(recent), 3)
    
    @patch('core.dialogue_database.get_llm_client')
    def test_clear_dialogues(self, mock_get_client):
        """测试清除对话"""
        mock_get_client.return_value = MockLLMClient()
        db = DialogueDatabase()
        
        db.record_dialogue(user_message="消息1", assistant_response="回复1")
        db.record_dialogue(user_message="消息2", assistant_response="回复2")
        
        self.assertEqual(len(db.dialogues), 2)
        
        db.clear_dialogues()
        
        self.assertEqual(len(db.dialogues), 0)
    
    @patch('core.dialogue_database.get_llm_client')
    def test_analyze_dialogues(self, mock_get_client):
        """测试分析对话"""
        mock_get_client.return_value = MockLLMClient()
        db = DialogueDatabase()
        
        db.record_dialogue(
            user_message="我想写一个修仙故事",
            assistant_response="好的，修仙题材很受欢迎"
        )
        
        result = db.analyze_dialogues(recent_count=10)
        
        self.assertIsInstance(result, dict)
        # 验证分析结果包含关键字段
        self.assertTrue(len(db.analysis_results) > 0)
    
    @patch('core.dialogue_database.get_llm_client')
    def test_get_narrative_logic(self, mock_get_client):
        """测试获取叙事逻辑"""
        mock_get_client.return_value = MockLLMClient()
        db = DialogueDatabase()
        
        logic = db.get_narrative_logic()
        
        # 应该返回叙事逻辑信息
        self.assertIsNotNone(logic)
    
    @patch('core.dialogue_database.get_llm_client')
    def test_get_reasoning_report(self, mock_get_client):
        """测试获取推理报告"""
        mock_get_client.return_value = MockLLMClient()
        db = DialogueDatabase()
        
        report = db.get_reasoning_report()
        
        # 应该返回推理报告
        self.assertIsNotNone(report)


if __name__ == '__main__':
    unittest.main()
