"""Prompt模板加载器单元测试"""
import unittest
import tempfile
import shutil
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.prompt_loader import PromptLoader


class TestPromptLoader(unittest.TestCase):
    """Prompt加载器测试"""
    
    def setUp(self):
        """测试前准备：使用临时目录"""
        self.test_dir = tempfile.mkdtemp()
        # 修改 config 中的路径
        import config
        config.TEMPLATES_DIR = self.test_dir
        self.loader = PromptLoader()
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_load_template_exists(self):
        """测试加载存在的模板"""
        # 创建测试模板
        template_file = os.path.join(self.test_dir, "test_prompt.md")
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write("# 测试模板\n\n参数1: {param1}\n参数2: {param2}")
        
        template = self.loader.load_template("test_prompt")
        
        self.assertIsNotNone(template)
        self.assertIn("测试模板", template)
        self.assertIn("{param1}", template)
    
    def test_load_template_not_exists(self):
        """测试加载不存在的模板"""
        template = self.loader.load_template("nonexistent_template")
        self.assertIsNone(template)
    
    def test_fill_template_basic(self):
        """测试填充模板基本功能"""
        # 创建测试模板
        template_file = os.path.join(self.test_dir, "test_prompt.md")
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write("你好，{name}！\n你的角色是{role}。")
        
        params = {
            "name": "张三",
            "role": "主角"
        }
        
        filled = self.loader.fill_template("test_prompt", params)
        
        self.assertIsNotNone(filled)
        self.assertIn("张三", filled)
        self.assertIn("主角", filled)
        self.assertNotIn("{name}", filled)
        self.assertNotIn("{role}", filled)
    
    def test_fill_template_with_dict(self):
        """测试填充字典类型参数"""
        template_file = os.path.join(self.test_dir, "test_prompt.md")
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write("配置信息：{config}")
        
        params = {
            "config": {"key1": "value1", "key2": "value2"}
        }
        
        filled = self.loader.fill_template("test_prompt", params)
        
        self.assertIsNotNone(filled)
        self.assertIn("key1", filled)
        self.assertIn("value1", filled)
    
    def test_fill_template_with_list(self):
        """测试填充列表类型参数"""
        template_file = os.path.join(self.test_dir, "test_prompt.md")
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write("角色列表：{characters}")
        
        params = {
            "characters": ["张三", "李四", "王五"]
        }
        
        filled = self.loader.fill_template("test_prompt", params)
        
        self.assertIsNotNone(filled)
        self.assertIn("张三", filled)
        self.assertIn("李四", filled)
        self.assertIn("王五", filled)
    
    def test_fill_template_not_exists(self):
        """测试填充不存在的模板"""
        params = {"param1": "value1"}
        filled = self.loader.fill_template("nonexistent", params)
        self.assertIsNone(filled)
    
    def test_get_available_templates(self):
        """测试获取可用模板列表"""
        # 创建多个测试模板
        for name in ["template_a", "template_b", "template_c"]:
            template_file = os.path.join(self.test_dir, f"{name}.md")
            with open(template_file, 'w') as f:
                f.write(f"# {name}")
        
        templates = self.loader.get_available_templates()
        
        self.assertEqual(len(templates), 3)
        self.assertIn("template_a", templates)
        self.assertIn("template_b", templates)
        self.assertIn("template_c", templates)
    
    def test_get_available_templates_empty(self):
        """测试空目录获取模板列表"""
        templates = self.loader.get_available_templates()
        self.assertEqual(len(templates), 0)
    
    def test_get_template_params(self):
        """测试获取模板参数列表"""
        template_file = os.path.join(self.test_dir, "test_prompt.md")
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write("{param1} {param2} {param3} {param1}")  # param1重复
        
        params = self.loader.get_template_params("test_prompt")
        
        self.assertEqual(len(params), 3)  # 应该去重
        self.assertIn("param1", params)
        self.assertIn("param2", params)
        self.assertIn("param3", params)
    
    def test_get_template_params_not_exists(self):
        """测试获取不存在模板的参数"""
        params = self.loader.get_template_params("nonexistent")
        self.assertEqual(len(params), 0)
    
    def test_fill_template_partial_params(self):
        """测试部分参数填充"""
        template_file = os.path.join(self.test_dir, "test_prompt.md")
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write("{param1} {param2} {param3}")
        
        # 只提供部分参数
        params = {"param1": "value1"}
        
        filled = self.loader.fill_template("test_prompt", params)
        
        self.assertIsNotNone(filled)
        self.assertIn("value1", filled)
        self.assertIn("{param2}", filled)  # 未填充的参数保留
        self.assertIn("{param3}", filled)
    
    def test_fill_template_chinese_content(self):
        """测试中文内容填充"""
        template_file = os.path.join(self.test_dir, "test_prompt.md")
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write("你是一个{genre}小说作家，请创作一个关于{theme}的故事。")
        
        params = {
            "genre": "玄幻",
            "theme": "修仙"
        }
        
        filled = self.loader.fill_template("test_prompt", params)
        
        self.assertIsNotNone(filled)
        self.assertIn("玄幻", filled)
        self.assertIn("修仙", filled)


if __name__ == '__main__':
    unittest.main()
