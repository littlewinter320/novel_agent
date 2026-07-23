"""
写手(SubAgent-Writer)

核心职责:
- 根据章节规划+真相文件+风格指南+题材禁忌，生成章节正文
- 内置25条通用写作规则（人物塑造、去AI味、节奏控制、视角一致）
- 题材专属禁忌
- 每章生成前输出"自检表"，生成后输出"结算表"

工作流程:
接收规划+真相文件+风格指南 → 自检表 → 加载相关历史摘要 → 生成正文 → 结算表 → 交给审计员

关键算法:
- 上下文构建：整合章节规划、真相文件、风格指南、前文摘要
- 规则注入：将25条通用规则和题材禁忌注入到Prompt中
- 自检表生成：在生成正文前，列出本章涉及的角色、伏笔、爽点
- 结算表生成：在生成正文后，总结新增/变更的角色状态、事件、伏笔

输出格式:
{
    "self_check": 自检表,
    "chapter_content": 章节正文,
    "settlement": 结算表,
    "word_count": 字数统计
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
from core.genre_knowledge import get_genre_knowledge_base
from core.truth_files import TruthFiles


class WriterAgent:
    """
    写手类
    
    核心功能:
    1. 章节生成：根据规划生成章节正文
    2. 自检表生成：生成前列出本章要点
    3. 结算表生成：生成后总结变更
    4. 规则注入：内置25条通用写作规则
    5. 题材禁忌：加载题材专属禁忌
    6. 多样性控制：集成表达变体库、梗库、结构模板库
    
    使用场景:
    - 用户确认章节规划后，生成章节正文
    - 批量生成多章内容
    - 重写某章节
    
    使用流程:
    1. 调用generate_self_check()生成自检表
    2. 用户确认自检表
    3. 调用generate_chapter()生成正文
    4. 调用generate_settlement()生成结算表
    5. 将结算表交给审计员
    """
    
    # 25条通用写作规则
    WRITING_RULES = [
        # 人物塑造（5条）
        "1. 角色行为必须符合其性格设定，避免OOC",
        "2. 对话要体现角色个性，不同角色说话风格应有区别",
        "3. 角色成长要有渐进性，避免突变",
        "4. 配角要有存在感，不能沦为工具人",
        "5. 反派要有合理动机，不能为恶而恶",
        
        # 去AI味（5条）
        "6. 避免使用'首先、其次、最后'等机械连接词",
        "7. 避免过度使用'然而、但是'等转折词",
        "8. 避免'值得一提的是、需要注意的是'等AI常用句式",
        "9. 避免过度总结性语句，如'综上所述、总的来说'",
        "10. 避免过度使用排比句，保持句式多样性",
        
        # 节奏控制（5条）
        "11. 开篇3章必须建立核心冲突，吸引读者",
        "12. 每章至少一个小高潮或悬念点",
        "13. 战斗场景节奏要快，情感场景节奏要慢",
        "14. 避免连续多章都是日常剧情，要有张有弛",
        "15. 章节结尾要有钩子，吸引读者继续阅读",
        
        # 视角一致（5条）
        "16. 保持叙事视角一致，避免频繁切换视角",
        "17. 第三人称叙事时，不要混入第一人称",
        "18. 角色认知边界要清晰，不能知道不该知道的事",
        "19. 内心独白要符合角色性格",
        "20. 避免上帝视角，让读者通过角色视角了解世界",
        
        # 其他（5条）
        "21. 环境描写要服务于氛围营造，不要为描写而描写",
        "22. 伏笔要有明确的回收计划，不要埋而不收",
        "23. 爽点分布要合理，不能连续多章无爽点",
        "24. 避免过度使用网络流行语，保持 timeless",
        "25. 每章字数控制在2000-5000字，避免过长或过短"
    ]
    
    def __init__(self):
        """
        初始化写手
        
        初始化流程:
        1. 获取LLM客户端
        2. 获取题材知识库
        3. 初始化真相文件管理器
        4. 初始化章节缓存
        """
        self.llm_client = get_llm_client()
        self.genre_knowledge_base = get_genre_knowledge_base()
        self.truth_files = TruthFiles()
        self._chapter_cache = {}
    
    def generate_chapter(self, chapter_plan: Dict[str, Any], 
                        genre: str,
                        style_guide: Dict[str, Any] = None,
                        previous_summaries: List[str] = None) -> Dict[str, Any]:
        """
        生成章节正文（核心方法）
        
        实现逻辑:
        1. 构建上下文：整合章节规划、真相文件、风格指南、前文摘要
        2. 加载题材禁忌
        3. 构建Prompt：包含写作规则、上下文、章节规划
        4. 调用LLM生成正文
        5. 生成结算表
        
        Args:
            chapter_plan: 章节规划（包含章节号、标题、核心事件等）
            genre: 题材名称
            style_guide: 风格指南（可选）
            previous_summaries: 前文摘要列表（可选）
        
        Returns:
            章节生成结果字典，包含：
            - chapter_content: 章节正文
            - settlement: 结算表
            - word_count: 字数统计
        """
        chapter_num = chapter_plan.get("chapter_num", 1)
        chapter_title = chapter_plan.get("chapter_title", f"第{chapter_num}章")
        core_event = chapter_plan.get("core_event", "")
        estimated_words = chapter_plan.get("estimated_words", 3000)
        
        # 1. 生成自检表
        self_check = self.generate_self_check(chapter_plan, genre)
        
        # 2. 构建上下文
        context = self._build_context(chapter_plan, genre, style_guide, previous_summaries)
        
        # 3. 加载题材禁忌
        genre_info = self.genre_knowledge_base.get_genre(genre)
        taboo_list = genre_info.get("taboo_list", []) if genre_info else []
        
        # 4. 构建Prompt
        prompt = self._build_chapter_prompt(
            chapter_plan=chapter_plan,
            context=context,
            taboo_list=taboo_list,
            style_guide=style_guide
        )
        
        # 5. 调用LLM生成正文
        try:
            chapter_content = self.llm_client.generate(prompt)
            
            # 6. 生成结算表
            settlement = self.generate_settlement(chapter_plan, chapter_content, genre)
            
            # 7. 统计字数
            word_count = len(chapter_content)
            
            result = {
                "chapter_num": chapter_num,
                "chapter_title": chapter_title,
                "chapter_content": chapter_content,
                "self_check": self_check,
                "settlement": settlement,
                "word_count": word_count,
                "generated_at": datetime.now().isoformat()
            }
            
            # 缓存结果
            self._chapter_cache[chapter_num] = result
            
            return result
        except Exception as e:
            print(f"生成章节失败: {e}")
            return {
                "chapter_num": chapter_num,
                "chapter_title": chapter_title,
                "chapter_content": f"生成失败: {e}",
                "self_check": self_check,
                "settlement": {},
                "word_count": 0,
                "error": str(e)
            }
    
    def generate_self_check(self, chapter_plan: Dict[str, Any], genre: str) -> Dict[str, Any]:
        """
        生成自检表（生成前检查清单）
        
        实现逻辑:
        1. 从章节规划中提取关键信息
        2. 从真相文件中加载相关角色、伏笔
        3. 构建自检表：本章涉及的角色、伏笔、爽点设计
        
        Args:
            chapter_plan: 章节规划
            genre: 题材名称
        
        Returns:
            自检表字典
        """
        chapter_num = chapter_plan.get("chapter_num", 1)
        core_event = chapter_plan.get("core_event", "")
        
        # 从真相文件中加载相关信息
        self.truth_files.load_all()
        
        # 提取相关角色
        character_matrix = self.truth_files.get_file("character_matrix")
        characters = character_matrix.get("characters", {})
        relevant_characters = list(characters.keys())[:5]  # 最多5个角色
        
        # 提取相关伏笔
        foreshadow_hooks = self.truth_files.get_file("foreshadow_hooks")
        foreshadows = foreshadow_hooks.get("foreshadows", [])
        relevant_foreshadows = [
            f for f in foreshadows 
            if f.get("plant_chapter", 0) <= chapter_num <= f.get("resolve_chapter", 9999)
        ][:3]  # 最多3个伏笔
        
        # 设计爽点
        excitement_design = self._design_excitement(core_event, genre)
        
        self_check = {
            "chapter_num": chapter_num,
            "involved_characters": relevant_characters,
            "involved_foreshadows": [f.get("foreshadow_name", "") for f in relevant_foreshadows],
            "excitement_design": excitement_design,
            "key_points": [
                f"核心事件: {core_event}",
                f"涉及角色: {', '.join(relevant_characters)}",
                f"涉及伏笔: {len(relevant_foreshadows)}个"
            ]
        }
        
        return self_check
    
    def _design_excitement(self, core_event: str, genre: str) -> str:
        """
        设计爽点
        
        实现逻辑:
        1. 根据核心事件和题材，设计本章的爽点
        2. 使用LLM生成爽点设计
        
        Args:
            core_event: 核心事件
            genre: 题材名称
        
        Returns:
            爽点设计描述
        """
        prompt = f"""基于以下核心事件，设计本章的爽点。

核心事件: {core_event}
题材: {genre}

请设计一个符合该题材的爽点，要求：
- 具体可感知
- 符合读者期待
- 与核心事件相关

请用一句话描述爽点设计。"""
        
        try:
            excitement = self.llm_client.generate(prompt)
            return excitement.strip()
        except Exception as e:
            print(f"设计爽点失败: {e}")
            return "待设计"
    
    def generate_settlement(self, chapter_plan: Dict[str, Any], 
                           chapter_content: str,
                           genre: str) -> Dict[str, Any]:
        """
        生成结算表（生成后总结）
        
        实现逻辑:
        1. 分析章节正文，提取新增/变更的角色状态
        2. 提取事件摘要
        3. 提取伏笔状态变更
        4. 构建结算表
        
        Args:
            chapter_plan: 章节规划
            chapter_content: 章节正文
            genre: 题材名称
        
        Returns:
            结算表字典
        """
        chapter_num = chapter_plan.get("chapter_num", 1)
        
        # 使用LLM分析章节内容
        prompt = f"""分析以下章节正文，提取关键信息。

章节正文:
{chapter_content[:2000]}...  # 只取前2000字

请提取以下信息，以JSON格式返回:
{{
    "new_character_states": ["新增的角色状态变更"],
    "event_summary": "事件摘要",
    "foreshadow_changes": ["伏笔状态变更"],
    "key_items": ["新增的重要物品/道具"]
}}

只返回JSON对象。"""
        
        try:
            analysis = self.llm_client.generate(prompt)
            settlement_data = json.loads(analysis)
            
            settlement = {
                "chapter_num": chapter_num,
                "new_character_states": settlement_data.get("new_character_states", []),
                "event_summary": settlement_data.get("event_summary", ""),
                "foreshadow_changes": settlement_data.get("foreshadow_changes", []),
                "key_items": settlement_data.get("key_items", []),
                "word_count": len(chapter_content)
            }
            
            return settlement
        except Exception as e:
            print(f"生成结算表失败: {e}")
            return {
                "chapter_num": chapter_num,
                "new_character_states": [],
                "event_summary": "结算表生成失败",
                "foreshadow_changes": [],
                "key_items": [],
                "word_count": len(chapter_content)
            }
    
    def _build_context(self, chapter_plan: Dict[str, Any],
                      genre: str,
                      style_guide: Dict[str, Any] = None,
                      previous_summaries: List[str] = None) -> Dict[str, Any]:
        """
        构建上下文
        
        实现逻辑:
        1. 加载真相文件
        2. 整合前文摘要
        3. 构建上下文字典
        
        Args:
            chapter_plan: 章节规划
            genre: 题材名称
            style_guide: 风格指南
            previous_summaries: 前文摘要
        
        Returns:
            上下文字典
        """
        # 加载真相文件
        self.truth_files.load_all()
        
        # 获取世界状态
        world_state = self.truth_files.get_file("world_state")
        
        # 获取角色矩阵
        character_matrix = self.truth_files.get_file("character_matrix")
        
        # 获取剧情进度
        plot_progress = self.truth_files.get_file("plot_progress")
        
        # 获取伏笔钩子
        foreshadow_hooks = self.truth_files.get_file("foreshadow_hooks")
        
        context = {
            "world_state": world_state,
            "character_matrix": character_matrix,
            "plot_progress": plot_progress,
            "foreshadow_hooks": foreshadow_hooks,
            "style_guide": style_guide or {},
            "previous_summaries": previous_summaries or []
        }
        
        return context
    
    def _build_chapter_prompt(self, chapter_plan: Dict[str, Any],
                             context: Dict[str, Any],
                             taboo_list: List[str],
                             style_guide: Dict[str, Any] = None) -> str:
        """
        构建章节生成Prompt
        
        实现逻辑:
        1. 整合写作规则
        2. 整合上下文信息
        3. 整合题材禁忌
        4. 整合风格指南
        5. 构建完整Prompt
        
        Args:
            chapter_plan: 章节规划
            context: 上下文
            taboo_list: 题材禁忌列表
            style_guide: 风格指南
        
        Returns:
            完整Prompt
        """
        chapter_num = chapter_plan.get("chapter_num", 1)
        chapter_title = chapter_plan.get("chapter_title", f"第{chapter_num}章")
        core_event = chapter_plan.get("core_event", "")
        estimated_words = chapter_plan.get("estimated_words", 3000)
        
        # 整合写作规则
        rules_text = "\n".join(self.WRITING_RULES)
        
        # 整合题材禁忌
        taboo_text = "\n".join([f"- {t}" for t in taboo_list]) if taboo_list else "无"
        
        # 整合上下文
        world_state = context.get("world_state", {})
        character_matrix = context.get("character_matrix", {})
        previous_summaries = context.get("previous_summaries", [])
        
        # 前文摘要
        previous_text = "\n".join([f"第{i+1}章: {s}" for i, s in enumerate(previous_summaries[-3:])]) if previous_summaries else "无"
        
        # 风格指南
        style_text = ""
        if style_guide:
            style_text = f"""
风格要求:
- 文风: {style_guide.get('tone', '未知')}
- 叙事视角: {style_guide.get('pov', '未知')}
- 禁用句式: {', '.join(style_guide.get('forbidden_patterns', []))}
"""
        
        prompt = f"""你是一个专业的网络小说写手。请根据以下信息，生成第{chapter_num}章的正文。

## 写作规则（必须遵守）
{rules_text}

## 题材禁忌（绝对不能违反）
{taboo_text}
{style_text}
## 世界状态
{json.dumps(world_state, ensure_ascii=False, indent=2)}

## 角色矩阵
{json.dumps(character_matrix.get('characters', {}), ensure_ascii=False, indent=2)}

## 前文摘要
{previous_text}

## 本章规划
- 章节号: 第{chapter_num}章
- 章节标题: {chapter_title}
- 核心事件: {core_event}
- 预估字数: {estimated_words}字

## 要求
1. 严格遵循写作规则
2. 绝对不能违反题材禁忌
3. 保持与前文的一致性
4. 字数控制在{estimated_words}字左右
5. 章节结尾要有钩子，吸引读者继续阅读

请直接输出章节正文，不要输出其他内容。"""
        
        return prompt
    
    def get_writing_rules(self) -> List[str]:
        """
        获取25条通用写作规则
        
        Returns:
            写作规则列表
        """
        return self.WRITING_RULES.copy()


# 全局实例
_writer_agent = None


def get_writer_agent() -> WriterAgent:
    """获取全局写手实例（单例模式）"""
    global _writer_agent
    if _writer_agent is None:
        _writer_agent = WriterAgent()
    return _writer_agent
