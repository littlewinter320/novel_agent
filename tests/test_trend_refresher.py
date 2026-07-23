"""TrendRefresher 单元测试"""
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
from core.trend_refresher import TrendRefresher, get_trend_refresher
import config


class TestTrendRefresher(unittest.TestCase):
    """TrendRefresher 测试类"""
    
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
    
    @patch('core.trend_refresher.get_llm_client')
    def test_initialization(self, mock_get_client):
        """测试初始化"""
        mock_get_client.return_value = MockLLMClient()
        refresher = TrendRefresher()
        self.assertIsNotNone(refresher)
        self.assertIsNotNone(refresher.llm_client)
        self.assertIsNotNone(refresher.meme_library)
        self.assertIsNotNone(refresher.expression_variants)
    
    @patch('core.trend_refresher.get_llm_client')
    def test_get_trend_refresher_singleton(self, mock_get_client):
        """测试单例模式"""
        mock_get_client.return_value = MockLLMClient()
        r1 = get_trend_refresher()
        r2 = get_trend_refresher()
        self.assertIs(r1, r2)
    
    @patch('core.trend_refresher.get_llm_client')
    def test_check_trigger(self, mock_get_client):
        """测试检查触发条件（替代不存在的should_refresh方法）"""
        mock_get_client.return_value = MockLLMClient()
        refresher = TrendRefresher()
        
        # 测试章节间隔未达到最小间隔
        result = refresher.check_trigger(current_chapter=3, last_refresh_chapter=0)
        self.assertFalse(result["should_refresh"])
        
        # 测试章节间隔达到最小间隔
        result = refresher.check_trigger(
            current_chapter=config.TREND_REFRESH_MIN_INTERVAL + 1,
            last_refresh_chapter=0
        )
        self.assertTrue(result["should_refresh"])
    
    @patch('core.trend_refresher.get_llm_client')
    def test_refresh(self, mock_get_client):
        """测试执行热点刷新（替代不存在的refresh_trends方法）"""
        mock_get_client.return_value = MockLLMClient()
        refresher = TrendRefresher()
        
        result = refresher.refresh("玄幻", current_chapter=10)
        
        self.assertIsInstance(result, dict)
        self.assertIn("refreshed", result)
        self.assertIn("refreshed_at", result)
        self.assertEqual(result["genre"], "玄幻")
    
    @patch('core.trend_refresher.get_llm_client')
    def test_generate_refresh_report(self, mock_get_client):
        """测试生成刷新报告（替代不存在的get_current_trends方法）"""
        mock_get_client.return_value = MockLLMClient()
        refresher = TrendRefresher()
        
        report = refresher.generate_refresh_report(
            genre="玄幻",
            new_memes_count=5,
            new_variants_count=3,
            stale_memes=[],
            current_chapter=10
        )
        
        self.assertIsInstance(report, str)
        self.assertIn("热点更新报告", report)
        self.assertIn("玄幻", report)
    
    @patch('core.trend_refresher.get_llm_client')
    def test_check_stale_content(self, mock_get_client):
        """测试检查过时内容（替代不存在的update_refresh_status方法）"""
        mock_get_client.return_value = MockLLMClient()
        refresher = TrendRefresher()
        
        # 检查过时内容
        result = refresher._check_stale_content(current_chapter=100)
        
        self.assertIsInstance(result, dict)
        self.assertIn("has_stale", result)
        self.assertIn("stale_memes", result)


if __name__ == '__main__':
    unittest.main()
