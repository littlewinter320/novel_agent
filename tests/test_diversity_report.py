"""
DiversityReport 单元测试

测试多样性统计报告的核心功能:
- 生成统计数据
- 检测过度使用
- 生成报告
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
from core.diversity_report import DiversityReport, get_diversity_report
import config


class TestDiversityReport(unittest.TestCase):
    """DiversityReport 测试类"""
    
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
        report = DiversityReport()
        self.assertIsNotNone(report)
        self.assertEqual(report.statistics, {})
    
    def test_generate_statistics(self):
        """测试生成统计数据"""
        report = DiversityReport()
        
        chapters = [
            {
                "chapter_num": 1,
                "chapter_content": "主角挥剑斩向敌人。他深吸一口气，继续向前冲去。打脸时刻终于到来！"
            },
            {
                "chapter_num": 2,
                "chapter_content": "逆袭成功！主角突破了境界。升级速度惊人，奇遇不断。"
            }
        ]
        
        result = report.generate_statistics(chapters)
        
        self.assertIsInstance(result, dict)
        self.assertIn("vocabulary_stats", result)
        self.assertIn("sentence_stats", result)
        self.assertIn("meme_stats", result)
        self.assertIn("structure_stats", result)
        self.assertIn("chapter_count", result)
        self.assertIn("total_words", result)
    
    def test_generate_statistics_empty(self):
        """测试生成统计数据-空章节"""
        report = DiversityReport()
        
        result = report.generate_statistics([])
        
        self.assertEqual(result, {})
    
    def test_check_overuse(self):
        """测试检测过度使用"""
        report = DiversityReport()
        
        # 先设置一些统计数据
        chapters = [
            {
                "chapter_num": 1,
                "chapter_content": "打脸 打脸 打脸 打脸 打脸 打脸 打脸 打脸 打脸 打脸 打脸"
            }
        ]
        
        report.generate_statistics(chapters)
        result = report.check_overuse()
        
        self.assertIsInstance(result, dict)
        self.assertIn("has_overuse", result)
        self.assertIn("warnings", result)
    
    def test_check_overuse_no_statistics(self):
        """测试检测过度使用-无统计数据"""
        report = DiversityReport()
        
        result = report.check_overuse()
        
        self.assertFalse(result["has_overuse"])
        self.assertEqual(len(result["warnings"]), 0)
    
    def test_generate_report(self):
        """测试生成报告"""
        report = DiversityReport()
        
        # 先设置统计数据
        chapters = [
            {
                "chapter_num": 1,
                "chapter_content": "主角挥剑斩向敌人。他深吸一口气，继续向前冲去。"
            }
        ]
        
        report.generate_statistics(chapters)
        
        # 生成报告
        report_text = report.generate_report()
        
        self.assertIsInstance(report_text, str)
        self.assertIn("多样性统计报告", report_text)
        self.assertIn("词汇统计", report_text)
        self.assertIn("句式统计", report_text)
        self.assertIn("梗使用统计", report_text)
    
    def test_generate_report_no_statistics(self):
        """测试生成报告-无统计数据"""
        report = DiversityReport()
        
        report_text = report.generate_report()
        
        self.assertEqual(report_text, "无统计数据")
    
    def test_analyze_vocabulary(self):
        """测试词汇分析"""
        report = DiversityReport()
        
        text = "主角 挥剑 斩向 敌人 主角 深吸 一口气"
        
        result = report._analyze_vocabulary(text)
        
        self.assertIsInstance(result, dict)
        self.assertIn("total_words", result)
        self.assertIn("unique_words", result)
        self.assertIn("most_common", result)
        
        # 验证"主角"出现了2次
        most_common = result["most_common"]
        self.assertGreater(len(most_common), 0)
    
    def test_analyze_sentences(self):
        """测试句式分析"""
        report = DiversityReport()
        
        text = "主角挥剑斩向敌人。他深吸一口气。继续向前冲去！"
        
        result = report._analyze_sentences(text)
        
        self.assertIsInstance(result, dict)
        self.assertIn("total_sentences", result)
        self.assertIn("avg_length", result)
        self.assertIn("max_length", result)
        self.assertIn("min_length", result)
        
        # 验证句子数量
        self.assertGreater(result["total_sentences"], 0)


if __name__ == '__main__':
    unittest.main()
