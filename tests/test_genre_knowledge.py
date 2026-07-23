"""
GenreKnowledgeBase 单元测试
"""

import unittest
import os
import json
import tempfile
import shutil
import time
from unittest.mock import patch
from core.genre_knowledge import GenreKnowledgeBase, get_genre_knowledge_base


class TestGenreKnowledgeBase(unittest.TestCase):
    """测试 GenreKnowledgeBase 类"""
    
    def setUp(self):
        """测试前准备临时目录"""
        self.test_dir = tempfile.mkdtemp()
        self.genres_dir = os.path.join(self.test_dir, 'genres')
        os.makedirs(self.genres_dir)
        
        # 创建测试题材文件
        self.test_genre = {
            "name": "测试题材",
            "tags": ["测试", "男频"],
            "basic_writing": {
                "narrative_structure": "测试结构",
                "pacing_design": "测试节奏",
                "opening_patterns": ["测试开局"]
            },
            "plot_system": {
                "classic_plot_templates": ["测试剧情"],
                "common_conflicts": ["测试冲突"],
                "satisfaction_distribution": "测试爽点"
            },
            "character_templates": {
                "protagonist": {"traits": ["测试特质"]},
                "supporting": [],
                "antagonist": {"traits": ["测试反派"]}
            },
            "hot_memes": ["测试梗"],
            "taboos": ["测试禁忌"]
        }
        
        filepath = os.path.join(self.genres_dir, '测试题材.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.test_genre, f, ensure_ascii=False, indent=2)
    
    def tearDown(self):
        """测试后清理临时目录"""
        shutil.rmtree(self.test_dir)
    
    def test_init_loads_genres(self):
        """测试初始化时加载题材文件"""
        with patch('config.GENRES_DIR', self.genres_dir):
            kb = GenreKnowledgeBase()
            genres = kb.list_genres()
            self.assertIn('测试题材', genres)
    
    def test_get_genre(self):
        """测试获取指定题材"""
        with patch('config.GENRES_DIR', self.genres_dir):
            kb = GenreKnowledgeBase()
            genre = kb.get_genre('测试题材')
            
            self.assertIsNotNone(genre)
            self.assertEqual(genre['name'], '测试题材')
            self.assertIn('测试', genre['tags'])
    
    def test_get_nonexistent_genre(self):
        """测试获取不存在的题材"""
        with patch('config.GENRES_DIR', self.genres_dir):
            kb = GenreKnowledgeBase()
            genre = kb.get_genre('不存在的题材')
            self.assertIsNone(genre)
    
    def test_list_genres(self):
        """测试列出所有题材"""
        with patch('config.GENRES_DIR', self.genres_dir):
            kb = GenreKnowledgeBase()
            genres = kb.list_genres()
            
            self.assertIsInstance(genres, list)
            self.assertGreater(len(genres), 0)
            self.assertIn('测试题材', genres)
    
    def test_add_genre(self):
        """测试添加新题材"""
        with patch('config.GENRES_DIR', self.genres_dir):
            kb = GenreKnowledgeBase()
            
            new_genre = {
                "name": "新题材",
                "tags": ["新", "测试"],
                "basic_writing": {},
                "plot_system": {},
                "character_templates": {},
                "hot_memes": [],
                "taboos": []
            }
            
            result = kb.add_genre('新题材', new_genre)
            self.assertTrue(result)
            
            # 验证内存中已添加
            genres = kb.list_genres()
            self.assertIn('新题材', genres)
            
            # 验证文件已创建
            filepath = os.path.join(self.genres_dir, '新题材.json')
            self.assertTrue(os.path.exists(filepath))
    
    def test_add_duplicate_genre(self):
        """测试添加重复题材"""
        with patch('config.GENRES_DIR', self.genres_dir):
            kb = GenreKnowledgeBase()
            
            duplicate_genre = {
                "name": "测试题材",
                "tags": ["重复"]
            }
            
            result = kb.add_genre('测试题材', duplicate_genre)
            self.assertFalse(result)
    
    def test_update_genre(self):
        """测试更新题材"""
        with patch('config.GENRES_DIR', self.genres_dir):
            kb = GenreKnowledgeBase()
            
            updated_data = {
                "name": "测试题材",
                "tags": ["更新", "测试"],
                "basic_writing": {},
                "plot_system": {},
                "character_templates": {},
                "hot_memes": ["新梗"],
                "taboos": []
            }
            
            result = kb.update_genre('测试题材', updated_data)
            self.assertTrue(result)
            
            # 验证内存中已更新
            genre = kb.get_genre('测试题材')
            self.assertIn('更新', genre['tags'])
            self.assertIn('新梗', genre['hot_memes'])
    
    def test_update_nonexistent_genre(self):
        """测试更新不存在的题材"""
        with patch('config.GENRES_DIR', self.genres_dir):
            kb = GenreKnowledgeBase()
            
            result = kb.update_genre('不存在的题材', {})
            self.assertFalse(result)
    
    def test_search_by_tag(self):
        """测试按标签搜索"""
        with patch('config.GENRES_DIR', self.genres_dir):
            kb = GenreKnowledgeBase()
            
            # 添加另一个题材
            new_genre = {
                "name": "另一个题材",
                "tags": ["测试", "女频"],
                "basic_writing": {},
                "plot_system": {},
                "character_templates": {},
                "hot_memes": [],
                "taboos": []
            }
            kb.add_genre('另一个题材', new_genre)
            
            # 搜索包含"测试"标签的题材
            results = kb.search_by_tag('测试')
            self.assertGreater(len(results), 0)
            self.assertIn('测试题材', results)
            self.assertIn('另一个题材', results)
            
            # 搜索包含"男频"标签的题材
            results = kb.search_by_tag('男频')
            self.assertIn('测试题材', results)
            self.assertNotIn('另一个题材', results)
    
    def test_hot_reload_modified_file(self):
        """测试热更新修改的文件"""
        with patch('config.GENRES_DIR', self.genres_dir):
            kb = GenreKnowledgeBase()
            
            # 修改文件
            filepath = os.path.join(self.genres_dir, '测试题材.json')
            time.sleep(0.1)  # 确保修改时间不同
            
            modified_genre = self.test_genre.copy()
            modified_genre['hot_memes'] = ["新梗", "另一个梗"]
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(modified_genre, f, ensure_ascii=False, indent=2)
            
            # 触发热更新检查
            genre = kb.get_genre('测试题材')
            
            # 验证已更新
            self.assertIn('新梗', genre['hot_memes'])
            self.assertIn('另一个梗', genre['hot_memes'])
    
    def test_hot_reload_deleted_file(self):
        """测试热更新删除的文件"""
        with patch('config.GENRES_DIR', self.genres_dir):
            kb = GenreKnowledgeBase()
            
            # 删除文件
            filepath = os.path.join(self.genres_dir, '测试题材.json')
            os.remove(filepath)
            
            # 触发热更新检查
            genres = kb.list_genres()
            
            # 验证已移除
            self.assertNotIn('测试题材', genres)
    
    def test_reload(self):
        """测试手动重新加载"""
        with patch('config.GENRES_DIR', self.genres_dir):
            kb = GenreKnowledgeBase()
            
            # 添加新文件
            new_genre = {
                "name": "新题材",
                "tags": ["新"],
                "basic_writing": {},
                "plot_system": {},
                "character_templates": {},
                "hot_memes": [],
                "taboos": []
            }
            
            filepath = os.path.join(self.genres_dir, '新题材.json')
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(new_genre, f, ensure_ascii=False, indent=2)
            
            # 手动重新加载
            kb.reload()
            
            # 验证已加载
            genres = kb.list_genres()
            self.assertIn('新题材', genres)
    
    def test_get_genre_knowledge_base_singleton(self):
        """测试全局单例"""
        with patch('config.GENRES_DIR', self.genres_dir):
            kb1 = get_genre_knowledge_base()
            kb2 = get_genre_knowledge_base()
            
            self.assertIs(kb1, kb2)


class TestGenreDataStructure(unittest.TestCase):
    """测试题材数据结构"""
    
    def test_genre_file_structure(self):
        """测试题材文件结构完整性"""
        required_fields = [
            'name', 'tags', 'basic_writing', 'plot_system',
            'character_templates', 'hot_memes', 'taboos'
        ]
        
        # 检查所有题材文件
        from config import GENRES_DIR
        if not os.path.exists(GENRES_DIR):
            self.skipTest("GENRES_DIR 不存在")
        
        for filename in os.listdir(GENRES_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(GENRES_DIR, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for field in required_fields:
                    self.assertIn(field, data, 
                                f"题材文件 {filename} 缺少字段: {field}")


if __name__ == '__main__':
    unittest.main()
