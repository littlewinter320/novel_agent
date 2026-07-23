"""
MemeLibrary 单元测试

测试梗库的核心功能:
- 梗获取
- 新鲜度追踪
- 梗组合创新
- 梗添加
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
from core.meme_library import MemeLibrary, get_meme_library
import config


class TestMemeLibrary(unittest.TestCase):
    """MemeLibrary 测试类"""
    
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
        library = MemeLibrary()
        self.assertIsNotNone(library)
        self.assertIsInstance(library.memes, dict)
        self.assertIsInstance(library.usage_records, dict)
    
    def test_get_meme_library_singleton(self):
        """测试单例模式"""
        # 重置全局实例
        import core.meme_library as ml_module
        ml_module._meme_library = None
        
        lib1 = get_meme_library()
        lib2 = get_meme_library()
        self.assertIs(lib1, lib2)
        
        # 清理
        ml_module._meme_library = None
    
    def test_get_meme(self):
        """测试获取梗"""
        library = MemeLibrary()
        
        # 获取一个存在的类别
        result = library.get_meme("打脸梗")
        
        self.assertIsInstance(result, dict)
        self.assertIn("category", result)
        self.assertIn("meme", result)
        self.assertIn("freshness", result)
    
    def test_get_meme_with_chapter_num(self):
        """测试带章节号获取梗"""
        library = MemeLibrary()
        
        result = library.get_meme("升级梗", chapter_num=10)
        
        self.assertIsInstance(result, dict)
        self.assertIn("meme", result)
    
    def test_track_freshness(self):
        """测试追踪新鲜度"""
        library = MemeLibrary()
        
        meme = "测试梗"
        chapter_num = 5
        
        library.track_freshness(meme, chapter_num)
        
        # 验证使用记录已更新
        self.assertIn(meme, library.usage_records)
        self.assertEqual(library.usage_records[meme]["last_used_chapter"], chapter_num)
    
    def test_add_meme(self):
        """测试添加梗"""
        library = MemeLibrary()
        
        category = "新类别"
        new_meme = "新梗内容"
        
        result = library.add_meme(category, new_meme)
        
        self.assertTrue(result)
        self.assertIn(category, library.memes)
        self.assertIn(new_meme, library.memes[category])
    
    def test_add_meme_duplicate(self):
        """测试添加重复梗"""
        library = MemeLibrary()
        
        category = "打脸梗"
        existing_meme = library.memes[category][0] if library.memes[category] else "测试"
        
        # 添加已存在的梗
        result = library.add_meme(category, existing_meme)
        
        # 应该返回False
        self.assertFalse(result)
    
    def test_get_all_memes(self):
        """测试获取所有梗"""
        library = MemeLibrary()
        
        all_memes = library.get_all_memes()
        
        self.assertIsInstance(all_memes, dict)
        self.assertTrue(len(all_memes) > 0)
    
    def test_get_categories(self):
        """测试获取所有类别"""
        library = MemeLibrary()
        
        categories = library.get_categories()
        
        self.assertIsInstance(categories, list)
        self.assertTrue(len(categories) > 0)
    
    def test_suggest_combination(self):
        """测试梗组合建议"""
        library = MemeLibrary()
        
        categories = ["打脸梗", "升级梗"]
        result = library.suggest_combination(categories)
        
        self.assertIsInstance(result, dict)
        # 可能成功也可能失败，但应该返回字典
        self.assertIn("combination", result)


if __name__ == '__main__':
    unittest.main()
