"""SessionState 单元测试"""
import unittest
import os
import sys
import json
import tempfile
import shutil

# 添加项目路径
test_dir = os.path.dirname(os.path.abspath(__file__))
novel_agent_dir = os.path.dirname(test_dir)
sys.path.insert(0, novel_agent_dir)

from core.session_state import SessionState
import config


class TestSessionState(unittest.TestCase):
    """SessionState 测试类"""
    
    def setUp(self):
        """测试前准备：使用临时目录"""
        # 创建临时目录
        self.test_dir = tempfile.mkdtemp()
        
        # 保存原始配置
        self.original_data_dir = config.DATA_DIR
        self.original_session_state_file = config.SESSION_STATE_FILE
        
        # 修改配置为临时目录
        config.DATA_DIR = self.test_dir
        config.SESSION_STATE_FILE = os.path.join(self.test_dir, "session_state.json")
    
    def tearDown(self):
        """测试后清理：删除临时目录"""
        # 恢复原始配置
        config.DATA_DIR = self.original_data_dir
        config.SESSION_STATE_FILE = self.original_session_state_file
        
        # 删除临时目录
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_initial_state(self):
        """测试初始状态"""
        state = SessionState()
        self.assertEqual(state.current_step, 1)
        self.assertEqual(state.version_chain, [])
        self.assertEqual(state.user_constraints, [])
        self.assertEqual(state.current_progress, {})
        self.assertIsNone(state.active_novel_id)
    
    def test_update_step(self):
        """测试更新步骤"""
        state = SessionState()
        
        # 测试正常更新
        state.update_step(3)
        self.assertEqual(state.current_step, 3)
        
        state.update_step(7)
        self.assertEqual(state.current_step, 7)
        
        # 测试边界值
        state.update_step(1)
        self.assertEqual(state.current_step, 1)
        
        # 测试无效值
        with self.assertRaises(ValueError):
            state.update_step(0)
        
        with self.assertRaises(ValueError):
            state.update_step(8)
    
    def test_add_constraint(self):
        """测试添加约束"""
        state = SessionState()
        
        # 测试添加约束
        state.add_constraint("主角必须是女性")
        self.assertEqual(len(state.user_constraints), 1)
        self.assertEqual(state.user_constraints[0], "主角必须是女性")
        
        # 测试添加多个约束
        state.add_constraint("故事背景在现代")
        self.assertEqual(len(state.user_constraints), 2)
        self.assertEqual(state.user_constraints[1], "故事背景在现代")
        
        # 测试空字符串不添加
        state.add_constraint("")
        state.add_constraint("   ")
        self.assertEqual(len(state.user_constraints), 2)
    
    def test_get_progress(self):
        """测试获取进度"""
        state = SessionState()
        
        # 测试空进度
        progress = state.get_progress()
        self.assertEqual(progress, {})
        
        # 测试设置进度后获取
        state.current_progress = {
            "chapter": 5,
            "status": "writing",
            "word_count": 3000
        }
        progress = state.get_progress()
        self.assertEqual(progress["chapter"], 5)
        self.assertEqual(progress["status"], "writing")
        self.assertEqual(progress["word_count"], 3000)
        
        # 测试返回的是副本
        progress["chapter"] = 10
        self.assertEqual(state.current_progress["chapter"], 5)
    
    def test_save_and_load(self):
        """测试保存和加载功能"""
        # 创建并设置状态
        state1 = SessionState()
        state1.current_step = 4
        state1.version_chain = ["v1", "v2", "v2.1"]
        state1.user_constraints = ["主角必须是女性", "故事背景在现代"]
        state1.current_progress = {"chapter": 5, "status": "writing"}
        state1.active_novel_id = "novel_123"
        
        # 保存状态
        state1.save()
        
        # 验证文件存在
        self.assertTrue(os.path.exists(config.SESSION_STATE_FILE))
        
        # 加载状态到新对象
        state2 = SessionState()
        state2.load()
        
        # 验证所有属性都正确恢复
        self.assertEqual(state2.current_step, 4)
        self.assertEqual(state2.version_chain, ["v1", "v2", "v2.1"])
        self.assertEqual(state2.user_constraints, ["主角必须是女性", "故事背景在现代"])
        self.assertEqual(state2.current_progress, {"chapter": 5, "status": "writing"})
        self.assertEqual(state2.active_novel_id, "novel_123")
    
    def test_load_nonexistent_file(self):
        """测试加载不存在的文件"""
        state = SessionState()
        
        # 设置一些初始值
        state.current_step = 3
        state.user_constraints = ["测试约束"]
        
        # 加载不存在的文件（应该保持默认值）
        state.load()
        
        # 验证值没有被改变
        self.assertEqual(state.current_step, 3)
        self.assertEqual(state.user_constraints, ["测试约束"])
    
    def test_file_persistence(self):
        """测试文件持久化"""
        # 创建并保存状态
        state1 = SessionState()
        state1.current_step = 5
        state1.version_chain = ["v1", "v2"]
        state1.add_constraint("约束1")
        state1.add_constraint("约束2")
        state1.current_progress = {"task": "outline", "progress": 80}
        state1.active_novel_id = "test_novel"
        state1.save()
        
        # 直接读取文件验证内容
        with open(config.SESSION_STATE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertEqual(data["current_step"], 5)
        self.assertEqual(data["version_chain"], ["v1", "v2"])
        self.assertEqual(data["user_constraints"], ["约束1", "约束2"])
        self.assertEqual(data["current_progress"], {"task": "outline", "progress": 80})
        self.assertEqual(data["active_novel_id"], "test_novel")
    
    def test_to_dict(self):
        """测试 to_dict 方法"""
        state = SessionState()
        state.current_step = 3
        state.version_chain = ["v1"]
        state.user_constraints = ["约束1"]
        state.current_progress = {"key": "value"}
        state.active_novel_id = "novel_456"
        
        result = state.to_dict()
        
        self.assertEqual(result["current_step"], 3)
        self.assertEqual(result["version_chain"], ["v1"])
        self.assertEqual(result["user_constraints"], ["约束1"])
        self.assertEqual(result["current_progress"], {"key": "value"})
        self.assertEqual(result["active_novel_id"], "novel_456")
        
        # 验证返回的是副本
        result["current_step"] = 10
        self.assertEqual(state.current_step, 3)


if __name__ == '__main__':
    unittest.main()
