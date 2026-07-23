"""
斜杠命令系统(SlashCommandHandler)

核心职责:
- 处理斜杠命令（如/goal、/help等）
- 集成各种技能（frontend-skill、complex-work-planner等）
- 提供命令路由和参数解析

工作流程:
接收命令 → 解析命令 → 路由到处理器 → 执行命令 → 返回结果

设计思路:
- 采用"命令注册"模式，支持动态添加命令
- 每个命令有独立的处理函数
- 支持命令参数解析
- 提供命令帮助信息

输出格式:
{
    "command": 命令名称,
    "success": bool,
    "result": 执行结果,
    "message": 返回消息
}
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class SlashCommandHandler:
    """
    斜杠命令处理器类
    
    核心功能:
    1. 命令注册：注册新的斜杠命令
    2. 命令解析：解析用户输入的命令
    3. 命令路由：将命令路由到对应的处理器
    4. 命令执行：执行命令并返回结果
    5. 帮助信息：提供命令帮助
    
    使用场景:
    - 用户输入/goal查看目标
    - 用户输入/help获取帮助
    - 用户输入各种技能命令
    
    使用流程:
    1. 初始化时注册默认命令
    2. 调用handle_command(user_input)处理命令
    3. 内部自动解析、路由、执行
    4. 返回执行结果
    """
    
    def __init__(self):
        """
        初始化斜杠命令处理器
        
        初始化流程:
        1. 创建命令注册表
        2. 注册默认命令
        """
        self.commands = {}
        self._register_default_commands()
    
    def _register_default_commands(self):
        """
        注册默认命令
        """
        # /goal命令 - 查看目标
        self.register_command(
            name="goal",
            handler=self._handle_goal,
            description="查看系统目标和任务",
            usage="/goal [目标编号]"
        )
        
        # /help命令 - 获取帮助
        self.register_command(
            name="help",
            handler=self._handle_help,
            description="获取命令帮助",
            usage="/help [命令名称]"
        )
        
        # /status命令 - 查看状态
        self.register_command(
            name="status",
            handler=self._handle_status,
            description="查看系统状态",
            usage="/status"
        )
        
        # /frontend命令 - 前端技能
        self.register_command(
            name="frontend",
            handler=self._handle_frontend,
            description="调用前端技能",
            usage="/frontend [参数]"
        )
        
        # /planner命令 - 工作规划器
        self.register_command(
            name="planner",
            handler=self._handle_planner,
            description="调用复杂工作规划器",
            usage="/planner [任务描述]"
        )
        
        # /cache命令 - 缓存管理
        self.register_command(
            name="cache",
            handler=self._handle_cache,
            description="管理LLM缓存",
            usage="/cache [stats|clear|report]"
        )
        
        # /dialogue命令 - 对话数据库
        self.register_command(
            name="dialogue",
            handler=self._handle_dialogue,
            description="管理对话数据库",
            usage="/dialogue [analyze|report|clear]"
        )
    
    def register_command(self, name: str, handler: Callable, 
                        description: str = "", usage: str = ""):
        """
        注册新命令
        
        Args:
            name: 命令名称（不含斜杠）
            handler: 命令处理函数
            description: 命令描述
            usage: 使用方式
        """
        self.commands[name] = {
            "handler": handler,
            "description": description,
            "usage": usage,
            "registered_at": datetime.now().isoformat()
        }
    
    def handle_command(self, user_input: str) -> Dict[str, Any]:
        """
        处理用户输入的命令
        
        实现逻辑:
        1. 检查是否以斜杠开头
        2. 解析命令名称和参数
        3. 查找命令处理器
        4. 执行命令
        5. 返回结果
        
        Args:
            user_input: 用户输入
        
        Returns:
            命令执行结果字典
        """
        # 检查是否以斜杠开头
        if not user_input.startswith('/'):
            return {
                "command": None,
                "success": False,
                "result": None,
                "message": "不是有效的斜杠命令"
            }
        
        # 解析命令
        parts = user_input[1:].split(maxsplit=1)
        command_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # 查找命令
        if command_name not in self.commands:
            return {
                "command": command_name,
                "success": False,
                "result": None,
                "message": f"未知命令: /{command_name}。输入 /help 查看可用命令。"
            }
        
        # 执行命令
        try:
            command_info = self.commands[command_name]
            handler = command_info["handler"]
            result = handler(args)
            
            return {
                "command": command_name,
                "success": True,
                "result": result,
                "message": "命令执行成功"
            }
        except Exception as e:
            return {
                "command": command_name,
                "success": False,
                "result": None,
                "message": f"命令执行失败: {e}"
            }
    
    def _handle_goal(self, args: str) -> Dict[str, Any]:
        """
        处理/goal命令
        
        Args:
            args: 命令参数
        
        Returns:
            执行结果
        """
        # 读取规范文档中的目标
        spec_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            ".trae", "specs", "novel-agent-3goals", "spec.md"
        )
        
        if not os.path.exists(spec_file):
            return {
                "goals": [],
                "message": "规范文档不存在"
            }
        
        try:
            with open(spec_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 简单解析目标（实际应该更复杂）
            goals = []
            if "目标1" in content:
                goals.append({"id": 1, "name": "搭建系统骨架与数据层", "status": "已完成"})
            if "目标2" in content:
                goals.append({"id": 2, "name": "实现内容生成智能核心", "status": "已完成"})
            if "目标3" in content:
                goals.append({"id": 3, "name": "构建质量保障与迭代闭环", "status": "待实现"})
            
            return {
                "goals": goals,
                "message": f"共{len(goals)}个目标"
            }
        except Exception as e:
            return {
                "goals": [],
                "message": f"读取目标失败: {e}"
            }
    
    def _handle_help(self, args: str) -> Dict[str, Any]:
        """
        处理/help命令
        
        Args:
            args: 命令参数（可选的命令名称）
        
        Returns:
            执行结果
        """
        if args:
            # 显示特定命令的帮助
            command_name = args.strip().lower()
            if command_name in self.commands:
                cmd = self.commands[command_name]
                return {
                    "command": command_name,
                    "description": cmd["description"],
                    "usage": cmd["usage"],
                    "message": f"/{command_name} - {cmd['description']}"
                }
            else:
                return {
                    "command": command_name,
                    "message": f"未知命令: {command_name}"
                }
        else:
            # 显示所有命令的帮助
            commands_list = []
            for name, cmd in self.commands.items():
                commands_list.append({
                    "name": name,
                    "description": cmd["description"],
                    "usage": cmd["usage"]
                })
            
            return {
                "commands": commands_list,
                "message": f"共{len(commands_list)}个可用命令"
            }
    
    def _handle_status(self, args: str) -> Dict[str, Any]:
        """
        处理/status命令
        
        Args:
            args: 命令参数
        
        Returns:
            执行结果
        """
        from core.session_state import SessionState
        
        session_state = SessionState()
        session_state.load()
        
        return {
            "current_step": session_state.current_step,
            "active_novel_id": session_state.active_novel_id,
            "version_count": len(session_state.version_chain),
            "constraint_count": len(session_state.user_constraints),
            "message": "系统状态正常"
        }
    
    def _handle_frontend(self, args: str) -> Dict[str, Any]:
        """
        处理/frontend命令（前端技能）
        
        Args:
            args: 命令参数
        
        Returns:
            执行结果
        """
        return {
            "skill": "frontend-skill",
            "args": args,
            "message": "前端技能已调用（实际实现需要集成frontend-skill）"
        }
    
    def _handle_planner(self, args: str) -> Dict[str, Any]:
        """
        处理/planner命令（复杂工作规划器）
        
        Args:
            args: 命令参数（任务描述）
        
        Returns:
            执行结果
        """
        return {
            "skill": "complex-work-planner",
            "task": args,
            "message": "工作规划器已调用（实际实现需要集成complex-work-planner）"
        }
    
    def _handle_cache(self, args: str) -> Dict[str, Any]:
        """
        处理/cache命令（缓存管理）
        
        Args:
            args: 命令参数（stats|clear|report）
        
        Returns:
            执行结果
        """
        from utils.llm_cache import get_llm_cache
        
        cache = get_llm_cache()
        action = args.strip().lower() if args else "stats"
        
        if action == "stats":
            return {
                "action": "stats",
                "stats": cache.get_stats(),
                "message": "缓存统计信息"
            }
        elif action == "clear":
            cache.clear_cache()
            return {
                "action": "clear",
                "message": "缓存已清空"
            }
        elif action == "report":
            report = cache.generate_cache_report()
            return {
                "action": "report",
                "report": report,
                "message": "缓存报告已生成"
            }
        else:
            return {
                "action": action,
                "message": f"未知操作: {action}。支持: stats, clear, report"
            }
    
    def _handle_dialogue(self, args: str) -> Dict[str, Any]:
        """
        处理/dialogue命令（对话数据库）
        
        Args:
            args: 命令参数（analyze|report|clear）
        
        Returns:
            执行结果
        """
        from core.dialogue_database import get_dialogue_database
        
        db = get_dialogue_database()
        action = args.strip().lower() if args else "report"
        
        if action == "analyze":
            result = db.analyze_dialogues()
            return {
                "action": "analyze",
                "result": result,
                "message": "对话分析完成"
            }
        elif action == "report":
            report = db.get_reasoning_report()
            return {
                "action": "report",
                "report": report,
                "message": "推理报告已生成"
            }
        elif action == "clear":
            db.clear_dialogues()
            return {
                "action": "clear",
                "message": "对话历史已清空"
            }
        else:
            return {
                "action": action,
                "message": f"未知操作: {action}。支持: analyze, report, clear"
            }
    
    def get_available_commands(self) -> List[Dict[str, str]]:
        """
        获取所有可用命令
        
        Returns:
            命令列表
        """
        commands_list = []
        for name, cmd in self.commands.items():
            commands_list.append({
                "name": name,
                "description": cmd["description"],
                "usage": cmd["usage"]
            })
        return commands_list


# 全局实例
_slash_command_handler = None


def get_slash_command_handler() -> SlashCommandHandler:
    """获取全局斜杠命令处理器实例（单例模式）"""
    global _slash_command_handler
    if _slash_command_handler is None:
        _slash_command_handler = SlashCommandHandler()
    return _slash_command_handler
