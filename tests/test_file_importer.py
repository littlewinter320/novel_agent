"""文件导入与解析模块单元测试"""
import unittest
import os
import sys
import tempfile
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.file_importer import FileImporter


class TestFileImporter(unittest.TestCase):
    """FileImporter 测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.importer = FileImporter()
        # 创建临时测试文件
        self.test_dir = tempfile.mkdtemp()
        self.test_txt = os.path.join(self.test_dir, "test.txt")
        
        # 写入测试内容
        test_content = """
第一章 开始

李明走在街道上，心中想着今天的会议。突然，他看到了一个熟悉的身影。

"你怎么在这里？"李明问道。

王华转过身来，笑着说："我来找你啊。"

李明觉得有些意外，但还是很高兴见到老朋友。

第二章 意外

他们走进咖啡厅，开始交谈。王华告诉李明一个重要消息。

"我发现了那个秘密，"王华低声说，"关于那个传说中的宝藏。"

李明心中一震，这个秘密可能会改变他们的命运。
"""
        with open(self.test_txt, 'w', encoding='utf-8') as f:
            f.write(test_content)
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.test_txt):
            os.remove(self.test_txt)
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)
    
    def test_import_file_not_found(self):
        """测试文件不存在"""
        with self.assertRaises(FileNotFoundError):
            self.importer.import_file("nonexistent.txt")
    
    def test_import_unsupported_format(self):
        """测试不支持的文件格式"""
        # 创建一个不支持的文件
        test_file = os.path.join(self.test_dir, "test.xyz")
        with open(test_file, 'w') as f:
            f.write("test")
        
        with self.assertRaises(ValueError):
            self.importer.import_file(test_file)
        
        os.remove(test_file)
    
    def test_import_txt_file(self):
        """测试导入TXT文件"""
        result = self.importer.import_file(self.test_txt)
        
        # 检查返回结构
        self.assertIn("file_path", result)
        self.assertIn("metadata", result)
        self.assertIn("content", result)
        self.assertIn("characters", result)
        self.assertIn("events", result)
        self.assertIn("foreshadows", result)
        self.assertIn("style_fingerprint", result)
        
        # 检查内容不为空
        self.assertGreater(len(result["content"]), 0)
    
    def test_extract_metadata(self):
        """测试提取元信息"""
        with open(self.test_txt, 'r', encoding='utf-8') as f:
            content = f.read()
        
        metadata = self.importer.extract_metadata(self.test_txt, content)
        
        # 检查元信息字段
        self.assertIn("file_name", metadata)
        self.assertIn("file_type", metadata)
        self.assertIn("total_words", metadata)
        self.assertIn("chapter_count", metadata)
        
        # 检查章节数（应该有2章）
        self.assertGreaterEqual(metadata["chapter_count"], 2)
        
        # 检查字数统计
        self.assertGreater(metadata["total_words"], 0)
    
    def test_extract_characters(self):
        """测试提取人物"""
        with open(self.test_txt, 'r', encoding='utf-8') as f:
            content = f.read()
        
        characters = self.importer.extract_characters(content)
        
        # 应该提取到至少2个人物
        self.assertGreaterEqual(len(characters), 2)
        
        # 检查人物结构
        for char in characters:
            self.assertIn("name", char)
            self.assertIn("mention_count", char)
            self.assertIn("descriptions", char)
        
        # 应该包含"李明"和"王华"
        char_names = [c["name"] for c in characters]
        self.assertIn("李明", char_names)
        self.assertIn("王华", char_names)
    
    def test_extract_events(self):
        """测试提取事件"""
        with open(self.test_txt, 'r', encoding='utf-8') as f:
            content = f.read()
        
        events = self.importer.extract_events(content)
        
        # 应该提取到事件
        self.assertGreaterEqual(len(events), 1)
        
        # 检查事件结构
        for event_group in events:
            self.assertIn("chapter", event_group)
            self.assertIn("chapter_index", event_group)
            self.assertIn("key_events", event_group)
    
    def test_extract_foreshadows(self):
        """测试提取伏笔"""
        with open(self.test_txt, 'r', encoding='utf-8') as f:
            content = f.read()
        
        foreshadows = self.importer.extract_foreshadows(content)
        
        # 应该提取到伏笔（包含"秘密"、"传说"等关键词）
        self.assertGreaterEqual(len(foreshadows), 1)
        
        # 检查伏笔结构
        for foreshadow in foreshadows:
            self.assertIn("content", foreshadow)
            self.assertIn("keyword", foreshadow)
            self.assertIn("type", foreshadow)
    
    def test_analyze_style_fingerprint(self):
        """测试分析文笔指纹"""
        with open(self.test_txt, 'r', encoding='utf-8') as f:
            content = f.read()
        
        fingerprint = self.importer.analyze_style_fingerprint(content)
        
        # 检查文笔指纹字段
        self.assertIn("sentence_lengths", fingerprint)
        self.assertIn("dialogue_ratio", fingerprint)
        self.assertIn("psychology_ratio", fingerprint)
        self.assertIn("environment_ratio", fingerprint)
        self.assertIn("common_words", fingerprint)
        self.assertIn("narrative_perspective", fingerprint)
        
        # 检查句式长度分析
        sentence_lengths = fingerprint["sentence_lengths"]
        self.assertIn("avg", sentence_lengths)
        self.assertIn("min", sentence_lengths)
        self.assertIn("max", sentence_lengths)
        self.assertIn("distribution", sentence_lengths)
        
        # 检查比例值在合理范围
        self.assertGreaterEqual(fingerprint["dialogue_ratio"], 0)
        self.assertLessEqual(fingerprint["dialogue_ratio"], 1)
        
        self.assertGreaterEqual(fingerprint["psychology_ratio"], 0)
        self.assertLessEqual(fingerprint["psychology_ratio"], 1)
        
        # 检查叙事视角
        self.assertIn(fingerprint["narrative_perspective"], ["first_person", "third_person"])
    
    def test_count_chapters(self):
        """测试章节计数"""
        content = """
第一章 开始
内容...

第二章 发展
内容...

第三章 高潮
内容...
"""
        count = self.importer._count_chapters(content)
        self.assertEqual(count, 3)
    
    def test_analyze_sentence_lengths(self):
        """测试句式长度分析"""
        content = "短句。这是一个中等长度的句子。这是一个非常非常长的句子，包含了很多很多的文字，用来测试长句的检测功能。"
        
        result = self.importer._analyze_sentence_lengths(content)
        
        self.assertIn("avg", result)
        self.assertIn("min", result)
        self.assertIn("max", result)
        self.assertIn("distribution", result)
        self.assertIn("short", result["distribution"])
        self.assertIn("medium", result["distribution"])
        self.assertIn("long", result["distribution"])
    
    def test_analyze_dialogue_ratio(self):
        """测试对话占比分析"""
        content = '他说："你好。"她回答："再见。"这是叙述部分。'
        
        ratio = self.importer._analyze_dialogue_ratio(content)
        
        self.assertGreaterEqual(ratio, 0)
        self.assertLessEqual(ratio, 1)
    
    def test_detect_narrative_perspective(self):
        """测试叙事视角检测"""
        # 第一人称
        first_person = "我走在街上，我觉得很开心，我想回家。"
        perspective = self.importer._detect_narrative_perspective(first_person)
        self.assertEqual(perspective, "first_person")
        
        # 第三人称
        third_person = "李明走在街上，李明觉得很开心，李明想回家。"
        perspective = self.importer._detect_narrative_perspective(third_person)
        self.assertEqual(perspective, "third_person")
    
    def test_is_common_word(self):
        """测试常见词过滤"""
        # 常见词应该返回True
        self.assertTrue(self.importer._is_common_word("一个"))
        self.assertTrue(self.importer._is_common_word("知道"))
        
        # 人名应该返回False
        self.assertFalse(self.importer._is_common_word("李明"))
        self.assertFalse(self.importer._is_common_word("王华"))


class TestFileImporterIntegration(unittest.TestCase):
    """FileImporter 集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.importer = FileImporter()
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_full_import_workflow(self):
        """测试完整导入流程"""
        # 创建测试文件
        test_file = os.path.join(self.test_dir, "novel.txt")
        content = """
第一章 相遇

李明在咖啡厅遇到了王华。

"好久不见！"李明说。

"是啊，"王华回答，"听说你最近在做项目？"

李明点点头，突然想到了那个秘密计划。他决定告诉王华真相。
"""
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 导入文件
        result = self.importer.import_file(test_file)
        
        # 验证所有信息都被提取
        self.assertGreater(len(result["characters"]), 0)
        self.assertGreater(len(result["events"]), 0)
        self.assertIsNotNone(result["style_fingerprint"])


if __name__ == '__main__':
    unittest.main()
