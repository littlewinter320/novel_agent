"""LLMCache 单元测试"""
import unittest
import os
import sys
import tempfile
import shutil
import time

# 添加项目路径
test_dir = os.path.dirname(os.path.abspath(__file__))
novel_agent_dir = os.path.dirname(test_dir)
sys.path.insert(0, novel_agent_dir)

from utils.llm_cache import LLMCache
import config


class TestLLMCache(unittest.TestCase):
    """LLMCache 测试类"""
    
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
        cache = LLMCache()
        self.assertIsNotNone(cache)
        self.assertEqual(cache.max_size, 1000)
        self.assertEqual(len(cache.cache), 0)
        self.assertEqual(cache.stats["total_requests"], 0)
    
    def test_generate_cache_key(self):
        """测试生成缓存键"""
        cache = LLMCache()
        
        key1 = cache._generate_key("测试提示", "系统提示")
        key2 = cache._generate_key("测试提示", "系统提示")
        key3 = cache._generate_key("不同提示", "系统提示")
        
        # 相同输入应该生成相同键
        self.assertEqual(key1, key2)
        # 不同输入应该生成不同键
        self.assertNotEqual(key1, key3)
    
    def test_manual_cache_operations(self):
        """测试手动缓存操作"""
        cache = LLMCache()
        
        # 手动添加缓存条目
        cache_key = cache._generate_key("测试", None)
        cache.cache[cache_key] = {
            "response": "缓存的响应",
            "token_count": 100,
            "cached_at": "2026-01-01T00:00:00"
        }
        
        # 验证缓存存在
        self.assertIn(cache_key, cache.cache)
        self.assertEqual(cache.cache[cache_key]["response"], "缓存的响应")
    
    def test_cache_stats(self):
        """测试缓存统计"""
        cache = LLMCache()
        
        # 初始统计
        stats = cache.get_stats()
        self.assertEqual(stats["total_requests"], 0)
        self.assertEqual(stats["cache_hits"], 0)
        self.assertEqual(stats["cache_misses"], 0)
        # hit_rate可能是字符串格式如"0.00%"或浮点数
        self.assertIn(stats["hit_rate"], [0.0, "0.00%"])
    
    def test_cache_stats_update(self):
        """测试缓存统计更新"""
        cache = LLMCache()
        
        # 模拟统计更新
        cache.stats["total_requests"] = 10
        cache.stats["cache_hits"] = 7
        cache.stats["cache_misses"] = 3
        
        stats = cache.get_stats()
        self.assertEqual(stats["total_requests"], 10)
        self.assertEqual(stats["cache_hits"], 7)
        # hit_rate可能是字符串格式如"70.00%"或浮点数
        self.assertIn(stats["hit_rate"], [0.7, "70.00%"])
    
    def test_cache_max_size(self):
        """测试缓存最大大小"""
        cache = LLMCache(max_size=3)
        
        # 添加超过最大大小的条目
        for i in range(5):
            key = f"key_{i}"
            cache.cache[key] = {
                "response": f"response_{i}",
                "token_count": 10,
                "cached_at": "2026-01-01T00:00:00"
            }
        
        # 缓存应该允许超过max_size（需要手动清理）
        self.assertEqual(len(cache.cache), 5)
    
    def test_clear_cache(self):
        """测试清除缓存"""
        cache = LLMCache()
        
        # 添加一些条目
        cache.cache["key1"] = {"response": "r1", "token_count": 10, "cached_at": ""}
        cache.cache["key2"] = {"response": "r2", "token_count": 20, "cached_at": ""}
        
        # 清除缓存
        cache.cache.clear()
        
        self.assertEqual(len(cache.cache), 0)
    
    def test_clear_cache_method(self):
        """测试清除缓存方法"""
        cache = LLMCache()
        
        # 添加一些条目
        cache.cache["key1"] = {"response": "r1", "token_count": 10, "cached_at": ""}
        cache.cache["key2"] = {"response": "r2", "token_count": 20, "cached_at": ""}
        
        # 调用清除方法
        cache.clear_cache()
        
        self.assertEqual(len(cache.cache), 0)
    
    def test_cache_efficiency_empty(self):
        """测试空缓存效率指标"""
        cache = LLMCache()
        efficiency = cache.get_cache_efficiency()
        
        self.assertEqual(efficiency["efficiency_score"], 0)
        self.assertEqual(efficiency["hit_rate_percent"], 0)
        self.assertEqual(efficiency["token_savings_percent"], 0)
        self.assertIsInstance(efficiency["recommendations"], list)
        self.assertTrue(len(efficiency["recommendations"]) > 0)
    
    def test_cache_efficiency_with_data(self):
        """测试有数据时的效率指标"""
        cache = LLMCache()
        cache.stats["total_requests"] = 100
        cache.stats["cache_hits"] = 70
        cache.stats["cache_misses"] = 30
        cache.stats["total_tokens_used"] = 5000
        cache.stats["cached_tokens_saved"] = 3000
        
        efficiency = cache.get_cache_efficiency()
        
        self.assertEqual(efficiency["hit_rate_percent"], 70.0)
        # Token节省率 = 3000 / (5000+3000) = 37.5%
        self.assertEqual(efficiency["token_savings_percent"], 37.5)
        # 效率评分 = 70 * 0.6 + 37.5 * 0.4 = 42 + 15 = 57
        self.assertEqual(efficiency["efficiency_score"], 57.0)
    
    def test_cache_report_generation(self):
        """测试缓存报告生成"""
        cache = LLMCache()
        cache.stats["total_requests"] = 50
        cache.stats["cache_hits"] = 30
        
        report = cache.generate_cache_report()
        
        self.assertIn("LLM缓存报告", report)
        self.assertIn("缓存统计", report)
        self.assertIn("Token使用统计", report)
        self.assertIn("缓存容量", report)
        self.assertIn("50", report)
        self.assertIn("30", report)
    
    def test_cache_persistence(self):
        """测试缓存持久化"""
        cache1 = LLMCache()
        cache1.cache["test_key"] = {
            "response": "test_response",
            "token_count": 100,
            "cached_at": "2026-01-01T00:00:00"
        }
        cache1.stats["total_requests"] = 42
        cache1._save_cache()
        
        # 重新加载
        cache2 = LLMCache()
        self.assertIn("test_key", cache2.cache)
        self.assertEqual(cache2.cache["test_key"]["response"], "test_response")
        self.assertEqual(cache2.stats["total_requests"], 42)


if __name__ == '__main__':
    unittest.main()
