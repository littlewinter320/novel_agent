"""
StructureTemplates 单元测试

测试结构模板库的核心功能:
- 模板获取
- 节奏平衡检查
- 结尾钩子获取
- 模板添加
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
from core.structure_templates import StructureTemplates, get_structure_templates
import config


class TestStructureTemplates(unittest.TestCase):
    """StructureTemplates 测试类"""
    
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
        templates = StructureTemplates()
        self.assertIsNotNone(templates)
        self.assertIsInstance(templates.templates, dict)
        # 应该有默认模板
        self.assertTrue(len(templates.templates) > 0)
    
    def test_get_structure_templates_singleton(self):
        """测试单例模式"""
        import core.structure_templates as st_module
        st_module._structure_templates = None
        
        t1 = get_structure_templates()
        t2 = get_structure_templates()
        self.assertIs(t1, t2)
        
        # 清理
        st_module._structure_templates = None
    
    def test_get_template_by_type(self):
        """测试按类型获取模板"""
        templates = StructureTemplates()
        
        # 获取指定类型的模板
        template = templates.get_template("正叙型")
        
        self.assertIsInstance(template, dict)
        self.assertIn("template_type", template)
        self.assertIn("template", template)
        self.assertIn("structure", template)
        self.assertIn("pacing", template)
        self.assertEqual(template["template_type"], "正叙型")
    
    def test_get_template_auto_select(self):
        """测试自动选择模板"""
        templates = StructureTemplates()
        
        # 不指定类型，自动选择
        template = templates.get_template()
        
        self.assertIsInstance(template, dict)
        self.assertIn("template_type", template)
        self.assertIn("structure", template)
    
    def test_add_template(self):
        """测试添加模板"""
        templates = StructureTemplates()
        
        new_template = {
            "description": "自定义模板描述",
            "structure": ["开头", "发展", "高潮", "结尾"],
            "pacing": "快节奏",
            "suitable_for": ["测试"]
        }
        
        success = templates.add_template("custom_template", new_template)
        self.assertTrue(success)
        
        # 验证模板已添加
        retrieved = templates.get_template("custom_template")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["template_type"], "custom_template")
        self.assertEqual(retrieved["template"]["description"], "自定义模板描述")
    
    def test_add_duplicate_template(self):
        """测试添加重复模板"""
        templates = StructureTemplates()
        
        # 添加已存在的模板类型应该失败
        success = templates.add_template("正叙型", {"description": "重复"})
        self.assertFalse(success)
    
    def test_check_rhythm_balance(self):
        """测试节奏平衡检查"""
        templates = StructureTemplates()
        
        # 无历史数据时的检查
        result = templates.check_rhythm_balance()
        
        self.assertIsInstance(result, dict)
        self.assertIn("is_balanced", result)
    
    def test_check_rhythm_balance_with_chapters(self):
        """测试带章节数据的节奏平衡检查"""
        templates = StructureTemplates()
        
        recent_chapters = [
            {"pacing": "快节奏"},
            {"pacing": "快节奏"},
            {"pacing": "快节奏"}
        ]
        
        result = templates.check_rhythm_balance(recent_chapters)
        
        self.assertIsInstance(result, dict)
        self.assertIn("is_balanced", result)
        # 连续3章快节奏应该不平衡
        self.assertFalse(result["is_balanced"])
    
    def test_get_ending_hook_type(self):
        """测试获取结尾钩子"""
        templates = StructureTemplates()
        
        # 获取指定类型的结尾钩子
        result = templates.get_ending_hook_type("悬念型")
        
        self.assertIsInstance(result, dict)
        self.assertIn("hook_type", result)
        self.assertIn("hook", result)
        self.assertIn("alternatives", result)
        self.assertEqual(result["hook_type"], "悬念型")
    
    def test_get_ending_hook_auto_select(self):
        """测试自动选择结尾钩子"""
        templates = StructureTemplates()
        
        # 不指定类型，自动选择
        result = templates.get_ending_hook_type()
        
        self.assertIsInstance(result, dict)
        self.assertIn("hook_type", result)
        self.assertIn("hook", result)
    
    def test_get_all_templates(self):
        """测试获取所有模板"""
        templates = StructureTemplates()
        
        all_templates = templates.get_all_templates()
        
        self.assertIsInstance(all_templates, dict)
        self.assertTrue(len(all_templates) >= 6)  # 至少有6个默认模板
    
    def test_get_template_types(self):
        """测试获取所有模板类型"""
        templates = StructureTemplates()
        
        types = templates.get_template_types()
        
        self.assertIsInstance(types, list)
        self.assertIn("正叙型", types)
        self.assertIn("倒叙型", types)
        self.assertIn("战斗型", types)


if __name__ == '__main__':
    unittest.main()
