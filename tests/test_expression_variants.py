"""
ExpressionVariants 单元测试

测试表达变体库的核心功能:
- 变体获取
- 重复检测（传入字符串列表，检查返回结构）
- 替换建议
- 变体添加
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
from core.expression_variants import ExpressionVariants, get_expression_variants
import config


class TestExpressionVariants(unittest.TestCase):
    """ExpressionVariants 测试类"""
    
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
        variants = ExpressionVariants()
        self.assertIsNotNone(variants)
        self.assertIsInstance(variants.variants, dict)
        self.assertIsInstance(variants.usage_stats, dict)
    
    def test_get_expression_variants_singleton(self):
        """测试单例模式"""
        # 重置全局实例
        import core.expression_variants as ev_module
        ev_module._expression_variants = None
        
        ev1 = get_expression_variants()
        ev2 = get_expression_variants()
        self.assertIs(ev1, ev2)
        
        # 清理
        ev_module._expression_variants = None
    
    def test_get_variant(self):
        """测试获取表达变体"""
        variants = ExpressionVariants()
        
        # 获取已知表达的变体
        result = variants.get_variant("震惊")
        
        self.assertIsInstance(result, dict)
        self.assertIn("variant", result)
        self.assertIn("alternatives", result)
        self.assertIn("usage_count", result)
        self.assertEqual(result["base"], "震惊")
    
    def test_get_variant_unknown_expression(self):
        """测试获取未知表达的变体"""
        variants = ExpressionVariants()
        
        # 未知表达应该返回自身
        result = variants.get_variant("未知表达")
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result["variant"], "未知表达")
    
    def test_add_variant(self):
        """测试添加变体"""
        variants = ExpressionVariants()
        
        # 添加新变体（使用一个不在默认列表中的变体）
        success = variants.add_variant("高兴", "喜笑颜开")
        
        # 验证变体已添加
        self.assertTrue(success)
        self.assertIn("喜笑颜开", variants.variants.get("高兴", []))
    
    def test_check_repetition(self):
        """测试重复检测"""
        variants = ExpressionVariants()
        
        # 模拟最近章节内容（字符串列表，不是字典列表）
        recent_chapters = [
            "他很高兴，很高兴，很高兴，很高兴，很高兴",
            "他很高兴，很高兴，很高兴，很高兴",
            "他很高兴，很高兴，很高兴"
        ]
        
        result = variants.check_repetition(recent_chapters, window_size=3)
        
        self.assertIsInstance(result, dict)
        self.assertIn("is_overused", result)
        self.assertIn("overused_words", result)
        self.assertIn("window_size", result)
        self.assertIn("total_chapters", result)
        self.assertEqual(result["total_chapters"], 3)
    
    def test_suggest_replacement(self):
        """测试替换建议"""
        variants = ExpressionVariants()
        
        # 获取替换建议
        result = variants.suggest_replacement("高兴")
        
        self.assertIsInstance(result, dict)
        self.assertIn("suggestion", result)
        self.assertIn("alternatives", result)
    
    def test_suggest_replacement_unknown_word(self):
        """测试未知词汇的替换建议"""
        variants = ExpressionVariants()
        
        # 未知词汇应该返回自身
        result = variants.suggest_replacement("不存在的词汇")
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result["suggestion"], "不存在的词汇")
    
    def test_get_all_variants(self):
        """测试获取所有变体"""
        variants = ExpressionVariants()
        
        all_variants = variants.get_all_variants()
        
        self.assertIsInstance(all_variants, dict)
        self.assertTrue(len(all_variants) > 0)
    
    def test_reset_usage_stats(self):
        """测试重置使用统计"""
        variants = ExpressionVariants()
        
        # 先使用一些变体
        variants.get_variant("震惊")
        variants.get_variant("高兴")
        
        # 验证有使用统计
        self.assertTrue(len(variants.usage_stats) > 0)
        
        # 重置统计
        variants.reset_usage_stats()
        
        # 验证统计已清空
        self.assertEqual(len(variants.usage_stats), 0)


if __name__ == '__main__':
    unittest.main()
