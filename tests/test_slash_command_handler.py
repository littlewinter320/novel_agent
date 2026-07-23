"""
SlashCommandHandler 单元测试

测试斜杠命令系统的核心功能:
- 命令注册
- 命令处理（handle_command）
- 帮助信息
- 自定义命令
"""
import unittest
import os
import sys
import tempfile
import shutil

# 添加项目路径
test_dir = os.path.dirname(os.path.abspath(__file__))
novel_agent_dir = os.path.dirname(test_dir)
sys.path.insert(0, novel_agent_dir)

from core.slash_command_handler import SlashCommandHandler
import config


class TestSlashCommandHandler(unittest.TestCase):
    """SlashCommandHandler 测试类"""
    
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
        handler = SlashCommandHandler()
        self.assertIsNotNone(handler)
        self.assertIsInstance(handler.commands, dict)
        # 应该注册了默认命令
        self.assertIn("help", handler.commands)
        self.assertIn("status", handler.commands)
        self.assertIn("goal", handler.commands)
    
    def test_handle_help_command(self):
        """测试/help命令"""
        handler = SlashCommandHandler()
        
        result = handler.handle_command("/help")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["command"], "help")
        self.assertIsNotNone(result["result"])
    
    def test_handle_status_command(self):
        """测试/status命令"""
        handler = SlashCommandHandler()
        
        result = handler.handle_command("/status")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["command"], "status")
    
    def test_handle_goal_command(self):
        """测试/goal命令"""
        handler = SlashCommandHandler()
        
        result = handler.handle_command("/goal 写一部玄幻小说")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["command"], "goal")
    
    def test_handle_command_with_args(self):
        """测试带参数的命令处理"""
        handler = SlashCommandHandler()
        
        # 测试/help带参数
        result = handler.handle_command("/help goal")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["command"], "help")
    
    def test_handle_non_command(self):
        """测试非命令输入"""
        handler = SlashCommandHandler()
        
        # 非斜杠开头不是命令
        result = handler.handle_command("普通消息")
        
        self.assertFalse(result["success"])
        self.assertIsNone(result["command"])
    
    def test_handle_unknown_command(self):
        """测试未知命令"""
        handler = SlashCommandHandler()
        
        result = handler.handle_command("/unknown_command")
        
        self.assertFalse(result["success"])
        self.assertEqual(result["command"], "unknown_command")
    
    def test_register_custom_command(self):
        """测试注册自定义命令"""
        handler = SlashCommandHandler()
        
        # 注册自定义命令
        def custom_handler(args):
            return {"message": f"自定义命令: {args}"}
        
        handler.register_command("custom", custom_handler, "自定义命令描述")
        
        # 验证命令已注册
        self.assertIn("custom", handler.commands)
        
        # 执行自定义命令
        result = handler.handle_command("/custom 测试参数")
        self.assertTrue(result["success"])
        self.assertEqual(result["command"], "custom")
    
    def test_get_available_commands(self):
        """测试获取可用命令列表"""
        handler = SlashCommandHandler()
        
        commands = handler.get_available_commands()
        
        # get_available_commands返回的是列表，每个元素是包含name、description、usage的字典
        self.assertIsInstance(commands, list)
        self.assertTrue(len(commands) > 0)
        
        # 检查是否包含默认命令
        command_names = [cmd["name"] for cmd in commands]
        self.assertIn("help", command_names)
        self.assertIn("status", command_names)
        self.assertIn("goal", command_names)


if __name__ == '__main__':
    unittest.main()
