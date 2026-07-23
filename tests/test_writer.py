"""WriterAgent 单元测试"""
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
from agents.writer import WriterAgent, get_writer_agent
import config


class TestWriterAgent(unittest.TestCase):
    """WriterAgent 测试类"""
    
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
    
    @patch('agents.writer.get_llm_client')
    def test_initialization(self, mock_get_client):
        """测试初始化"""
        mock_get_client.return_value = MockLLMClient()
        writer = WriterAgent()
        self.assertIsNotNone(writer.llm_client)
        self.assertIsNotNone(writer.genre_knowledge_base)
        self.assertIsNotNone(writer.truth_files)
        self.assertEqual(writer._chapter_cache, {})
    
    @patch('agents.writer.get_llm_client')
    def test_get_writer_agent_singleton(self, mock_get_client):
        """测试单例模式"""
        mock_get_client.return_value = MockLLMClient()
        writer1 = get_writer_agent()
        writer2 = get_writer_agent()
        self.assertIs(writer1, writer2)
    
    @patch('agents.writer.get_llm_client')
    def test_writing_rules(self, mock_get_client):
        """测试写作规则"""
        mock_get_client.return_value = MockLLMClient()
        writer = WriterAgent()
        
        # 验证规则数量
        self.assertEqual(len(writer.WRITING_RULES), 25)
        
        # 验证规则格式
        for rule in writer.WRITING_RULES:
            self.assertIsInstance(rule, str)
            self.assertTrue(len(rule) > 0)
    
    @patch('agents.writer.get_llm_client')
    def test_generate_self_check(self, mock_get_client):
        """测试生成自检表"""
        mock_get_client.return_value = MockLLMClient()
        writer = WriterAgent()
        
        chapter_plan = {
            "chapter_num": 1,
            "chapter_title": "第一章",
            "core_event": "主角觉醒"
        }
        
        self_check = writer.generate_self_check(chapter_plan, "玄幻")
        
        self.assertIsInstance(self_check, dict)
        self.assertIn("chapter_num", self_check)
        self.assertIn("involved_characters", self_check)
        self.assertIn("involved_foreshadows", self_check)
        self.assertIn("excitement_design", self_check)
    
    @patch('agents.writer.get_llm_client')
    def test_build_context(self, mock_get_client):
        """测试构建上下文"""
        mock_get_client.return_value = MockLLMClient()
        writer = WriterAgent()
        
        chapter_plan = {
            "chapter_num": 1,
            "chapter_title": "第一章",
            "core_event": "主角觉醒"
        }
        
        context = writer._build_context(chapter_plan, "玄幻")
        
        self.assertIsInstance(context, dict)
        self.assertIn("world_state", context)
        self.assertIn("character_matrix", context)
        self.assertIn("plot_progress", context)
        self.assertIn("foreshadow_hooks", context)
    
    @patch('agents.writer.get_llm_client')
    def test_chapter_cache(self, mock_get_client):
        """测试章节缓存"""
        mock_get_client.return_value = MockLLMClient()
        writer = WriterAgent()
        
        # 模拟缓存数据
        chapter_data = {
            "chapter_num": 1,
            "chapter_content": "测试内容",
            "word_count": 100
        }
        
        writer._chapter_cache[1] = chapter_data
        
        # 验证缓存存在
        self.assertEqual(writer._chapter_cache[1], chapter_data)
        
        # 清除缓存
        writer._chapter_cache.clear()
        self.assertEqual(len(writer._chapter_cache), 0)


if __name__ == '__main__':
    unittest.main()
