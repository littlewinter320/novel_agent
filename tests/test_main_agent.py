"""Main Agent 单元测试"""
import unittest
import sys
import os
import tempfile
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from core.main_agent import MainAgent, Intent


class TestMainAgent(unittest.TestCase):
    """MainAgent 测试类"""
    
    def setUp(self):
        """测试前准备 - 使用临时文件隔离测试"""
        self._orig_session_file = config.SESSION_STATE_FILE
        self._tmp_dir = tempfile.mkdtemp()
        config.SESSION_STATE_FILE = os.path.join(self._tmp_dir, "test_session.json")
        # 确保每个测试都从干净状态开始
        if os.path.exists(config.SESSION_STATE_FILE):
            os.remove(config.SESSION_STATE_FILE)
        self.agent = MainAgent()
    
    def tearDown(self):
        """测试后清理"""
        config.SESSION_STATE_FILE = self._orig_session_file
        if os.path.exists(self._tmp_dir):
            import shutil
            shutil.rmtree(self._tmp_dir, ignore_errors=True)
    
    def test_intent_identification_keywords(self):
        """测试关键词意图识别"""
        # 测试分析意图
        self.assertEqual(
            self.agent.identify_intent("分析爆火写法"),
            Intent.ANALYZE_TRENDS
        )
        self.assertEqual(
            self.agent.identify_intent("调研热门小说"),
            Intent.ANALYZE_TRENDS
        )
        
        # 测试规划意图
        self.assertEqual(
            self.agent.identify_intent("规划大纲"),
            Intent.PLAN_OUTLINE
        )
        self.assertEqual(
            self.agent.identify_intent("设计篇章结构"),
            Intent.PLAN_OUTLINE
        )
        
        # 测试生成意图
        self.assertEqual(
            self.agent.identify_intent("生成第1章"),
            Intent.GENERATE_CHAPTER
        )
        self.assertEqual(
            self.agent.identify_intent("写正文内容"),
            Intent.GENERATE_CHAPTER
        )
        
        # 测试导入意图
        self.assertEqual(
            self.agent.identify_intent("导入文件"),
            Intent.IMPORT_FILE
        )
        self.assertEqual(
            self.agent.identify_intent("上传docx"),
            Intent.IMPORT_FILE
        )
    
    def test_register_subagent(self):
        """测试注册SubAgent"""
        def mock_handler(input_text, context):
            return {"success": True, "message": "测试成功"}
        
        self.agent.register_subagent("test_agent", mock_handler)
        self.assertIn("test_agent", self.agent.subagents)
    
    def test_route_to_subagent(self):
        """测试路由到SubAgent"""
        # 注册测试处理器
        def mock_handler(input_text, context):
            return {
                "success": True,
                "message": f"处理: {input_text}",
                "intent": context.get("intent")
            }
        
        self.agent.register_subagent("scout", mock_handler)
        
        # 测试路由
        result = self.agent.route_to_subagent(Intent.ANALYZE_TRENDS, "分析爆火写法")
        self.assertTrue(result["success"])
        self.assertEqual(result["subagent"], "scout")
    
    def test_memory_points_update(self):
        """测试记忆点更新"""
        # 直接测试记忆点更新方法
        self.agent._update_memory_points("必须写爽文风格", {"success": True})
        self.assertEqual(len(self.agent.memory_points["user_constraints"]), 1)
        self.assertIn("必须写爽文风格", self.agent.memory_points["user_constraints"])
        
        # 测试修改记忆
        self.agent._update_memory_points("把主角改成女性", {"success": True})
        self.assertEqual(len(self.agent.memory_points["user_modifications"]), 1)
    
    def test_flow_control(self):
        """测试流程控制"""
        # 初始步骤为1
        self.assertEqual(self.agent.session_state.current_step, 1)
        
        # 步骤1应该允许分析意图
        can_proceed, _ = self.agent._check_flow_control(Intent.ANALYZE_TRENDS)
        self.assertTrue(can_proceed)
        
        # 步骤1应该阻止生成章节（跳步）
        can_proceed, reason = self.agent._check_flow_control(Intent.GENERATE_CHAPTER)
        self.assertFalse(can_proceed)
        self.assertIn("步骤", reason)
    
    def test_work_progress_update(self):
        """测试工作进度更新"""
        # 模拟分析完成
        self.agent._update_work_progress(Intent.ANALYZE_TRENDS, {"success": True})
        self.assertTrue(self.agent.memory_points["work_progress"]["trends_analyzed"])
        
        # 模拟规划完成
        self.agent._update_work_progress(Intent.PLAN_OUTLINE, {"success": True})
        self.assertTrue(self.agent.memory_points["work_progress"]["outline_planned"])
        self.assertEqual(self.agent.session_state.current_step, 2)
        
        # 模拟生成章节
        self.agent._update_work_progress(Intent.GENERATE_CHAPTER, {"success": True})
        self.assertEqual(self.agent.memory_points["work_progress"]["chapters_generated"], 1)
        self.assertEqual(self.agent.session_state.current_step, 3)
    
    def test_conversation_history(self):
        """测试对话历史"""
        # 模拟对话
        self.agent.receive_input("你好")
        self.agent.receive_input("分析爆火写法")
        
        # 检查历史（每次receive_input会添加user和assistant两条记录）
        self.assertGreaterEqual(len(self.agent.conversation_history), 2)
        # 第一条应该是用户输入
        self.assertEqual(self.agent.conversation_history[0]["role"], "user")
        self.assertEqual(self.agent.conversation_history[0]["content"], "你好")
    
    def test_get_status(self):
        """测试获取状态"""
        status = self.agent.get_status()
        
        self.assertIn("current_step", status)
        self.assertIn("registered_subagents", status)
        self.assertIn("conversation_turns", status)
        self.assertIn("memory_points", status)
    
    def test_reset_session(self):
        """测试重置会话"""
        # 添加一些数据
        self.agent.receive_input("测试输入")
        self.agent.add_user_constraint("测试约束")
        
        # 重置
        self.agent.reset_session()
        
        # 检查是否清空
        self.assertEqual(len(self.agent.conversation_history), 0)
        self.assertEqual(len(self.agent.memory_points["user_constraints"]), 0)
        self.assertEqual(self.agent.session_state.current_step, 1)


class TestIntentEnum(unittest.TestCase):
    """Intent枚举测试"""
    
    def test_intent_values(self):
        """测试意图值"""
        self.assertEqual(Intent.ANALYZE_TRENDS.value, "analyze_trends")
        self.assertEqual(Intent.PLAN_OUTLINE.value, "plan_outline")
        self.assertEqual(Intent.GENERATE_CHAPTER.value, "generate_chapter")
        self.assertEqual(Intent.IMPORT_FILE.value, "import_file")
        self.assertEqual(Intent.QUERY_KNOWLEDGE.value, "query_knowledge")
        self.assertEqual(Intent.VERSION_MANAGE.value, "version_manage")
        self.assertEqual(Intent.UNKNOWN.value, "unknown")


if __name__ == '__main__':
    unittest.main()
