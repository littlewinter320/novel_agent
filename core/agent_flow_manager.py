"""
Agent流程管理器(AgentFlowManager)

核心职责:
- 管理Agent调用流程和顺序
- 实时跟踪Agent执行状态
- 支持自定义流程配置
- 提供流程执行报告

设计思路:
- 流程定义：预定义标准流程（如创作流程、分析流程）
- 流程执行：按顺序调用Agent，记录状态
- 流程定制：允许用户自定义Agent调用顺序
- 状态跟踪：实时显示当前执行的Agent和进度

输出格式:
{
    "flow_name": "流程名称",
    "steps": [执行步骤列表],
    "current_step": 当前步骤,
    "status": "执行状态"
}
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class AgentFlowManager:
    """
    Agent流程管理器类
    
    核心功能:
    1. 流程定义：预定义标准创作流程
    2. 流程执行：按顺序调用Agent
    3. 状态跟踪：实时显示执行状态
    4. 流程定制：支持用户自定义流程
    
    使用场景:
    - 用户创作小说时，自动调用多个Agent协作
    - 显示当前正在执行的Agent
    - 允许用户自定义Agent调用顺序
    
    使用流程:
    1. 创建AgentFlowManager实例
    2. 选择或自定义流程
    3. 执行流程，实时查看状态
    4. 获取执行报告
    """
    
    # 预定义的标准流程
    STANDARD_FLOWS = {
        "novel_creation": {
            "name": "小说创作流程",
            "description": "完整的小说创作流程，包含市场分析、大纲规划、章节生成、质量审核",
            "steps": [
                {
                    "agent": "scout",
                    "name": "扫榜分析师",
                    "description": "分析热门小说，提取爆火特征",
                    "method": "analyze_genre"
                },
                {
                    "agent": "architect",
                    "name": "架构师",
                    "description": "规划小说大纲和章节结构",
                    "method": "plan_novel"
                },
                {
                    "agent": "writer",
                    "name": "写手",
                    "description": "生成章节正文",
                    "method": "generate_chapter"
                },
                {
                    "agent": "style_engineer",
                    "name": "文风工程师",
                    "description": "分析和优化文风",
                    "method": "analyze_writing_style"
                },
                {
                    "agent": "auditor",
                    "name": "审计员",
                    "description": "审核章节质量",
                    "method": "audit_chapter"
                },
                {
                    "agent": "revisor",
                    "name": "修订员",
                    "description": "根据审核结果修订内容",
                    "method": "revise_chapter"
                }
            ]
        },
        "quick_analysis": {
            "name": "快速分析流程",
            "description": "快速分析热门小说特征",
            "steps": [
                {
                    "agent": "scout",
                    "name": "扫榜分析师",
                    "description": "分析热门小说",
                    "method": "analyze_genre"
                }
            ]
        },
        "outline_only": {
            "name": "大纲规划流程",
            "description": "只规划大纲，不生成正文",
            "steps": [
                {
                    "agent": "scout",
                    "name": "扫榜分析师",
                    "description": "分析热门小说",
                    "method": "analyze_genre"
                },
                {
                    "agent": "architect",
                    "name": "架构师",
                    "description": "规划大纲",
                    "method": "plan_novel"
                }
            ]
        }
    }
    
    def __init__(self):
        """
        初始化流程管理器
        
        初始化流程:
        1. 加载预定义流程
        2. 初始化流程状态
        """
        self.current_flow = None
        self.current_step_index = 0
        self.execution_log = []
        self.custom_flows = {}
        
    def list_flows(self) -> List[Dict[str, str]]:
        """
        列出所有可用流程
        
        Returns:
            流程列表，包含名称和描述
        """
        flows = []
        
        # 标准流程
        for key, flow in self.STANDARD_FLOWS.items():
            flows.append({
                "key": key,
                "name": flow["name"],
                "description": flow["description"],
                "step_count": len(flow["steps"])
            })
        
        # 自定义流程
        for key, flow in self.custom_flows.items():
            flows.append({
                "key": key,
                "name": flow["name"],
                "description": flow["description"],
                "step_count": len(flow["steps"]),
                "custom": True
            })
        
        return flows
    
    def select_flow(self, flow_key: str) -> bool:
        """
        选择要执行的流程
        
        Args:
            flow_key: 流程标识符
        
        Returns:
            bool: 是否选择成功
        """
        # 检查标准流程
        if flow_key in self.STANDARD_FLOWS:
            self.current_flow = self.STANDARD_FLOWS[flow_key].copy()
            self.current_step_index = 0
            self.execution_log = []
            return True
        
        # 检查自定义流程
        if flow_key in self.custom_flows:
            self.current_flow = self.custom_flows[flow_key].copy()
            self.current_step_index = 0
            self.execution_log = []
            return True
        
        return False
    
    def create_custom_flow(self, flow_key: str, name: str, 
                          description: str, steps: List[Dict[str, str]]) -> bool:
        """
        创建自定义流程
        
        Args:
            flow_key: 流程标识符
            name: 流程名称
            description: 流程描述
            steps: 步骤列表，每个步骤包含agent、name、description、method
        
        Returns:
            bool: 是否创建成功
        """
        # 验证步骤
        for step in steps:
            if not all(k in step for k in ["agent", "name", "description", "method"]):
                return False
        
        self.custom_flows[flow_key] = {
            "name": name,
            "description": description,
            "steps": steps
        }
        
        return True
    
    def get_current_step(self) -> Optional[Dict[str, Any]]:
        """
        获取当前执行步骤
        
        Returns:
            当前步骤信息，如果没有则返回None
        """
        if not self.current_flow:
            return None
        
        if self.current_step_index >= len(self.current_flow["steps"]):
            return None
        
        return self.current_flow["steps"][self.current_step_index]
    
    def next_step(self) -> Optional[Dict[str, Any]]:
        """
        前进到下一步
        
        Returns:
            下一步骤信息，如果已完成则返回None
        """
        if not self.current_flow:
            return None
        
        self.current_step_index += 1
        
        if self.current_step_index >= len(self.current_flow["steps"]):
            return None
        
        return self.current_flow["steps"][self.current_step_index]
    
    def log_execution(self, step: Dict[str, Any], status: str, 
                     result: Any = None, error: str = None):
        """
        记录执行日志
        
        Args:
            step: 执行的步骤
            status: 执行状态（success/failed/skipped）
            result: 执行结果
            error: 错误信息
        """
        log_entry = {
            "step": step,
            "status": status,
            "result": result,
            "error": error,
            "executed_at": datetime.now().isoformat()
        }
        
        self.execution_log.append(log_entry)
    
    def get_execution_report(self) -> Dict[str, Any]:
        """
        获取执行报告
        
        Returns:
            执行报告字典
        """
        if not self.current_flow:
            return {"error": "没有执行的流程"}
        
        total_steps = len(self.current_flow["steps"])
        completed_steps = len(self.execution_log)
        success_count = sum(1 for log in self.execution_log if log["status"] == "success")
        failed_count = sum(1 for log in self.execution_log if log["status"] == "failed")
        
        return {
            "flow_name": self.current_flow["name"],
            "flow_description": self.current_flow["description"],
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "success_count": success_count,
            "failed_count": failed_count,
            "execution_log": self.execution_log,
            "completed_at": datetime.now().isoformat()
        }
    
    def generate_flow_display(self) -> str:
        """
        生成流程展示文本
        
        Returns:
            流程展示字符串
        """
        if not self.current_flow:
            return "没有选择流程"
        
        display = f"\n{'='*60}\n"
        display += f"流程: {self.current_flow['name']}\n"
        display += f"描述: {self.current_flow['description']}\n"
        display += f"{'='*60}\n\n"
        
        for i, step in enumerate(self.current_flow["steps"]):
            # 判断状态
            if i < self.current_step_index:
                # 已执行
                log_entry = next((log for log in self.execution_log 
                                 if log["step"]["agent"] == step["agent"]), None)
                if log_entry:
                    status_icon = "✓" if log_entry["status"] == "success" else "✗"
                else:
                    status_icon = "?"
            elif i == self.current_step_index:
                # 正在执行
                status_icon = "▶"
            else:
                # 待执行
                status_icon = "○"
            
            display += f"{status_icon} [{i+1}/{len(self.current_flow['steps'])}] "
            display += f"{step['name']} ({step['agent']})\n"
            display += f"   {step['description']}\n\n"
        
        return display
    
    def get_agent_status_display(self, step: Dict[str, Any], status: str) -> str:
        """
        生成Agent状态展示
        
        Args:
            step: 当前步骤
            status: 状态（running/completed/failed）
        
        Returns:
            状态展示字符串
        """
        status_icons = {
            "running": "⏳",
            "completed": "✓",
            "failed": "✗"
        }
        
        icon = status_icons.get(status, "?")
        
        display = f"\n{icon} 正在调用: {step['name']} ({step['agent']})\n"
        display += f"   任务: {step['description']}\n"
        
        return display


# 全局实例
_agent_flow_manager = None


def get_agent_flow_manager() -> AgentFlowManager:
    """获取全局AgentFlowManager实例（单例模式）"""
    global _agent_flow_manager
    if _agent_flow_manager is None:
        _agent_flow_manager = AgentFlowManager()
    return _agent_flow_manager
