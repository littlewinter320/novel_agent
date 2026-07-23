"""
DeAIChecker 单元测试

测试去AI味检查器的核心功能:
- AI句式检测
- 频率统计
- 阈值判定
- 报告生成
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
from core.de_ai_checker import DeAIChecker, get_de_ai_checker
import config


class TestDeAIChecker(unittest.TestCase):
    """DeAIChecker 测试类"""
    
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
        checker = DeAIChecker()
        self.assertIsNotNone(checker)
        self.assertEqual(checker.check_results, [])
        self.assertEqual(len(checker.AI_TICS_PATTERNS), 15)
    
    def test_check_ai_tics_pass(self):
        """测试AI句式检测-通过"""
        checker = DeAIChecker()
        
        # 正常文本，不包含AI句式
        content = "主角挥剑斩向敌人，鲜血飞溅。他深吸一口气，继续向前冲去。"
        
        result = checker.check_ai_tics(content)
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result["pass"])
        self.assertIn("tics_count", result)
        self.assertEqual(len(result["issues"]), 0)
    
    def test_check_ai_tics_fail(self):
        """测试AI句式检测-不通过"""
        checker = DeAIChecker()

        # 包含多个AI句式的文本，每个句式出现2次以超过阈值1
        content = """
        首先，我们需要分析局势。其次，制定计划。最后，执行行动。
        首先，我们需要分析局势。其次，制定计划。最后，执行行动。
        值得一提的是，这个计划至关重要。值得一提的是，敌人很强大。
        综上所述，我们必须谨慎。综上所述，这是一场硬仗。
        """

        result = checker.check_ai_tics(content)

        self.assertIsInstance(result, dict)
        self.assertFalse(result["pass"])
        self.assertGreater(len(result["issues"]), 0)
        self.assertGreater(len(result["suggestions"]), 0)
    
    def test_check_ai_tics_count(self):
        """测试AI句式频率统计"""
        checker = DeAIChecker()
        
        content = "首先，我们要分析。其次，制定计划。最后，执行。"
        
        result = checker.check_ai_tics(content)
        
        self.assertIn("tics_count", result)
        tics_count = result["tics_count"]
        
        # 验证统计了所有15种句式
        self.assertEqual(len(tics_count), 15)
        
        # 验证检测到了"首先...其次...最后"
        self.assertGreater(tics_count.get("首先...其次...最后", 0), 0)
    
    def test_generate_report(self):
        """测试生成报告"""
        checker = DeAIChecker()
        
        # 先执行检查
        content = "这是一段正常的文本。"
        checker.check_ai_tics(content)
        
        # 生成报告
        report = checker.generate_report()
        
        self.assertIsInstance(report, str)
        self.assertIn("AI味检查报告", report)
        self.assertIn("总体结果", report)
        self.assertIn("句式统计", report)
    
    def test_generate_report_with_specific_result(self):
        """测试生成特定结果的报告"""
        checker = DeAIChecker()
        
        check_result = {
            "pass": False,
            "tics_count": {"首先...其次...最后": 2, "值得一提的是": 1},
            "issues": ["AI句式'首先...其次...最后'出现2次"],
            "suggestions": ["减少使用'首先...其次...最后'"]
        }
        
        report = checker.generate_report(check_result)
        
        self.assertIsInstance(report, str)
        self.assertIn("不通过", report)
        self.assertIn("问题列表", report)
        self.assertIn("改进建议", report)
    
    def test_ai_tics_patterns_defined(self):
        """测试AI句式模式定义"""
        checker = DeAIChecker()
        
        # 验证定义了15种AI句式
        self.assertEqual(len(checker.AI_TICS_PATTERNS), 15)
        
        # 验证每个模式都是正则表达式字符串
        for name, pattern in checker.AI_TICS_PATTERNS.items():
            self.assertIsInstance(name, str)
            self.assertIsInstance(pattern, str)
            self.assertGreater(len(pattern), 0)


if __name__ == '__main__':
    unittest.main()
