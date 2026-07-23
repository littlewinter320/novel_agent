"""
模糊度检测器(AmbiguityDetector)

核心职责:
- 检测用户输入中的模糊/不完整/歧义/矛盾信息
- 触发提问机制，格式：[A] 选项1 [B] 选项2 [C] 选项3 [D] 其他
- 必须有"其他"选项

工作流程:
接收用户输入 → 检测模糊度 → 生成提问 → 返回选项

设计思路:
- 采用"规则检测 + LLM辅助"的双层策略
- 规则检测：关键词匹配、模式识别
- LLM辅助：复杂语义分析

关键算法:
- 信息不完整检测：检查是否缺少关键参数
- 信息歧义检测：检查是否有多种理解
- 信息矛盾检测：检查是否与之前信息矛盾
- 信息模糊检测：检查是否太模糊

输出格式:
{
    "is_ambiguous": bool,
    "ambiguity_type": 模糊类型,
    "questions": [提问列表]
}
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.llm_client import get_llm_client


class AmbiguityDetector:
    """
    模糊度检测器类
    
    核心功能:
    1. 信息不完整检测：检查是否缺少关键参数
    2. 信息歧义检测：检查是否有多种理解
    3. 信息矛盾检测：检查是否与之前信息矛盾
    4. 信息模糊检测：检查是否太模糊
    5. 提问生成：为每个模糊点生成带选项的提问
    
    使用场景:
    - 用户输入需求时，检测是否清晰
    - 用户修改设定是，检测是否矛盾
    - 用户提供信息时，检测是否完整
    
    使用流程:
    1. 调用detect_ambiguity(user_input, context)
    2. 内部自动执行4种检测
    3. 生成提问（带选项）
    4. 返回检测结果
    """
    
    # 关键参数列表
    REQUIRED_PARAMS = {
        "genre": ["题材", "类型", "风格"],
        "protagonist": ["主角", "主人公", "男主", "女主"],
        "plot": ["剧情", "故事", "情节", "主线"],
        "setting": ["背景", "设定", "世界观"]
    }
    
    # 模糊词汇
    AMBIGUOUS_WORDS = [
        "可能", "也许", "大概", "似乎", "好像", "或许",
        "一些", "某些", "部分", "有点", "稍微"
    ]
    
    # 矛盾关键词
    CONTRADICTION_WORDS = [
        "但是", "然而", "不过", "可是", "却", "反而"
    ]
    
    def __init__(self):
        """
        初始化模糊度检测器
        
        初始化流程:
        1. 获取LLM客户端
        2. 初始化检测结果缓存（供 generate_questions 使用）
        """
        self.llm_client = get_llm_client()
        # 缓存最近一次 detect_ambiguity 的检测结果，供 generate_questions() 使用
        self._last_detection_result: Dict[str, Any] = {}
    
    def detect_ambiguity(self, user_input: str,
                        context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        检测用户输入的模糊度（核心方法）
        
        实现逻辑:
        1. 检测信息不完整
        2. 检测信息歧义
        3. 检测信息矛盾
        4. 检测信息模糊
        5. 生成提问（带选项）
        
        与 SessionState 的集成:
        - 如果调用方未提供 context，则尝试从 SessionState 获取
        - context 中的 user_constraints / current_progress 等会被用于矛盾检测
        - 已存在于 context 中的关键参数不会被重复标记为"缺失"
        
        Args:
            user_input: 用户输入
            context: 上下文信息（可选）。若为 None，则自动从 SessionState 获取
        
        Returns:
            检测结果字典，包含：
            - is_ambiguous: 是否模糊
            - ambiguity_type: 模糊类型
            - questions: 提问列表（每个提问包含[A][B][C][D]四个选项）
            - detected_at: 检测时间戳
        """
        # 若未提供 context，则从 SessionState 获取
        if context is None:
            context = self._get_context_from_session_state()
        
        # 1. 检测信息不完整
        incomplete_result = self._check_incomplete(user_input, context)
        
        # 2. 检测信息歧义
        ambiguous_result = self._check_ambiguous(user_input)
        
        # 3. 检测信息矛盾
        contradiction_result = self._check_contradiction(user_input, context)
        
        # 4. 检测信息模糊
        vague_result = self._check_vague(user_input)
        
        # 汇总结果
        is_ambiguous = (
            incomplete_result.get("is_ambiguous", False) or
            ambiguous_result.get("is_ambiguous", False) or
            contradiction_result.get("is_ambiguous", False) or
            vague_result.get("is_ambiguous", False)
        )
        
        questions = []
        questions.extend(incomplete_result.get("questions", []))
        questions.extend(ambiguous_result.get("questions", []))
        questions.extend(contradiction_result.get("questions", []))
        questions.extend(vague_result.get("questions", []))
        
        # 确定主要模糊类型（优先级：矛盾 > 歧义 > 模糊 > 不完整）
        ambiguity_type = "none"
        if contradiction_result.get("is_ambiguous"):
            ambiguity_type = "contradiction"
        elif ambiguous_result.get("is_ambiguous"):
            ambiguity_type = "ambiguous"
        elif vague_result.get("is_ambiguous"):
            ambiguity_type = "vague"
        elif incomplete_result.get("is_ambiguous"):
            ambiguity_type = "incomplete"
        
        result = {
            "is_ambiguous": is_ambiguous,
            "ambiguity_type": ambiguity_type,
            "questions": questions,
            "detected_at": datetime.now().isoformat()
        }
        
        # 缓存检测结果，供 generate_questions() 使用
        self._last_detection_result = result
        
        return result
    
    def generate_questions(self) -> List[Dict[str, Any]]:
        """
        生成澄清问题（公开方法）
        
        基于最近一次 detect_ambiguity() 的结果，返回带[A][B][C][D]选项的澄清问题列表。
        每个问题格式:
        {
            "question": "问题描述",
            "options": ["[A] 选项1", "[B] 选项2", "[C] 选项3", "[D] 其他(请输入您的想法)"]
        }
        
        使用方式:
            result = detector.detect_ambiguity(user_input, context)
            if result["is_ambiguous"]:
                questions = detector.generate_questions()
                for q in questions:
                    print(q["question"])
                    for opt in q["options"]:
                        print(f"  {opt}")
        
        Returns:
            问题列表，每个问题包含 question 和 options 字段。
            options 始终包含 [A][B][C][D] 四个选项，其中 [D] 为"其他"。
            如果未检测到模糊，返回空列表。
        """
        if not self._last_detection_result:
            return []
        
        questions = self._last_detection_result.get("questions", [])
        
        # 确保每个问题都符合格式要求
        validated_questions = []
        for q in questions:
            validated_q = self._validate_question_format(q)
            validated_questions.append(validated_q)
        
        return validated_questions
    
    def _validate_question_format(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证并规范化问题格式，确保包含[A][B][C][D]四个选项
        
        规则:
        - 必须包含 "question" 和 "options" 字段
        - options 必须恰好包含 [A][B][C][D] 四个选项
        - [D] 必须为"其他"选项
        - 如果原始选项不足3个，补充默认选项
        - 如果原始选项超过3个（不含D），截断到3个
        
        Args:
            question: 原始问题字典
        
        Returns:
            规范化后的问题字典
        """
        if not isinstance(question, dict):
            return {
                "question": "请提供更多信息:",
                "options": [
                    "[A] 选项1",
                    "[B] 选项2",
                    "[C] 选项3",
                    "[D] 其他(请输入您的想法)"
                ]
            }
        
        q_text = question.get("question", "请提供更多信息:")
        options = question.get("options", [])
        
        # 过滤掉已有的[D]其他选项，保留[A][B][C]选项
        abc_options = [opt for opt in options if not opt.startswith("[D]")]
        
        # 确保至少有3个[A][B][C]选项
        default_filler = [
            "[A] 我需要更多信息",
            "[B] 让我重新描述",
            "[C] 暂时跳过此项"
        ]
        while len(abc_options) < 3:
            # 使用默认填充选项，避免重复
            for filler in default_filler:
                if filler not in abc_options:
                    abc_options.append(filler)
                    if len(abc_options) >= 3:
                        break
        
        # 截断到最多3个[A][B][C]选项
        abc_options = abc_options[:3]
        
        # 重新标记为[A][B][C]
        final_options = []
        labels = ["[A]", "[B]", "[C]"]
        for i, opt in enumerate(abc_options):
            # 去除原有的[A]/[B]/[C]前缀，重新添加规范前缀
            clean_opt = opt
            for label in ["[A]", "[B]", "[C]", "[D]"]:
                if clean_opt.startswith(label + " "):
                    clean_opt = clean_opt[len(label) + 1:]
                    break
                elif clean_opt.startswith(label):
                    clean_opt = clean_opt[len(label):]
                    break
            final_options.append(f"{labels[i]} {clean_opt.strip()}")
        
        # 始终添加[D]其他选项
        final_options.append("[D] 其他(请输入您的想法)")
        
        return {
            "question": q_text,
            "options": final_options
        }
    
    def _get_context_from_session_state(self) -> Dict[str, Any]:
        """
        从 SessionState 获取上下文信息
        
        将 SessionState 中的关键信息转换为 ambiguity detector 可用的 context 格式。
        包含:
        - user_constraints: 用户约束条件列表
        - current_progress: 当前进度
        - current_step: 当前步骤
        - active_novel_id: 当前小说项目ID
        
        如果 SessionState 无法加载，返回空字典。
        
        Returns:
            上下文信息字典
        """
        try:
            from core.session_state import SessionState
            state = SessionState()
            state.load()
            return {
                "user_constraints": state.user_constraints,
                "current_progress": state.current_progress,
                "current_step": state.current_step,
                "active_novel_id": state.active_novel_id,
                "version_chain": state.version_chain
            }
        except Exception as e:
            print(f"从 SessionState 获取上下文失败: {e}")
            return {}
    
    def _check_incomplete(self, user_input: str,
                         context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        检测信息不完整
        
        实现逻辑:
        1. 检查用户输入中是否包含关键参数关键词
        2. 若输入中未找到，再检查 context 中是否已有该参数信息
        3. 仅当输入和上下文中都缺少该参数时，才标记为缺失并生成提问
        
        Args:
            user_input: 用户输入
            context: 上下文信息（来自 SessionState 或调用方传入）
        
        Returns:
            检测结果字典
        """
        missing_params = []
        questions = []
        
        # 从 context 中提取已知的关键参数（用于避免重复提问）
        context_params = self._extract_params_from_context(context)
        
        # 检查每个关键参数
        for param, keywords in self.REQUIRED_PARAMS.items():
            # 先在用户输入中查找
            found_in_input = False
            for keyword in keywords:
                if keyword in user_input:
                    found_in_input = True
                    break
            
            # 若输入中没有，检查 context 中是否已有
            found_in_context = param in context_params
            
            if not found_in_input and not found_in_context:
                missing_params.append(param)
                # 生成提问
                question = self._generate_question_for_param(param)
                questions.append(question)
        
        return {
            "is_ambiguous": len(missing_params) > 0,
            "missing_params": missing_params,
            "questions": questions
        }
    
    def _extract_params_from_context(self, context: Dict[str, Any]) -> Dict[str, str]:
        """
        从上下文信息中提取已知的关键参数
        
        扫描 context 中的 user_constraints、current_progress 等字段，
        通过关键词匹配识别已经确定的参数值。
        
        Args:
            context: 上下文信息字典
        
        Returns:
            已识别的参数字典，格式为 {param_name: matched_keyword}
        """
        if not context:
            return {}
        
        found_params = {}
        
        # 收集所有上下文本用于关键词扫描
        text_parts = []
        
        # 从 user_constraints 提取
        constraints = context.get("user_constraints", [])
        if isinstance(constraints, list):
            text_parts.extend(constraints)
        
        # 从 current_progress 提取
        progress = context.get("current_progress", {})
        if isinstance(progress, dict):
            for v in progress.values():
                if isinstance(v, str):
                    text_parts.append(v)
                elif isinstance(v, list):
                    text_parts.extend([str(item) for item in v])
        
        combined_text = " ".join(text_parts)
        
        # 对每个关键参数进行关键词匹配
        for param, keywords in self.REQUIRED_PARAMS.items():
            for keyword in keywords:
                if keyword in combined_text:
                    found_params[param] = keyword
                    break
        
        return found_params
    
    def _check_ambiguous(self, user_input: str) -> Dict[str, Any]:
        """
        检测信息歧义

        实现逻辑:
        1. 检查是否包含模糊词汇
        2. 使用LLM判断是否有多种理解
        3. 生成的问题必须包含[A][B][C][D]四个选项

        Args:
            user_input: 用户输入

        Returns:
            检测结果字典
        """
        # 检查模糊词汇
        ambiguous_words_found = []
        for word in self.AMBIGUOUS_WORDS:
            if word in user_input:
                ambiguous_words_found.append(word)

        # 如果使用LLM进一步判断
        if ambiguous_words_found:
            prompt = f"""判断以下用户输入是否有多种理解。

用户输入: {user_input}

发现的模糊词汇: {', '.join(ambiguous_words_found)}

请判断:
1. 是否有多种理解方式
2. 如果有，列出不同的理解（至少列出3种）

以JSON格式返回:
{{
    "is_ambiguous": true/false,
    "interpretations": ["理解1", "理解2", "理解3"]
}}

只返回JSON对象。"""

            try:
                response = self.llm_client.generate(prompt)
                result = json.loads(response)

                questions = []
                if result.get("is_ambiguous"):
                    interpretations = result.get("interpretations", [])
                    # 确保至少有3种理解，不足则补充默认选项
                    default_interpretations = [
                        "按字面意思理解",
                        "按比喻/引申理解",
                        "按反问/否定理解"
                    ]
                    while len(interpretations) < 3:
                        for default_interp in default_interpretations:
                            if default_interp not in interpretations:
                                interpretations.append(default_interp)
                                if len(interpretations) >= 3:
                                    break

                    # 构建[A][B][C][D]四个选项
                    options = [f"[{chr(65+i)}] {interp}" for i, interp in enumerate(interpretations[:3])]
                    options.append("[D] 其他(请输入您的想法)")

                    question = {
                        "question": "您的表述有多种理解，请选择您想要的意思:",
                        "options": options
                    }
                    questions.append(question)

                return {
                    "is_ambiguous": result.get("is_ambiguous", False),
                    "ambiguous_words": ambiguous_words_found,
                    "questions": questions
                }
            except Exception as e:
                print(f"歧义检测失败: {e}")

        return {
            "is_ambiguous": False,
            "ambiguous_words": [],
            "questions": []
        }
    
    def _check_contradiction(self, user_input: str,
                            context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        检测信息矛盾
        
        实现逻辑:
        1. 检查是否与上下文信息矛盾
        2. 使用LLM判断是否有矛盾
        
        Args:
            user_input: 用户输入
            context: 上下文信息
        
        Returns:
            检测结果字典
        """
        if not context:
            return {
                "is_ambiguous": False,
                "contradictions": [],
                "questions": []
            }
        
        # 使用LLM判断矛盾
        prompt = f"""判断以下用户输入是否与上下文信息矛盾。

用户输入: {user_input}

上下文信息: {json.dumps(context, ensure_ascii=False)}

请判断:
1. 是否有矛盾
2. 如果有，指出矛盾之处

以JSON格式返回:
{{
    "is_contradiction": true/false,
    "contradictions": ["矛盾1", "矛盾2"]
}}

只返回JSON对象。"""
        
        try:
            response = self.llm_client.generate(prompt)
            result = json.loads(response)
            
            questions = []
            if result.get("is_contradiction"):
                contradictions = result.get("contradictions", [])
                question = {
                    "question": "您的输入与之前的信息有矛盾，请确认:",
                    "options": [
                        "[A] 以最新输入为准",
                        "[B] 以之前信息为准",
                        "[C] 我需要重新说明",
                        "[D] 其他(请输入您的想法)"
                    ]
                }
                questions.append(question)
            
            return {
                "is_ambiguous": result.get("is_contradiction", False),
                "contradictions": result.get("contradictions", []),
                "questions": questions
            }
        except Exception as e:
            print(f"矛盾检测失败: {e}")
            return {
                "is_ambiguous": False,
                "contradictions": [],
                "questions": []
            }
    
    def _check_vague(self, user_input: str) -> Dict[str, Any]:
        """
        检测信息模糊
        
        实现逻辑:
        1. 检查输入是否太短
        2. 检查是否缺少具体细节
        3. 使用LLM判断是否太模糊
        
        Args:
            user_input: 用户输入
        
        Returns:
            检测结果字典
        """
        # 检查输入长度
        if len(user_input) < 10:
            question = {
                "question": "您的输入太简短，请提供更多细节:",
                "options": [
                    "[A] 我想写一个关于成长的故事",
                    "[B] 我想写一个关于复仇的故事",
                    "[C] 我想写一个关于爱情的故事",
                    "[D] 其他(请输入您的想法)"
                ]
            }
            return {
                "is_ambiguous": True,
                "reason": "输入太简短",
                "questions": [question]
            }
        
        # 使用LLM判断是否太模糊
        prompt = f"""判断以下用户输入是否太模糊，缺少具体细节。

用户输入: {user_input}

请判断:
1. 是否太模糊
2. 如果太模糊，缺少什么信息

以JSON格式返回:
{{
    "is_vague": true/false,
    "missing_info": ["缺少的信息1", "缺少的信息2"]
}}

只返回JSON对象。"""
        
        try:
            response = self.llm_client.generate(prompt)
            result = json.loads(response)
            
            questions = []
            if result.get("is_vague"):
                missing_info = result.get("missing_info", [])
                question = {
                    "question": "您的输入缺少一些具体信息，请补充:",
                    "options": [
                        "[A] 我需要更多关于主角的设定",
                        "[B] 我需要更多关于剧情的规划",
                        "[C] 我需要更多关于世界观的设定",
                        "[D] 其他(请输入您的想法)"
                    ]
                }
                questions.append(question)
            
            return {
                "is_ambiguous": result.get("is_vague", False),
                "missing_info": result.get("missing_info", []),
                "questions": questions
            }
        except Exception as e:
            print(f"模糊检测失败: {e}")
            return {
                "is_ambiguous": False,
                "missing_info": [],
                "questions": []
            }
    
    def _generate_question_for_param(self, param: str) -> Dict[str, Any]:
        """
        为缺失参数生成提问
        
        Args:
            param: 参数名称
        
        Returns:
            提问字典
        """
        question_templates = {
            "genre": {
                "question": "请选择小说题材:",
                "options": [
                    "[A] 玄幻(修仙、魔法等)",
                    "[B] 都市(现代都市生活)",
                    "[C] 科幻(未来科技、太空等)",
                    "[D] 其他(请输入您的想法)"
                ]
            },
            "protagonist": {
                "question": "请选择主角类型:",
                "options": [
                    "[A] 废柴逆袭(从弱到强)",
                    "[B] 天才流(天赋异禀)",
                    "[C] 重生复仇(重回过去)",
                    "[D] 其他(请输入您的想法)"
                ]
            },
            "plot": {
                "question": "请选择核心剧情:",
                "options": [
                    "[A] 成长(不断成长突破)",
                    "[B] 复仇(为复仇而战)",
                    "[C] 探索(探索未知世界)",
                    "[D] 其他(请输入您的想法)"
                ]
            },
            "setting": {
                "question": "请选择世界背景:",
                "options": [
                    "[A] 古代(修仙世界、江湖等)",
                    "[B] 现代(都市生活)",
                    "[C] 未来(科幻世界)",
                    "[D] 其他(请输入您的想法)"
                ]
            }
        }
        
        return question_templates.get(param, {
            "question": f"请提供{param}:",
            "options": ["[A] 选项1", "[B] 选项2", "[C] 选项3", "[D] 其他"]
        })


# 全局实例
_ambiguity_detector = None


def get_ambiguity_detector() -> AmbiguityDetector:
    """获取全局模糊度检测器实例（单例模式）"""
    global _ambiguity_detector
    if _ambiguity_detector is None:
        _ambiguity_detector = AmbiguityDetector()
    return _ambiguity_detector
