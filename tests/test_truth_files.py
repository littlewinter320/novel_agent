"""真相文件体系的单元测试"""
import unittest
import tempfile
import shutil
import os
import sys
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.truth_files import TruthFiles


class TestTruthFiles(unittest.TestCase):
    """TruthFiles 类的单元测试"""
    
    def setUp(self):
        """每个测试前的初始化"""
        # 创建临时测试目录
        self.test_dir = tempfile.mkdtemp()
        self.tf = TruthFiles(truth_dir=self.test_dir)
    
    def tearDown(self):
        """每个测试后的清理"""
        # 清理测试目录中的所有文件
        if os.path.exists(self.test_dir):
            for file in os.listdir(self.test_dir):
                file_path = os.path.join(self.test_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
    
    def test_load_all_creates_default_files(self):
        """测试 load_all 创建默认文件"""
        data = self.tf.load_all()
        
        # 验证7个文件都被加载
        self.assertEqual(len(data), 7)
        
        # 验证每个文件的默认结构
        self.assertIn("world_state", data)
        self.assertEqual(data["world_state"], {"rules": {}, "forces": {}, "resources": {}})
        
        self.assertIn("character_matrix", data)
        self.assertEqual(data["character_matrix"], {"characters": {}})
        
        self.assertIn("plot_progress", data)
        self.assertEqual(data["plot_progress"], {"events": [], "main_plot": {}, "sub_plots": {}})
        
        self.assertIn("foreshadow_hooks", data)
        self.assertEqual(data["foreshadow_hooks"], {"foreshadows": []})
        
        self.assertIn("resource_ledger", data)
        self.assertEqual(data["resource_ledger"], {"items": [], "transactions": []})
        
        self.assertIn("timeline", data)
        self.assertEqual(data["timeline"], {"events": []})
        
        self.assertIn("style_guide", data)
        self.assertEqual(data["style_guide"], {"tone": "", "forbidden_patterns": [], "pov": ""})
        
        # 验证文件确实被创建到磁盘
        for file_def in TruthFiles.TRUTH_FILE_DEFS.values():
            file_path = os.path.join(self.test_dir, file_def["filename"])
            self.assertTrue(os.path.exists(file_path), f"文件 {file_def['filename']} 应该存在")
    
    def test_load_all_loads_existing_files(self):
        """测试 load_all 加载已存在的文件"""
        # 先创建一个自定义文件
        custom_data = {"rules": {"gravity": "normal"}, "forces": {}, "resources": {}}
        file_path = os.path.join(self.test_dir, "world_state.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(custom_data, f)
        
        # 加载所有文件
        data = self.tf.load_all()
        
        # 验证自定义数据被加载
        self.assertEqual(data["world_state"]["rules"]["gravity"], "normal")
    
    def test_save_all(self):
        """测试 save_all 保存所有文件"""
        self.tf.load_all()
        
        # 修改一些数据
        self.tf.data["world_state"]["rules"]["magic"] = "limited"
        self.tf.data["character_matrix"]["characters"]["hero"] = {"name": "张三"}
        
        # 保存
        self.tf.save_all()
        
        # 验证文件内容
        with open(os.path.join(self.test_dir, "world_state.json"), 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data["rules"]["magic"], "limited")
        
        with open(os.path.join(self.test_dir, "character_matrix.json"), 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data["characters"]["hero"]["name"], "张三")
    
    def test_get_file(self):
        """测试 get_file 获取指定文件"""
        self.tf.load_all()
        
        world_state = self.tf.get_file("world_state")
        self.assertEqual(world_state, {"rules": {}, "forces": {}, "resources": {}})
        
        # 测试获取不存在的文件
        with self.assertRaises(ValueError):
            self.tf.get_file("nonexistent")
    
    def test_update_file(self):
        """测试 update_file 更新文件"""
        self.tf.load_all()
        
        new_data = {"rules": {"physics": "custom"}, "forces": {"faction1": 100}, "resources": {"gold": 500}}
        self.tf.update_file("world_state", new_data)
        
        # 验证内存中的数据
        self.assertEqual(self.tf.data["world_state"]["rules"]["physics"], "custom")
        
        # 验证磁盘上的数据
        with open(os.path.join(self.test_dir, "world_state.json"), 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data["rules"]["physics"], "custom")
        
        # 测试更新不存在的文件
        with self.assertRaises(ValueError):
            self.tf.update_file("nonexistent", {})
    
    def test_cross_validate_no_issues(self):
        """测试交叉验证 - 无问题时"""
        self.tf.load_all()
        issues = self.tf.cross_validate()
        self.assertEqual(len(issues), 0)
    
    def test_cross_validate_character_knowledge(self):
        """测试角色认知边界检查"""
        self.tf.load_all()
        
        # 设置一个未来事件
        self.tf.data["plot_progress"]["events"] = [
            {"id": "event1", "status": "future", "description": "未来事件"}
        ]
        
        # 设置角色知道这个未来事件
        self.tf.data["character_matrix"]["characters"]["hero"] = {
            "name": "张三",
            "knowledge": ["event1"]
        }
        
        issues = self.tf.cross_validate()
        self.assertTrue(any("知道了未来事件" in issue for issue in issues))
    
    def test_cross_validate_resource_flow(self):
        """测试物品流转检查"""
        self.tf.load_all()
        
        # 添加一个没有创建记录的物品
        self.tf.data["resource_ledger"]["items"] = [
            {"id": "sword1", "name": "宝剑"}
        ]
        
        issues = self.tf.cross_validate()
        self.assertTrue(any("没有创建记录" in issue for issue in issues))
        
        # 测试转移未创建的物品
        self.tf.data["resource_ledger"]["items"] = []
        self.tf.data["resource_ledger"]["transactions"] = [
            {"item_id": "sword2", "type": "transfer", "from": "A", "to": "B"}
        ]
        
        issues = self.tf.cross_validate()
        self.assertTrue(any("在转移前未创建" in issue for issue in issues))
    
    def test_cross_validate_timeline_consistency(self):
        """测试时间线一致性检查"""
        self.tf.load_all()
        
        # 设置时间线，其中事件顺序矛盾
        # event1 发生在时间5，但依赖于 event2（发生在时间10）
        # 这意味着 event1 依赖于后续事件，这是矛盾的
        self.tf.data["timeline"]["events"] = [
            {"id": "event1", "time": 5, "depends_on": ["event2"]},
            {"id": "event2", "time": 10, "depends_on": []}
        ]
        
        issues = self.tf.cross_validate()
        self.assertTrue(any("依赖于后续事件" in issue for issue in issues))
    
    def test_cross_validate_world_rules(self):
        """测试世界规则一致性检查"""
        self.tf.load_all()
        
        # 设置规则
        self.tf.data["world_state"]["rules"] = {
            "no_flying": "在这个世界中，人类不能飞行"
        }
        
        # 设置违反规则的事件
        self.tf.data["plot_progress"]["events"] = [
            {"id": "event1", "violates_rules": ["no_flying"]}
        ]
        
        issues = self.tf.cross_validate()
        self.assertTrue(any("违反了规则" in issue for issue in issues))
    
    def test_truth_dir_creation(self):
        """测试真相目录自动创建"""
        # 删除测试目录
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        
        # 创建新的 TruthFiles 实例，传递测试目录
        tf = TruthFiles(truth_dir=self.test_dir)
        
        # 验证目录被创建
        self.assertTrue(os.path.exists(self.test_dir))
        
        # 加载文件
        tf.load_all()
        
        # 验证文件被创建
        for file_def in TruthFiles.TRUTH_FILE_DEFS.values():
            file_path = os.path.join(self.test_dir, file_def["filename"])
            self.assertTrue(os.path.exists(file_path))


if __name__ == '__main__':
    unittest.main()
