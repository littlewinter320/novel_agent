"""
会话状态管理模块

核心职责：
- 维护系统的全局工作状态，确保跨会话的连续性
- 跟踪当前工作步骤（1-7步流程控制）
- 管理用户约束条件和工作进度
- 维护版本链，支持版本回溯

设计思路：
- 使用JSON文件持久化，确保程序重启后能恢复状态
- 步骤控制采用有限状态机模式，防止跳步操作
- 用户约束采用列表存储，支持多约束叠加
- 进度信息使用字典存储，灵活记录各阶段完成情况

关键属性说明：
- current_step: 当前工作步骤（1=扫榜分析, 2=大纲规划, 3=章节生成...）
- version_chain: 版本历史链，记录所有生成的版本ID
- user_constraints: 用户提出的约束条件（如"不要后宫"、"必须HE"等）
- current_progress: 当前进度详情，记录各步骤的完成状态
- active_novel_id: 当前活跃的小说项目ID
"""
import json
import os
from typing import Dict, List, Any, Optional

# 从 config 导入配置
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class SessionState:
    """
    会话状态管理类
    
    核心功能：
    1. 状态持久化：将工作状态保存到JSON文件，支持断点续传
    2. 步骤控制：管理7步工作流程，确保按序执行
    3. 约束管理：收集和存储用户约束条件
    4. 进度跟踪：记录当前工作进度和完成情况
    
    使用场景：
    - MainAgent在每次操作后调用save()保存状态
    - 程序启动时调用load()恢复上次的工作状态
    - 流程控制时检查current_step判断当前阶段
    """
    
    def __init__(self):
        """
        初始化会话状态
        
        默认状态：
        - 从第1步开始（扫榜分析）
        - 版本链为空
        - 无用户约束
        - 无进度记录
        - 无活跃小说项目
        """
        self.current_step: int = 1
        self.version_chain: List[str] = []
        self.user_constraints: List[str] = []
        self.current_progress: Dict[str, Any] = {}
        self.active_novel_id: Optional[str] = None
    
    def save(self) -> None:
        """
        持久化会话状态到JSON文件
        
        实现细节：
        1. 自动创建数据目录（如果不存在）
        2. 将所有状态属性序列化为JSON格式
        3. 使用UTF-8编码确保中文正确保存
        4. 使用缩进格式便于人工查看和调试
        
        异常处理：
        - 目录创建失败会抛出IOError
        - 文件写入失败会抛出IOError
        - 调用方需要捕获并处理这些异常
        """
        # 确保数据目录存在
        os.makedirs(config.DATA_DIR, exist_ok=True)
        
        # 准备要保存的数据
        data = {
            "current_step": self.current_step,
            "version_chain": self.version_chain,
            "user_constraints": self.user_constraints,
            "current_progress": self.current_progress,
            "active_novel_id": self.active_novel_id
        }
        
        # 写入JSON文件
        with open(config.SESSION_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self) -> None:
        """
        从JSON文件加载会话状态
        
        实现细节：
        1. 检查文件是否存在，不存在则保持默认状态
        2. 读取JSON文件并反序列化
        3. 使用get()方法提供默认值，防止字段缺失导致错误
        4. 捕获JSON解析错误和IO错误，保持程序健壮性
        
        异常处理：
        - JSON格式错误：打印警告，保持默认状态
        - 文件读取错误：打印警告，保持默认状态
        - 文件不存在：静默处理，保持默认状态
        """
        # 如果文件不存在，保持默认值
        if not os.path.exists(config.SESSION_STATE_FILE):
            return
        
        try:
            with open(config.SESSION_STATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 恢复各个属性，使用get()提供默认值
            self.current_step = data.get("current_step", 1)
            self.version_chain = data.get("version_chain", [])
            self.user_constraints = data.get("user_constraints", [])
            self.current_progress = data.get("current_progress", {})
            self.active_novel_id = data.get("active_novel_id")
        except (json.JSONDecodeError, IOError) as e:
            # 如果读取失败，保持默认值
            print(f"警告: 无法加载会话状态文件: {e}")
    
    def update_step(self, step: int) -> None:
        """
        更新当前步骤
        
        流程控制逻辑：
        - 步骤范围：1-7（对应7步工作流程）
        - 超出范围抛出ValueError，防止非法状态
        - 步骤定义：
          1. 扫榜分析（Scout）
          2. 大纲规划（Architect）
          3. 章节生成（Writer）
          4. 连续性审计（Auditor）
          5. 修订（Revisor）
          6. 文风优化（StyleEngineer）
          7. 完成
        
        Args:
            step: 步骤编号 (1-7)
        
        Raises:
            ValueError: 步骤编号超出范围
        """
        if 1 <= step <= 7:
            self.current_step = step
        else:
            raise ValueError(f"步骤编号必须在 1-7 之间，收到: {step}")
    
    def add_constraint(self, constraint: str) -> None:
        """
        添加用户约束
        
        约束类型示例：
        - 题材约束："必须是玄幻题材"
        - 风格约束："文风要轻松幽默"
        - 内容约束："不要后宫情节"
        - 结构约束："必须HE结局"
        
        实现细节：
        1. 去除首尾空白字符
        2. 过滤空字符串
        3. 追加到约束列表末尾
        
        Args:
            constraint: 用户约束描述
        """
        if constraint and constraint.strip():
            self.user_constraints.append(constraint.strip())
    
    def get_progress(self) -> Dict[str, Any]:
        """
        获取当前工作进度
        
        返回字典的浅拷贝，防止外部修改影响内部状态
        
        进度信息示例：
        {
            "scout_completed": True,
            "outline_completed": False,
            "current_chapter": 3,
            "total_chapters": 10
        }
        
        Returns:
            当前进度字典的拷贝
        """
        return self.current_progress.copy()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将会话状态转换为字典
        
        使用场景：
        - 序列化为JSON
        - 传递给其他模块
        - 调试时查看完整状态
        
        返回字典的浅拷贝，防止外部修改影响内部状态
        列表和字典属性使用copy()确保深度隔离
        
        Returns:
            包含所有状态的字典
        """
        return {
            "current_step": self.current_step,
            "version_chain": self.version_chain.copy(),
            "user_constraints": self.user_constraints.copy(),
            "current_progress": self.current_progress.copy(),
            "active_novel_id": self.active_novel_id
        }
