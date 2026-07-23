"""
Main Agent 主协调器模块

核心职责：
- 作为系统的中枢神经，协调所有SubAgent的工作
- 实现意图识别，将用户输入路由到正确的SubAgent
- 维护3个记忆点（用户约束、修改方案、工作进度）
- 实现流程控制，确保"不能跳步、不能混搅、不能遗漏"
- 管理对话历史和会话状态

设计思路：
- 采用"控制面与创作面分离"原则：MainAgent负责调度，SubAgent负责执行
- 意图识别采用"关键词匹配 + LLM辅助"的双层策略
- 流程控制基于SessionState的current_step，实现7步工作流
- 记忆点机制确保跨会话的上下文连续性

关键流程：
1. 用户输入 → 意图识别 → 流程控制检查 → SubAgent路由 → 结果处理 → 状态保存
2. 每个SubAgent调用后，结果必须经过Quality Gate才能输出给用户
3. 流程控制确保：扫榜分析(1) → 大纲规划(2) → 章节生成(3) → ...

3个记忆点说明：
- 记忆点1（user_constraints）：用户的总体约束条件，如"不要后宫"、"必须HE"
- 记忆点2（user_modifications）：用户对生成内容的修改记录，用于学习用户偏好
- 记忆点3（work_progress）：当前工作进度，记录各步骤的完成情况
"""
import json
import os
from typing import Dict, List, Any, Optional, Callable
from enum import Enum

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from core.session_state import SessionState
from utils.llm_client import get_llm_client


class Intent(Enum):
    """
    用户意图枚举
    
    意图识别是MainAgent的核心功能，决定了用户输入应该路由到哪个SubAgent。
    每个意图对应一个SubAgent，实现职责的清晰分离。
    """
    ANALYZE_TRENDS = "analyze_trends"      # 分析爆火写法 → Scout Agent
    PLAN_OUTLINE = "plan_outline"          # 规划大纲 → Architect Agent
    GENERATE_CHAPTER = "generate_chapter"  # 生成章节 → Writer Agent
    IMPORT_FILE = "import_file"            # 导入文件 → FileImporter
    QUERY_KNOWLEDGE = "query_knowledge"    # 查询知识库 → GenreKnowledgeBase
    VERSION_MANAGE = "version_manage"      # 版本管理 → VersionManager
    UNKNOWN = "unknown"                    # 未知意图 → 需要进一步澄清


class MainAgent:
    """
    Main Agent 主协调器
    
    核心功能：
    1. 意图识别：通过关键词匹配和LLM辅助识别用户意图
    2. 流程控制：基于SessionState控制7步工作流程
    3. SubAgent调度：根据意图路由到对应的SubAgent
    4. 记忆管理：维护3个记忆点，确保上下文连续性
    5. 状态持久化：每次操作后保存状态，支持断点续传
    
    使用流程：
    1. 初始化时加载SessionState
    2. 接收用户输入 → identify_intent() → route_to_subagent()
    3. SubAgent执行 → process_result() → 保存状态
    4. 返回结果给用户
    """
    
    # 意图关键词映射：用于快速匹配用户意图
    # 设计原则：每个意图配置多个关键词，提高识别准确率
    INTENT_KEYWORDS = {
        Intent.ANALYZE_TRENDS: ["分析", "调研", "爆火", "热门", "写法", "趋势", "扫榜"],
        Intent.PLAN_OUTLINE: ["大纲", "规划", "篇章", "章节规划", "总纲", "卷纲", "outline"],
        Intent.GENERATE_CHAPTER: ["生成", "写", "创作", "第.*章", "正文", "内容"],
        Intent.IMPORT_FILE: ["导入", "上传", "文件", "docx", "pdf", "txt"],
        Intent.QUERY_KNOWLEDGE: ["查询", "查看", "人物", "事件", "伏笔", "知识库"],
        Intent.VERSION_MANAGE: ["版本", "回滚", "历史", "对比", "v1", "v2"],
    }
    
    # SubAgent名称映射：意图到SubAgent的路由表
    # 每个意图对应一个SubAgent，实现职责分离
    INTENT_TO_SUBAGENT = {
        Intent.ANALYZE_TRENDS: "scout",           # 扫榜分析师
        Intent.PLAN_OUTLINE: "architect",         # 架构师
        Intent.GENERATE_CHAPTER: "writer",        # 写手
        Intent.IMPORT_FILE: "importer",           # 文件导入器
        Intent.QUERY_KNOWLEDGE: "knowledge",      # 知识库查询
        Intent.VERSION_MANAGE: "version",         # 版本管理器
    }
    
    def __init__(self):
        """
        初始化MainAgent
        
        初始化流程：
        1. 创建SessionState实例并加载历史状态
        2. 初始化3个记忆点（用户约束、修改记录、工作进度）
        3. 创建空的SubAgent注册表
        4. 创建空的对话历史
        5. 延迟初始化LLM客户端（首次使用时才创建）
        """
        # 加载会话状态（支持断点续传）
        self.session_state = SessionState()
        self.session_state.load()
        
        # 3个记忆点：确保跨会话的上下文连续性
        self.memory_points = {
            "user_constraints": [],      # 记忆点1：用户总体约束（如"不要后宫"、"必须HE"）
            "user_modifications": [],    # 记忆点2：用户修改方案（记录用户对生成内容的修改）
            "work_progress": {}          # 记忆点3：当前工作进度（记录各步骤完成情况）
        }
        
        # SubAgent注册表：存储已注册的SubAgent处理器
        # 键：SubAgent名称（如"scout"、"architect"）
        # 值：处理函数（接收user_input和context，返回结果字典）
        self.subagents: Dict[str, Callable] = {}
        
        # 对话历史：存储所有对话记录，用于上下文连续性
        # 格式：[{"role": "user/assistant", "content": "..."}]
        self.conversation_history: List[Dict[str, str]] = []
        
        # LLM客户端（延迟初始化，首次使用时才创建）
        self._llm_client = None
    
    @property
    def llm_client(self):
        """
        延迟获取LLM客户端（属性装饰器）
        
        设计思路：
        - 延迟初始化：避免在不需要LLM的场景下创建客户端
        - 单例模式：确保整个MainAgent生命周期只有一个客户端实例
        - 简化调用：通过属性访问，无需调用方法
        
        Returns:
            LLMClient实例
        """
        if self._llm_client is None:
            self._llm_client = get_llm_client()
        return self._llm_client
    
    def register_subagent(self, name: str, handler: Callable) -> None:
        """
        注册SubAgent处理器
        
        使用场景：
        - 在目标2中实现各个SubAgent后，通过此方法注册到MainAgent
        - 支持动态注册，可以在运行时添加新的SubAgent
        
        Args:
            name: SubAgent名称（如"scout"、"architect"、"writer"等）
            handler: 处理函数，签名为 handler(user_input: str, context: dict) -> dict
        
        示例：
            def scout_handler(user_input, context):
                return {"success": True, "message": "扫榜分析完成"}
            
            main_agent.register_subagent("scout", scout_handler)
        """
        self.subagents[name] = handler
    
    def receive_input(self, user_input: str) -> Dict[str, Any]:
        """
        接收用户输入并处理（核心入口方法）
        
        处理流程：
        1. 记录对话历史 → 2. 识别意图 → 3. 流程控制检查 → 
        4. 路由到SubAgent → 5. 处理结果 → 6. 更新记忆点 → 7. 保存状态
        
        这是MainAgent的核心方法，所有用户输入都通过此方法处理。
        实现了完整的"输入→处理→输出"流程。
        
        Args:
            user_input: 用户输入文本
        
        Returns:
            处理结果字典，包含以下字段：
            - success: bool - 是否成功
            - intent: str - 识别出的意图
            - message: str - 返回给用户的消息
            - subagent: str - 处理的SubAgent名称（可选）
            - suggestion: str - 流程控制失败时的建议（可选）
        """
        # 1. 记录对话历史（用于上下文连续性）
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })
        
        # 2. 识别用户意图
        intent = self.identify_intent(user_input)
        
        # 3. 检查流程控制（确保不跳步）
        can_proceed, reason = self._check_flow_control(intent)
        if not can_proceed:
            return {
                "success": False,
                "intent": intent.value,
                "message": reason,
                "suggestion": self._get_suggestion()
            }
        
        # 4. 路由到对应的SubAgent
        result = self.route_to_subagent(intent, user_input)
        
        # 5. 处理SubAgent返回结果（未来集成Quality Gate）
        processed_result = self.process_result(result, intent)
        
        # 6. 更新记忆点（维护上下文连续性）
        self._update_memory_points(user_input, result)
        
        # 7. 保存会话状态（支持断点续传）
        self.session_state.save()
        
        return processed_result
    
    def identify_intent(self, user_input: str) -> Intent:
        """
        识别用户意图（双层策略）
        
        识别策略：
        1. 关键词匹配（快速、准确率高）：遍历INTENT_KEYWORDS，匹配到关键词立即返回
        2. LLM辅助判断（兜底、处理复杂表述）：关键词匹配失败时，调用LLM识别
        
        设计思路：
        - 优先使用关键词匹配：速度快、成本低、准确率高
        - LLM作为兜底：处理复杂、模糊的表述
        - 两层策略结合：兼顾效率和准确性
        
        Args:
            user_input: 用户输入文本
        
        Returns:
            识别出的Intent枚举值
        """
        user_input_lower = user_input.lower()
        
        # 第1层：关键词匹配（快速路径）
        for intent, keywords in self.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in user_input_lower:
                    return intent
        
        # 第2层：LLM辅助判断（兜底路径）
        try:
            llm_intent = self._identify_intent_with_llm(user_input)
            if llm_intent != Intent.UNKNOWN:
                return llm_intent
        except Exception as e:
            print(f"LLM意图识别失败: {e}")
        
        return Intent.UNKNOWN
    
    def _identify_intent_with_llm(self, user_input: str) -> Intent:
        """
        使用LLM辅助识别意图（兜底策略）
        
        实现逻辑：
        1. 构造提示词，列出所有意图选项及其描述
        2. 调用LLM进行意图分类
        3. 解析LLM返回的意图名称，映射到Intent枚举
        
        设计思路：
        - 提示词简洁明确，要求LLM只返回意图名称
        - 使用小写的意图名称，便于匹配
        - 如果LLM返回未知内容，默认返回UNKNOWN
        
        Args:
            user_input: 用户输入文本
        
        Returns:
            识别出的Intent枚举值
        """
        # 构造意图分类提示词
        prompt = f"""分析用户意图，从以下选项中选择一个：
- analyze_trends: 分析爆火写法、调研热门小说
- plan_outline: 规划大纲、篇章设计
- generate_chapter: 生成章节内容
- import_file: 导入文件
- query_knowledge: 查询知识库
- version_manage: 版本管理
- unknown: 无法识别

用户输入：{user_input}

只回复意图名称，不要其他内容。"""
        
        # 调用LLM生成意图
        response = self.llm_client.generate(prompt)
        response = response.strip().lower()
        
        # 意图名称映射表
        intent_map = {
            "analyze_trends": Intent.ANALYZE_TRENDS,
            "plan_outline": Intent.PLAN_OUTLINE,
            "generate_chapter": Intent.GENERATE_CHAPTER,
            "import_file": Intent.IMPORT_FILE,
            "query_knowledge": Intent.QUERY_KNOWLEDGE,
            "version_manage": Intent.VERSION_MANAGE,
        }
        
        # 返回映射结果，未知则返回UNKNOWN
        return intent_map.get(response, Intent.UNKNOWN)
    
    def route_to_subagent(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """
        路由到对应的SubAgent（核心调度方法）
        
        实现逻辑：
        1. 根据意图查找对应的SubAgent名称
        2. 检查SubAgent是否已注册
        3. 准备上下文信息（记忆点、对话历史等）
        4. 调用SubAgent处理器
        5. 捕获异常并返回错误信息
        
        设计思路：
        - 使用注册表模式，SubAgent通过register_subagent()动态注册
        - 上下文注入：将记忆点和对话历史传递给SubAgent
        - 异常隔离：SubAgent执行失败不影响主流程
        
        Args:
            intent: 用户意图
            user_input: 用户输入
        
        Returns:
            SubAgent处理结果字典，包含：
            - success: bool - 是否成功
            - message: str - 返回消息
            - subagent: str - SubAgent名称
        """
        # 查找意图对应的SubAgent名称
        subagent_name = self.INTENT_TO_SUBAGENT.get(intent)
        
        # 意图无法映射到SubAgent
        if subagent_name is None:
            return {
                "success": False,
                "message": "无法识别的意图",
                "intent": intent.value
            }
        
        # 查找已注册的SubAgent处理器
        handler = self.subagents.get(subagent_name)
        
        # SubAgent未注册（目标2中实现）
        if handler is None:
            # 返回默认处理，不报错
            return {
                "success": True,
                "message": f"SubAgent '{subagent_name}' 尚未实现，待后续开发",
                "intent": intent.value,
                "subagent": subagent_name
            }
        
        # 准备上下文（包含记忆点和对话历史）
        context = self._prepare_context(intent, user_input)
        
        # 调用SubAgent处理器
        try:
            result = handler(user_input, context)
            result["subagent"] = subagent_name  # 标记处理来源
            return result
        except Exception as e:
            # 异常隔离：SubAgent失败不影响主流程
            return {
                "success": False,
                "message": f"SubAgent执行失败: {e}",
                "intent": intent.value,
                "subagent": subagent_name
            }
    
    def _prepare_context(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """
        准备SubAgent上下文（上下文注入）
        
        核心逻辑：
        收集当前会话状态、记忆点、对话历史等信息，打包成上下文字典传递给SubAgent。
        SubAgent可以基于这些上下文信息做出更准确的决策。
        
        上下文内容：
        - intent: 当前意图
        - current_step: 当前工作步骤
        - user_constraints: 用户约束（记忆点1）
        - user_modifications: 用户修改记录（记忆点2）
        - work_progress: 工作进度（记忆点3）
        - conversation_history: 最近10轮对话（避免上下文过长）
        
        设计思路：
        - 对话历史限制为最近10轮，平衡上下文长度和token消耗
        - 传递记忆点引用，SubAgent可以读取和修改
        
        Args:
            intent: 用户意图
            user_input: 用户输入
        
        Returns:
            上下文字典，包含会话状态和记忆点
        """
        return {
            "intent": intent.value,
            "current_step": self.session_state.current_step,
            "user_constraints": self.memory_points["user_constraints"],
            "user_modifications": self.memory_points["user_modifications"],
            "work_progress": self.memory_points["work_progress"],
            "conversation_history": self.conversation_history[-10:]  # 最近10轮对话
        }
    
    def process_result(self, result: Dict[str, Any], intent: Intent) -> Dict[str, Any]:
        """
        处理SubAgent返回结果（结果后处理）
        
        核心逻辑：
        1. 如果SubAgent执行成功，更新工作进度
        2. 将SubAgent的回复添加到对话历史
        3. 预留Quality Gate接口（目标3实现）
        
        设计思路：
        - 结果后处理：统一处理SubAgent返回的结果
        - 进度更新：成功时自动更新工作进度
        - 对话历史：保持对话连续性
        - Quality Gate：预留接口，目标3中实现
        
        Args:
            result: SubAgent返回结果
            intent: 原始意图
        
        Returns:
            处理后的结果字典
        """
        # 成功时更新工作进度
        if result.get("success"):
            self._update_work_progress(intent, result)
        
        # 将SubAgent回复添加到对话历史
        if "message" in result:
            self.conversation_history.append({
                "role": "assistant",
                "content": result["message"]
            })
        
        # Quality Gate集成将在目标3中实现
        # 届时会在此处添加质量检查逻辑，不合格的结果会被拦截并返回上一步
        
        return result
    
    def _check_flow_control(self, intent: Intent) -> tuple:
        """
        检查流程控制（防止跳步）
        
        核心逻辑：
        1. 定义步骤-意图映射关系（步骤1→扫榜，步骤2→大纲，步骤3→生成）
        2. 允许随时执行的操作（导入文件、查询知识库、版本管理）
        3. 检查当前步骤是否允许执行该意图
        4. 允许回退到之前的步骤（但不允许跳步）
        
        设计思路：
        - 步骤顺序：扫榜分析(1) → 大纲规划(2) → 章节生成(3)
        - 允许回退：可以从步骤3回退到步骤1或2
        - 禁止跳步：不能在步骤1时直接执行步骤3
        - 灵活操作：导入文件、查询知识库等操作不受步骤限制
        
        流程控制规则：
        - 步骤1（扫榜）：只允许ANALYZE_TRENDS
        - 步骤2（大纲）：只允许PLAN_OUTLINE
        - 步骤3（生成）：只允许GENERATE_CHAPTER
        - 允许回退：可以从高步骤回退到低步骤
        - 随时允许：IMPORT_FILE, QUERY_KNOWLEDGE, VERSION_MANAGE
        
        Args:
            intent: 用户意图
        
        Returns:
            (can_proceed, reason) 元组：
            - can_proceed: bool - 是否允许继续
            - reason: str - 拒绝原因（如果拒绝）
        """
        current_step = self.session_state.current_step
        
        # 步骤-意图映射表
        step_intents = {
            1: Intent.ANALYZE_TRENDS,      # 步骤1：扫榜分析
            2: Intent.PLAN_OUTLINE,        # 步骤2：大纲规划
            3: Intent.GENERATE_CHAPTER,    # 步骤3：章节生成
        }
        
        # 允许随时执行的操作（不受步骤限制）
        allowed_anytime = {
            Intent.IMPORT_FILE,            # 导入文件
            Intent.QUERY_KNOWLEDGE,        # 查询知识库
            Intent.VERSION_MANAGE,         # 版本管理
            Intent.UNKNOWN                 # 未知意图（需要进一步澄清）
        }
        
        # 随时允许的操作直接通过
        if intent in allowed_anytime:
            return True, ""
        
        # 检查当前步骤是否允许执行该意图
        expected_intent = step_intents.get(current_step)
        if expected_intent and intent != expected_intent:
            # 允许回退到之前的步骤
            for step, step_intent in step_intents.items():
                if step < current_step and intent == step_intent:
                    return True, ""  # 允许回退
            
            # 拒绝跳步
            return False, f"当前处于步骤{current_step}，请先完成当前步骤或明确指定要修改的步骤"
        
        # 当前步骤允许的意图
        return True, ""
    
    def _get_suggestion(self) -> str:
        """
        获取当前步骤的建议（用户引导）
        
        核心逻辑：
        根据当前工作步骤，返回相应的建议消息，引导用户按流程操作。
        
        设计思路：
        - 步骤1：建议先扫榜分析
        - 步骤2：建议规划大纲
        - 步骤3：建议生成章节
        - 其他步骤：通用提示
        
        Returns:
            建议消息字符串
        """
        step_suggestions = {
            1: "建议先进行'分析爆火写法'，了解当前热门趋势",
            2: "建议进行'规划大纲'，确定故事框架",
            3: "建议开始'生成章节'，创作具体内容",
        }
        return step_suggestions.get(self.session_state.current_step, "请告诉我你想做什么")
    
    def _update_memory_points(self, user_input: str, result: Dict[str, Any]) -> None:
        """
        更新3个记忆点（记忆维护）
        
        核心逻辑：
        1. 检测用户输入中的约束性语句（记忆点1）
        2. 检测用户输入中的修改性语句（记忆点2）
        3. 工作进度由_update_work_progress()更新（记忆点3）
        
        设计思路：
        - 关键词检测：通过关键词识别约束和修改语句
        - 自动记录：检测到约束/修改时自动记录到记忆点
        - 记忆点1（user_constraints）：记录用户的总体约束
        - 记忆点2（user_modifications）：记录用户的修改方案
        - 记忆点3（work_progress）：由其他方法更新
        
        约束关键词：必须、不要、要求、约束、限制、禁止
        修改关键词：修改、改成、换成、调整、改为
        
        Args:
            user_input: 用户输入
            result: SubAgent结果
        """
        # 记忆点1：检测约束性语句
        constraint_keywords = ["必须", "不要", "要求", "约束", "限制", "禁止"]
        for keyword in constraint_keywords:
            if keyword in user_input:
                self.memory_points["user_constraints"].append(user_input)
                break
        
        # 记忆点2：检测修改性语句
        modification_keywords = ["修改", "改成", "换成", "调整", "改为"]
        for keyword in modification_keywords:
            if keyword in user_input:
                self.memory_points["user_modifications"].append({
                    "input": user_input,
                    "result": result.get("message", "")[:100]  # 截取前100字符
                })
                break
        
        # 记忆点3：工作进度由_update_work_progress()更新
    
    def _update_work_progress(self, intent: Intent, result: Dict[str, Any]) -> None:
        """
        更新工作进度（进度追踪）
        
        核心逻辑：
        根据意图类型更新工作进度字典，并同步到SessionState。
        
        进度更新规则：
        - ANALYZE_TRENDS：标记trends_analyzed为True
        - PLAN_OUTLINE：标记outline_planned为True，更新步骤到2
        - GENERATE_CHAPTER：累加chapters_generated计数，首次生成时更新步骤到3
        
        设计思路：
        - 进度字典：记录各步骤的完成情况
        - 步骤同步：完成关键步骤时自动更新SessionState的current_step
        - 计数累加：章节生成采用计数方式
        
        Args:
            intent: 用户意图
            result: SubAgent结果
        """
        progress = self.memory_points["work_progress"]
        
        # 根据意图更新进度
        if intent == Intent.ANALYZE_TRENDS:
            progress["trends_analyzed"] = True
        elif intent == Intent.PLAN_OUTLINE:
            progress["outline_planned"] = True
            self.session_state.update_step(2)  # 更新到步骤2
        elif intent == Intent.GENERATE_CHAPTER:
            chapter_count = progress.get("chapters_generated", 0)
            progress["chapters_generated"] = chapter_count + 1
            if chapter_count == 0:
                self.session_state.update_step(3)  # 首次生成时更新到步骤3
        
        # 同步到SessionState
        self.session_state.current_progress = progress
    
    def _check_step_flow(self, intent: Intent) -> tuple:
        """检查流程是否符合步骤控制
        
        核心逻辑：
        1. 定义每个步骤对应的意图
        2. 检查当前意图是否符合步骤顺序
        3. 允许随时执行的操作（导入文件、查询知识库、版本管理）
        4. 允许回退到之前的步骤（用户修改历史内容）
        
        Args:
            intent: 用户意图
        
        Returns:
            (can_proceed, reason) 元组
        """
        current_step = self.session_state.current_step
        
        # 步骤定义
        step_intents = {
            1: Intent.ANALYZE_TRENDS,
            2: Intent.PLAN_OUTLINE,
            3: Intent.GENERATE_CHAPTER,
        }
        
        # 允许的操作（不受步骤限制）
        allowed_anytime = {
            Intent.IMPORT_FILE,
            Intent.QUERY_KNOWLEDGE,
            Intent.VERSION_MANAGE,
            Intent.UNKNOWN
        }
        
        if intent in allowed_anytime:
            return True, ""
        
        # 检查是否跳步
        expected_intent = step_intents.get(current_step)
        if expected_intent and intent != expected_intent:
            # 允许回退到之前的步骤
            for step, step_intent in step_intents.items():
                if step < current_step and intent == step_intent:
                    return True, ""
            
            return False, f"当前处于步骤{current_step}，请先完成当前步骤或明确指定要修改的步骤"
        
        return True, ""
    
    def _get_suggestion(self) -> str:
        """获取当前步骤的建议"""
        step_suggestions = {
            1: "建议先进行'分析爆火写法'，了解当前热门趋势",
            2: "建议进行'规划大纲'，确定故事框架",
            3: "建议开始'生成章节'，创作具体内容",
        }
        return step_suggestions.get(self.session_state.current_step, "请告诉我你想做什么")
    
    def _update_memory_points(self, user_input: str, result: Dict[str, Any]) -> None:
        """更新3个记忆点
        
        Args:
            user_input: 用户输入
            result: SubAgent结果
        """
        # 记忆点1：用户总体约束（检测约束性语句）
        constraint_keywords = ["必须", "不要", "要求", "约束", "限制", "禁止"]
        for keyword in constraint_keywords:
            if keyword in user_input:
                self.memory_points["user_constraints"].append(user_input)
                break
        
        # 记忆点2：用户修改方案（检测修改性语句）
        modification_keywords = ["修改", "改成", "换成", "调整", "改为"]
        for keyword in modification_keywords:
            if keyword in user_input:
                self.memory_points["user_modifications"].append({
                    "input": user_input,
                    "result": result.get("message", "")[:100]
                })
                break
        
        # 记忆点3：当前工作进度（由_update_work_progress更新）
    
    def _update_work_progress(self, intent: Intent, result: Dict[str, Any]) -> None:
        """更新工作进度
        
        Args:
            intent: 用户意图
            result: SubAgent结果
        """
        progress = self.memory_points["work_progress"]
        
        # 更新进度
        if intent == Intent.ANALYZE_TRENDS:
            progress["trends_analyzed"] = True
        elif intent == Intent.PLAN_OUTLINE:
            progress["outline_planned"] = True
            self.session_state.update_step(2)
        elif intent == Intent.GENERATE_CHAPTER:
            chapter_count = progress.get("chapters_generated", 0)
            progress["chapters_generated"] = chapter_count + 1
            if chapter_count == 0:
                self.session_state.update_step(3)
        
        # 同步到SessionState
        self.session_state.current_progress = progress
    
    def get_memory_points(self) -> Dict[str, Any]:
        """获取当前记忆点
        
        Returns:
            记忆点字典
        """
        return self.memory_points.copy()
    
    def add_user_constraint(self, constraint: str) -> None:
        """添加用户约束
        
        Args:
            constraint: 约束描述
        """
        self.memory_points["user_constraints"].append(constraint)
        self.session_state.add_constraint(constraint)
    
    def add_user_modification(self, modification: Dict[str, Any]) -> None:
        """添加用户修改记录
        
        Args:
            modification: 修改记录
        """
        self.memory_points["user_modifications"].append(modification)
    
    def reset_session(self) -> None:
        """重置会话"""
        self.session_state = SessionState()
        self.memory_points = {
            "user_constraints": [],
            "user_modifications": [],
            "work_progress": {}
        }
        self.conversation_history = []
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态
        
        Returns:
            状态字典
        """
        return {
            "current_step": self.session_state.current_step,
            "active_novel_id": self.session_state.active_novel_id,
            "registered_subagents": list(self.subagents.keys()),
            "conversation_turns": len(self.conversation_history),
            "memory_points": self.memory_points
        }


if __name__ == "__main__":
    # 测试代码
    agent = MainAgent()
    
    # 注册测试SubAgent
    def test_handler(input_text, context):
        return {
            "success": True,
            "message": f"测试处理: {input_text}",
            "context_keys": list(context.keys())
        }
    
    agent.register_subagent("scout", test_handler)
    
    # 测试意图识别
    print("测试意图识别:")
    print(f"  '分析爆火写法' -> {agent.identify_intent('分析爆火写法')}")
    print(f"  '规划大纲' -> {agent.identify_intent('规划大纲')}")
    print(f"  '生成第1章' -> {agent.identify_intent('生成第1章')}")
    
    # 测试接收输入
    print("\n测试接收输入:")
    result = agent.receive_input("分析爆火写法")
    print(f"  结果: {result}")
    
    print("\n系统状态:")
    print(f"  {agent.get_status()}")
