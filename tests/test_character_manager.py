"""
CharacterManager 单元测试

测试角色管理系统的核心功能:
- 角色上下文加载
- 角色状态更新
- 一致性检查
- 添加角色
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
from core.character_manager import CharacterManager, get_character_manager
import config


class TestCharacterManager(unittest.TestCase):
    """CharacterManager 测试类"""
    
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
    
    @patch('core.character_manager.get_llm_client')
    @patch('core.character_manager.TruthFiles')
    def test_initialization(self, mock_truth_files, mock_get_client):
        """测试初始化"""
        mock_tf_instance = MagicMock()
        mock_tf_instance.get_file.return_value = {"characters": {}}
        mock_truth_files.return_value = mock_tf_instance
        mock_get_client.return_value = MockLLMClient()
        
        cm = CharacterManager()
        self.assertIsNotNone(cm.truth_files)
        self.assertIsNotNone(cm.llm_client)
        self.assertEqual(cm.characters, {})
    
    @patch('core.character_manager.get_llm_client')
    @patch('core.character_manager.TruthFiles')
    def test_load_character_context(self, mock_truth_files, mock_get_client):
        """测试加载角色上下文"""
        mock_tf_instance = MagicMock()
        mock_tf_instance.get_file.return_value = {
            "characters": {
                "protagonist": {
                    "name": "主角",
                    "personality": "勇敢"
                }
            }
        }
        mock_truth_files.return_value = mock_tf_instance
        mock_get_client.return_value = MockLLMClient()
        
        cm = CharacterManager()
        
        # 加载所有角色
        context = cm.load_character_context()
        self.assertIsInstance(context, dict)
        
        # 加载指定角色
        context = cm.load_character_context(["protagonist"])
        self.assertIn("protagonist", context)
    
    @patch('core.character_manager.get_llm_client')
    @patch('core.character_manager.TruthFiles')
    def test_add_character(self, mock_truth_files, mock_get_client):
        """测试添加角色"""
        mock_tf_instance = MagicMock()
        mock_tf_instance.get_file.return_value = {"characters": {}}
        mock_truth_files.return_value = mock_tf_instance
        mock_get_client.return_value = MockLLMClient()
        
        cm = CharacterManager()
        
        character_info = {
            "name": "主角",
            "personality": "勇敢",
            "current_goal": "修炼"
        }
        
        result = cm.add_character("protagonist", character_info)
        self.assertTrue(result)
        self.assertIn("protagonist", cm.characters)
    
    @patch('core.character_manager.get_llm_client')
    @patch('core.character_manager.TruthFiles')
    def test_update_character_state(self, mock_truth_files, mock_get_client):
        """测试更新角色状态"""
        mock_tf_instance = MagicMock()
        mock_tf_instance.get_file.return_value = {
            "characters": {
                "protagonist": {
                    "name": "主角",
                    "personality": "勇敢",
                    "relationships": [],
                    "secrets": []
                }
            }
        }
        mock_truth_files.return_value = mock_tf_instance
        mock_get_client.return_value = MockLLMClient()
        
        cm = CharacterManager()
        
        result = cm.update_character_state(
            character_id="protagonist",
            chapter_content="主角获得了新的能力"
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn("updated", result)
    
    @patch('core.character_manager.get_llm_client')
    @patch('core.character_manager.TruthFiles')
    def test_check_consistency(self, mock_truth_files, mock_get_client):
        """测试一致性检查"""
        mock_tf_instance = MagicMock()
        mock_tf_instance.get_file.return_value = {
            "characters": {
                "protagonist": {
                    "name": "主角",
                    "personality": "勇敢"
                }
            }
        }
        mock_truth_files.return_value = mock_tf_instance

        # 使用自定义Mock，返回check_consistency期望的JSON格式
        mock_client = MockLLMClient()
        mock_client.generate = lambda prompt, system_prompt=None: '{"consistent": true, "issues": [], "suggestions": []}'
        mock_get_client.return_value = mock_client

        cm = CharacterManager()

        result = cm.check_consistency(
            character_id="protagonist",
            behavior="主角勇敢地面对敌人"
        )

        self.assertIsInstance(result, dict)
        self.assertIn("consistent", result)
        self.assertTrue(result["consistent"])


if __name__ == '__main__':
    unittest.main()
