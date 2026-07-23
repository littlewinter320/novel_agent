"""
Exporter 单元测试

测试导出器的核心功能:
- TXT导出
- Markdown导出
- EPUB导出
- 内部工件过滤
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
from core.exporter import Exporter, get_exporter
import config


class TestExporter(unittest.TestCase):
    """Exporter 测试类"""
    
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
        exporter = Exporter()
        self.assertIsNotNone(exporter)
        self.assertEqual(exporter.chapters, [])
    
    def test_filter_internal_artifacts(self):
        """测试内部工件过滤"""
        exporter = Exporter()
        
        chapter = {
            "chapter_num": 1,
            "chapter_title": "第一章",
            "chapter_content": "测试内容",
            "internal_audit": {"score": 90},
            "internal_checklist": {"items": []}
        }
        
        filtered = exporter._filter_internal_artifacts(chapter)
        
        self.assertIsInstance(filtered, dict)
        self.assertIn("chapter_num", filtered)
        self.assertIn("chapter_title", filtered)
        self.assertIn("chapter_content", filtered)
        # 内部工件应该被过滤掉
        self.assertNotIn("internal_audit", filtered)
        self.assertNotIn("internal_checklist", filtered)
    
    def test_export_txt(self):
        """测试TXT导出"""
        exporter = Exporter()
        
        chapters = [
            {
                "chapter_num": 1,
                "chapter_title": "第一章",
                "chapter_content": "第一章内容"
            },
            {
                "chapter_num": 2,
                "chapter_title": "第二章",
                "chapter_content": "第二章内容"
            }
        ]
        
        output_dir = os.path.join(self.test_dir, "txt_output")
        result = exporter.export_txt(chapters, output_dir)
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result["exported"])
        self.assertEqual(result["format"], "txt")
        self.assertEqual(result["file_count"], 2)
        
        # 验证文件是否创建
        self.assertTrue(os.path.exists(output_dir))
        files = os.listdir(output_dir)
        self.assertEqual(len(files), 2)
    
    def test_export_markdown(self):
        """测试Markdown导出"""
        exporter = Exporter()
        
        chapters = [
            {
                "chapter_num": 1,
                "chapter_title": "第一章",
                "chapter_content": "第一章内容"
            },
            {
                "chapter_num": 2,
                "chapter_title": "第二章",
                "chapter_content": "第二章内容"
            }
        ]
        
        output_file = os.path.join(self.test_dir, "output.md")
        result = exporter.export_markdown(chapters, output_file)
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result["exported"])
        self.assertEqual(result["format"], "markdown")
        self.assertEqual(result["chapter_count"], 2)
        
        # 验证文件是否创建
        self.assertTrue(os.path.exists(output_file))
        
        # 验证文件内容
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("第一章", content)
            self.assertIn("第二章", content)
    
    def test_export_epub_without_library(self):
        """测试EPUB导出（缺少依赖库）"""
        exporter = Exporter()
        
        chapters = [
            {
                "chapter_num": 1,
                "chapter_title": "第一章",
                "chapter_content": "第一章内容"
            }
        ]
        
        output_file = os.path.join(self.test_dir, "output.epub")
        
        # Mock掉ebooklib导入失败的情况
        with patch('builtins.__import__', side_effect=ImportError):
            result = exporter.export_epub(chapters, output_file)
        
        self.assertIsInstance(result, dict)
        self.assertFalse(result["exported"])
        self.assertIn("error", result)
    
    def test_export_empty_chapters(self):
        """测试导出空章节列表"""
        exporter = Exporter()
        
        chapters = []
        output_dir = os.path.join(self.test_dir, "empty_output")
        
        result = exporter.export_txt(chapters, output_dir)
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result["exported"])
        self.assertEqual(result["file_count"], 0)


if __name__ == '__main__':
    unittest.main()
