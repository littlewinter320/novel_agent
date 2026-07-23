"""
架构师(SubAgent-Architect)

核心职责:
- 需求澄清:通过结构化提问确认所有关键参数
- 分层大纲生成:总纲层 → 卷纲层 → 弧纲层 → 章节规划
- Compass机制:只详细规划前2卷+当前弧,后续卷保留骨架,每完成一卷自动展开下一卷
- 伏笔规划:每个伏笔必须有埋设章节、触发条件、预计回收章节区间
- 多轮用户确认流程:总纲→卷纲→弧纲→章节规划→伏笔规划
- 局部修改:用户修改某一层时,只重新生成受影响的层级

工作流程:
接收需求+扫榜建议 → 需求澄清 → 总纲 → 卷纲 → 弧纲 → 章节规划 → 伏笔规划 → 用户确认

设计思路:
- 采用"分层规划+逐步细化"的策略
- 每一层都需要用户确认后才进入下一层
- Compass机制避免过早规划,保持灵活性
- 伏笔规划采用"埋设-触发-回收"的三段式结构

关键算法:
- 需求澄清:检测缺失的关键参数,生成提问
- 分层生成:每层基于上一层的结果生成
- Compass滚动:只详细规划前2卷+当前弧
- 伏笔规划:确保每个伏笔有完整的生命周期

输出格式:
{
    "master_outline": 总纲,
    "volume_outlines": [卷纲列表],
    "arc_outlines": [弧纲列表],
    "chapter_plans": [章节规划列表],
    "foreshadow_plans": [伏笔规划列表]
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


class ArchitectAgent:
    """
    架构师类
    
    核心功能:
    1. 需求澄清:检测缺失参数,生成结构化提问
    2. 分层大纲生成:总纲→卷纲→弧纲→章节规划
    3. Compass滚动规划:只详细规划前2卷+当前弧
    4. 伏笔规划:每个伏笔有埋设章节、触发条件、预计回收章节区间
    5. 多轮用户确认:每层都需要用户确认
    6. 局部修改:修改某一层时只重新生成受影响的部分
    
    使用场景:
    - 用户确定了题材,需要规划整体大纲
    - 用户需要细化某一层的大纲
    - 用户需要调整伏笔规划
    
    使用流程:
    1. 调用clarify_requirements(user_input)检测缺失参数
    2. 如果有缺失,返回提问让用户补充
    3. 参数完整后,调用generate_master_outline()生成总纲
    4. 用户确认总纲后,调用generate_volume_outlines()生成卷纲
    5. 用户确认卷纲后,调用generate_arc_outlines()生成弧纲
    6. 用户确认弧纲后,调用generate_chapter_plans()生成章节规划
    7. 最后调用generate_foreshadow_plans()生成伏笔规划
    """
    
    def __init__(self):
        """
        初始化架构师
        
        初始化流程:
        1. 获取LLM客户端(用于生成大纲)
        2. 获取题材知识库实例(用于查询题材规范)
        3. 初始化规划状态(记录当前规划到哪一层)
        4. 初始化规划缓存(避免重复生成)
        """
        self.llm_client = get_llm_client()
        self.genre_knowledge_base = get_genre_knowledge_base()
        self._planning_state = {
            "current_level": None,  # master/volume/arc/chapter/foreshadow
            "requirements": {},
            "master_outline": None,
            "volume_outlines": [],
            "arc_outlines": [],
            "chapter_plans": [],
            "foreshadow_plans": []
        }
    
    def clarify_requirements(self, user_input: str, genre: str) -> Dict[str, Any]:
        """
        需求澄清:检测缺失的关键参数,生成结构化提问
        
        实现逻辑:
        1. 定义必需参数列表(题材、主角类型、核心冲突、目标读者等)
        2. 从用户输入中提取已有参数
        3. 检测缺失的参数
        4. 为每个缺失参数生成提问(包含[A][B][C][D]其他选项)
        
        必需参数:
        - genre: 题材(已提供)
        - protagonist_type: 主角类型(如"废柴逆袭"、"天才流"等)
        - core_conflict: 核心冲突(如"复仇"、"成长"、"探索"等)
        - target_audience: 目标读者(如"男频"、"女频")
        - tone: 基调(如"轻松"、"热血"、"黑暗"等)
        - estimated_chapters: 预估章节数
        
        Args:
            user_input: 用户输入文本
            genre: 题材名称
        
        Returns:
            澄清结果字典,包含:
            - complete: bool - 参数是否完整
            - extracted_params: dict - 已提取的参数
            - missing_params: list - 缺失的参数列表
            - questions: list - 生成的提问列表
        """
        # 定义必需参数
        required_params = [
            "protagonist_type",  # 主角类型
            "core_conflict",     # 核心冲突
            "target_audience",   # 目标读者
            "tone",              # 基调
            "estimated_chapters" # 预估章节数
        ]
        
        # 从用户输入中提取参数(使用LLM辅助)
        extracted_params = self._extract_parameters(user_input, genre)
        
        # 检测缺失参数
        missing_params = [p for p in required_params if p not in extracted_params]
        
        # 如果参数完整,直接返回
        if not missing_params:
            return {
                "complete": True,
                "extracted_params": extracted_params,
                "missing_params": [],
                "questions": []
            }
        
        # 为每个缺失参数生成提问
        questions = []
        for param in missing_params:
            question = self._generate_question_for_param(param, genre)
            questions.append(question)
        
        return {
            "complete": False,
            "extracted_params": extracted_params,
            "missing_params": missing_params,
            "questions": questions
        }
    
    def _extract_parameters(self, user_input: str, genre: str) -> Dict[str, Any]:
        """
        从用户输入中提取参数(使用LLM辅助)
        
        实现逻辑:
        1. 构造提示词,要求LLM从用户输入中提取关键参数
        2. 调用LLM生成参数字典
        3. 解析JSON格式结果
        
        Args:
            user_input: 用户输入文本
            genre: 题材名称
        
        Returns:
            提取的参数字典
        """
        prompt = f"""从以下用户输入中提取小说创作的关键参数。

用户输入:{user_input}

题材:{genre}

请提取以下参数(如果用户未提及,不要猜测,留空即可):
- protagonist_type: 主角类型(如"废柴逆袭"、"天才流"、"重生复仇"等)
- core_conflict: 核心冲突(如"复仇"、"成长"、"探索"、"争霸"等)
- target_audience: 目标读者(如"男频"、"女频")
- tone: 基调(如"轻松"、"热血"、"黑暗"、"温馨"等)
- estimated_chapters: 预估章节数(数字)

请以JSON格式返回,格式如下:
{{
    "protagonist_type": "主角类型",
    "core_conflict": "核心冲突",
    "target_audience": "目标读者",
    "tone": "基调",
    "estimated_chapters": 章节数
}}

只返回JSON对象,不要其他内容。如果某个参数未提及,不要包含在JSON中。"""
        
        try:
            response = self.llm_client.generate(prompt)
            params = json.loads(response)
            # 过滤空值
            return {k: v for k, v in params.items() if v}
        except Exception as e:
            print(f"提取参数失败: {e}")
            return {}
    
    def _generate_question_for_param(self, param: str, genre: str) -> Dict[str, Any]:
        """
        为缺失参数生成提问(包含选项)
        
        实现逻辑:
        1. 根据参数类型,生成对应的提问文本
        2. 为每个参数提供3个常见选项 + 1个"其他"选项
        3. 返回提问字典
        
        Args:
            param: 参数名称
            genre: 题材名称
        
        Returns:
            提问字典,包含question和options
        """
        # 参数提问模板
        question_templates = {
            "protagonist_type": {
                "question": "请选择主角类型:",
                "options": [
                    "[A] 废柴逆袭(主角从弱到强,逐步成长)",
                    "[B] 天才流(主角天赋异禀,一路碾压)",
                    "[C] 重生复仇(主角重生回到过去,复仇逆袭)",
                    "[D] 其他(请输入你的想法)"
                ]
            },
            "core_conflict": {
                "question": "请选择核心冲突:",
                "options": [
                    "[A] 复仇(主角为复仇而战斗)",
                    "[B] 成长(主角不断成长,突破自我)",
                    "[C] 探索(主角探索未知世界)",
                    "[D] 其他(请输入你的想法)"
                ]
            },
            "target_audience": {
                "question": "请选择目标读者:",
                "options": [
                    "[A] 男频(面向男性读者)",
                    "[B] 女频(面向女性读者)",
                    "[C] 通用(男女读者都适合)",
                    "[D] 其他(请输入你的想法)"
                ]
            },
            "tone": {
                "question": "请选择小说基调:",
                "options": [
                    "[A] 轻松幽默(轻松愉快的氛围)",
                    "[B] 热血激昂(激情澎湃的战斗)",
                    "[C] 黑暗深沉(压抑沉重的氛围)",
                    "[D] 其他(请输入你的想法)"
                ]
            },
            "estimated_chapters": {
                "question": "请选择预估章节数:",
                "options": [
                    "[A] 短篇(50章以内)",
                    "[B] 中篇(50-250章)",
                    "[C] 长篇(250以上章)",
                    "[D] 其他(请输入你的想法)"
                ]
            }
        }
        
        return question_templates.get(param, {
            "question": f"请提供{param}:",
            "options": ["[A] 选项1", "[B] 选项2", "[C] 选项3", "[D] 其他"]
        })
    
    def generate_master_outline(self, requirements: Dict[str, Any], 
                               scout_suggestions: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        生成总纲(整体剧情走向)
        
        实现逻辑:
        1. 结合用户需求和扫榜建议
        2. 使用LLM生成总纲(起承转合四幕结构)
        3. 总纲包含:核心设定、主线剧情、主要角色、结局走向
        
        Args:
            requirements: 用户需求参数
            scout_suggestions: 扫榜分析师的建议(可选)
        
        Returns:
            总纲字典
        """
        genre = requirements.get("genre", "未知")
        
        # 获取题材知识库信息
        genre_info = self.genre_knowledge_base.get_genre(genre)
        plot_systems = genre_info.get("plot_systems", []) if genre_info else []
        
        # 构造扫榜建议文本
        scout_text = ""
        if scout_suggestions:
            outline = scout_suggestions.get("recommended_outline", {})
            if outline:
                scout_text = f"\n扫榜建议的总纲:\n{outline.get('master_outline', '')}"
        
        # 构造提示词
        prompt = f"""基于以下信息,为{genre}题材的小说生成总纲(整体剧情走向)。

用户需求:
- 主角类型:{requirements.get('protagonist_type', '未知')}
- 核心冲突:{requirements.get('core_conflict', '未知')}
- 目标读者:{requirements.get('target_audience', '未知')}
- 基调:{requirements.get('tone', '未知')}
- 预估章节数:{requirements.get('estimated_chapters', '未知')}

题材经典剧情体系:
{chr(10).join([f'- {p}' for p in plot_systems[:3]])}
{scout_text}

请生成总纲,包含以下内容:
1. 核心设定:世界观、力量体系、核心规则
2. 主线剧情:起承转合四幕结构
   - 起(开篇):主角的初始状态和触发事件
   - 承(发展):主角的成长和冲突升级
   - 转(高潮):最大的危机和转折
   - 合(结局):最终决战和结局
3. 主要角色:主角、重要配角、主要反派
4. 结局走向:HE/BE/OE

请以JSON格式返回,格式如下:
{{
    "core_setting": "核心设定描述",
    "main_plot": {{
        "act_1_start": "起(开篇)描述",
        "act_2_develop": "承(发展)描述",
        "act_3_turn": "转(高潮)描述",
        "act_4_end": "合(结局)描述"
    }},
    "main_characters": ["主角", "配角1", "配角2", "反派"],
    "ending_direction": "结局走向"
}}

只返回JSON对象,不要其他内容。"""
        
        try:
            response = self.llm_client.generate(prompt)
            master_outline = json.loads(response)
            self._planning_state["master_outline"] = master_outline
            self._planning_state["current_level"] = "master"
            return master_outline
        except Exception as e:
            print(f"生成总纲失败: {e}")
            return {}
    
    def generate_volume_outlines(self, master_outline: Dict[str, Any], 
                                total_volumes: int = 3) -> List[Dict[str, Any]]:
        """
        生成卷纲(每卷的核心事件和目标)
        
        实现逻辑:
        1. 基于总纲的主线剧情,将故事分为多卷
        2. Compass机制:只详细规划前2卷,后续卷保留骨架
        3. 每卷包含:卷名、核心事件、目标、预估章节数
        
        Compass机制说明:
        - 前2卷:详细规划(包含核心事件、目标、关键转折)
        - 第3卷及以后:只保留骨架(卷名、预估章节数、大致目标)
        
        Args:
            master_outline: 总纲
            total_volumes: 总卷数(根据预估章节数计算,默认3卷)
        
        Returns:
            卷纲列表
        """
        # 构造提示词
        prompt = f"""基于以下总纲,生成{total_volumes}卷的卷纲。

总纲:
{json.dumps(master_outline, ensure_ascii=False, indent=2)}

Compass机制说明:
- 前2卷:详细规划(包含核心事件、目标、关键转折)
- 第3卷及以后:只保留骨架(卷名、预估章节数、大致目标)

请生成{total_volumes}卷的卷纲。

前2卷请以详细JSON格式返回,第3卷及以后以简略JSON格式返回。

详细格式(前2卷):
{{
    "volume_num": 卷号,
    "volume_name": "卷名",
    "core_events": ["核心事件1", "核心事件2"],
    "goal": "本卷目标",
    "key_turning_point": "关键转折",
    "estimated_chapters": 预估章节数
}}

简略格式(第3卷及以后):
{{
    "volume_num": 卷号,
    "volume_name": "卷名",
    "estimated_chapters": 预估章节数,
    "rough_goal": "大致目标"
}}

请以JSON数组格式返回所有卷纲,不要其他内容。"""
        
        try:
            response = self.llm_client.generate(prompt)
            volume_outlines = json.loads(response)
            self._planning_state["volume_outlines"] = volume_outlines
            self._planning_state["current_level"] = "volume"
            return volume_outlines
        except Exception as e:
            print(f"生成卷纲失败: {e}")
            return []
    
    def generate_arc_outlines(self, volume_outline: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        生成弧纲(每卷内的小高潮设计)
        
        实现逻辑:
        1. 基于单卷的详细规划,将该卷分为多个弧(小高潮)
        2. 每个弧包含:弧名、核心冲突、高潮设计、预估章节数
        3. Compass机制:只详细规划当前弧,后续弧保留骨架
        
        Args:
            volume_outline: 单卷的详细卷纲
        
        Returns:
            弧纲列表
        """
        volume_name = volume_outline.get("volume_name", "未知卷")
        core_events = volume_outline.get("core_events", [])
        
        # 构造提示词
        prompt = f"""基于以下卷纲,将该卷分为3-5个弧(小高潮)。

卷纲:
{json.dumps(volume_outline, ensure_ascii=False, indent=2)}

Compass机制说明:
- 第1个弧:详细规划(包含核心冲突、高潮设计、关键转折)
- 后续弧:只保留骨架(弧名、预估章节数、大致冲突)

请生成3-5个弧纲。

第1个弧详细格式:
{{
    "arc_num": 1,
    "arc_name": "弧名",
    "core_conflict": "核心冲突",
    "climax_design": "高潮设计",
    "key_turning_point": "关键转折",
    "estimated_chapters": 预估章节数
}}

后续弧简略格式:
{{
    "arc_num": 弧号,
    "arc_name": "弧名",
    "estimated_chapters": 预估章节数,
    "rough_conflict": "大致冲突"
}}

请以JSON数组格式返回所有弧纲,不要其他内容。"""
        
        try:
            response = self.llm_client.generate(prompt)
            arc_outlines = json.loads(response)
            self._planning_state["arc_outlines"] = arc_outlines
            self._planning_state["current_level"] = "arc"
            return arc_outlines
        except Exception as e:
            print(f"生成弧纲失败: {e}")
            return []
    
    def generate_chapter_plans(self, arc_outline: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        生成章节规划(每章的核心事件)
        
        实现逻辑:
        1. 基于单个弧的详细规划,将该弧分为多个章节
        2. 每章包含:章节号、章节标题、核心事件、字数预估
        3. 确保章节之间有连贯性和节奏感
        
        Args:
            arc_outline: 单个弧的详细弧纲
        
        Returns:
            章节规划列表
        """
        arc_name = arc_outline.get("arc_name", "未知弧")
        estimated_chapters = arc_outline.get("estimated_chapters", 10)
        
        # 构造提示词
        prompt = f"""基于以下弧纲,生成{estimated_chapters}章的章节规划。

弧纲:
{json.dumps(arc_outline, ensure_ascii=False, indent=2)}

请生成{estimated_chapters}章的章节规划,每章包含:
- 章节号
- 章节标题
- 核心事件(本章发生什么)
- 字数预估(2000-5000字)

请以JSON数组格式返回,格式如下:
[
    {{
        "chapter_num": 1,
        "chapter_title": "章节标题",
        "core_event": "核心事件",
        "estimated_words": 3000
    }},
    ...
]

只返回JSON数组,不要其他内容。"""
        
        try:
            response = self.llm_client.generate(prompt)
            chapter_plans = json.loads(response)
            self._planning_state["chapter_plans"] = chapter_plans
            self._planning_state["current_level"] = "chapter"
            return chapter_plans
        except Exception as e:
            print(f"生成章节规划失败: {e}")
            return []
    
    def generate_foreshadow_plans(self, master_outline: Dict[str, Any], 
                                 volume_outlines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        生成伏笔规划(每个伏笔的生命周期)
        
        实现逻辑:
        1. 基于总纲和卷纲,设计3-5个核心伏笔
        2. 每个伏笔必须包含:
           - 伏笔名称
           - 埋设章节:在哪一章埋下伏笔
           - 触发条件:什么情况下触发(具体可验证的)
           - 预计回收章节区间:在哪一章回收
           - 伏笔内容:伏笔的具体内容
        
        设计原则:
        - 伏笔要有明确的触发条件(不能太模糊)
        - 回收时机要合理(不能太早或太晚)
        - 活跃伏笔不超过5个(避免剧情线过于复杂)
        
        Args:
            master_outline: 总纲
            volume_outlines: 卷纲列表
        
        Returns:
            伏笔规划列表
        """
        # 构造提示词
        prompt = f"""基于以下总纲和卷纲,设计3-5个核心伏笔。

总纲:
{json.dumps(master_outline, ensure_ascii=False, indent=2)}

卷纲:
{json.dumps(volume_outlines[:2], ensure_ascii=False, indent=2)}

请设计3-5个核心伏笔,每个伏笔必须包含:
- 伏笔名称
- 埋设章节:在哪一章埋下伏笔(章节号)
- 触发条件:什么情况下触发(要具体可验证)
- 预计回收章节区间:在哪一章回收(章节号区间)
- 伏笔内容:伏笔的具体内容

设计原则:
- 伏笔要有明确的触发条件
- 回收时机要合理
- 活跃伏笔不超过5个

请以JSON数组格式返回,格式如下:
[
    {{
        "foreshadow_name": "伏笔名称",
        "plant_chapter": 埋设章节号,
        "trigger_condition": "触发条件",
        "resolve_chapter_range": "预计回收章节区间(如10-15)",
        "content": "伏笔内容"
    }},
    ...
]

只返回JSON数组,不要其他内容。"""
        
        try:
            response = self.llm_client.generate(prompt)
            foreshadow_plans = json.loads(response)
            self._planning_state["foreshadow_plans"] = foreshadow_plans
            self._planning_state["current_level"] = "foreshadow"
            return foreshadow_plans
        except Exception as e:
            print(f"生成伏笔规划失败: {e}")
            return []
    
    def update_planning(self, level: str, modifications: Dict[str, Any]) -> Dict[str, Any]:
        """
        局部修改:用户修改某一层时,只重新生成受影响的层级
        
        实现逻辑:
        1. 确定修改的层级(master/volume/arc/chapter/foreshadow)
        2. 根据层级依赖关系,确定需要重新生成的层级
        3. 只重新生成受影响的层级,保留未受影响的部分
        
        层级依赖关系:
        - 修改总纲 → 需要重新生成卷纲、弧纲、章节规划、伏笔规划
        - 修改卷纲 → 需要重新生成该卷的弧纲、章节规划
        - 修改弧纲 → 需要重新生成该弧的章节规划
        - 修改章节规划 → 只重新生成该章节
        - 修改伏笔规划 → 只重新生成伏笔规划
        
        Args:
            level: 修改的层级
            modifications: 修改内容
        
        Returns:
            更新后的规划结果
        """
        # 根据层级确定需要重新生成的部分
        if level == "master":
            # 修改总纲,需要重新生成所有后续层级
            self._planning_state["master_outline"] = modifications
            self._planning_state["volume_outlines"] = []
            self._planning_state["arc_outlines"] = []
            self._planning_state["chapter_plans"] = []
            self._planning_state["foreshadow_plans"] = []
        elif level == "volume":
            # 修改卷纲,需要重新生成该卷的弧纲和章节规划
            volume_num = modifications.get("volume_num")
            self._planning_state["volume_outlines"] = [
                v if v.get("volume_num") != volume_num else modifications
                for v in self._planning_state["volume_outlines"]
            ]
            # 清空该卷的弧纲和章节规划
            self._planning_state["arc_outlines"] = []
            self._planning_state["chapter_plans"] = []
        elif level == "arc":
            # 修改弧纲,需要重新生成该弧的章节规划
            arc_num = modifications.get("arc_num")
            self._planning_state["arc_outlines"] = [
                a if a.get("arc_num") != arc_num else modifications
                for a in self._planning_state["arc_outlines"]
            ]
            # 清空该弧的章节规划
            self._planning_state["chapter_plans"] = []
        elif level == "chapter":
            # 修改章节规划,只重新生成该章节
            chapter_num = modifications.get("chapter_num")
            self._planning_state["chapter_plans"] = [
                c if c.get("chapter_num") != chapter_num else modifications
                for c in self._planning_state["chapter_plans"]
            ]
        elif level == "foreshadow":
            # 修改伏笔规划,只重新生成伏笔规划
            self._planning_state["foreshadow_plans"] = modifications
        
        return self._planning_state
    
    def get_planning_state(self) -> Dict[str, Any]:
        """
        获取当前规划状态
        
        Returns:
            规划状态字典
        """
        return self._planning_state.copy()
    
    def generate_planning_report(self) -> str:
        """
        生成人类可读的规划报告
        
        Returns:
            Markdown格式的规划报告
        """
        report = "# 大纲规划报告\n\n"
        
        # 1. 总纲
        master_outline = self._planning_state.get("master_outline")
        if master_outline:
            report += "## 一、总纲\n\n"
            report += f"### 核心设定\n{master_outline.get('core_setting', '未知')}\n\n"
            report += "### 主线剧情\n"
            main_plot = master_outline.get("main_plot", {})
            report += f"- **起(开篇)**: {main_plot.get('act_1_start', '未知')}\n"
            report += f"- **承(发展)**: {main_plot.get('act_2_develop', '未知')}\n"
            report += f"- **转(高潮)**: {main_plot.get('act_3_turn', '未知')}\n"
            report += f"- **合(结局)**: {main_plot.get('act_4_end', '未知')}\n\n"
            report += f"### 主要角色\n{', '.join(master_outline.get('main_characters', []))}\n\n"
            report += f"### 结局走向\n{master_outline.get('ending_direction', '未知')}\n\n"
        
        # 2. 卷纲
        volume_outlines = self._planning_state.get("volume_outlines", [])
        if volume_outlines:
            report += "## 二、卷纲\n\n"
            for i, volume in enumerate(volume_outlines, 1):
                report += f"### 第{i}卷: {volume.get('volume_name', '未知')}\n"
                if "core_events" in volume:
                    # 详细规划
                    report += f"- **核心事件**: {', '.join(volume.get('core_events', []))}\n"
                    report += f"- **目标**: {volume.get('goal', '未知')}\n"
                    report += f"- **关键转折**: {volume.get('key_turning_point', '未知')}\n"
                else:
                    # 简略规划
                    report += f"- **大致目标**: {volume.get('rough_goal', '未知')}\n"
                report += f"- **预估章节数**: {volume.get('estimated_chapters', '未知')}\n\n"
        
        # 3. 弧纲
        arc_outlines = self._planning_state.get("arc_outlines", [])
        if arc_outlines:
            report += "## 三、弧纲\n\n"
            for i, arc in enumerate(arc_outlines, 1):
                report += f"### 弧{i}: {arc.get('arc_name', '未知')}\n"
                if "core_conflict" in arc:
                    # 详细规划
                    report += f"- **核心冲突**: {arc.get('core_conflict', '未知')}\n"
                    report += f"- **高潮设计**: {arc.get('climax_design', '未知')}\n"
                    report += f"- **关键转折**: {arc.get('key_turning_point', '未知')}\n"
                else:
                    # 简略规划
                    report += f"- **大致冲突**: {arc.get('rough_conflict', '未知')}\n"
                report += f"- **预估章节数**: {arc.get('estimated_chapters', '未知')}\n\n"
        
        # 4. 章节规划
        chapter_plans = self._planning_state.get("chapter_plans", [])
        if chapter_plans:
            report += "## 四、章节规划\n\n"
            for chapter in chapter_plans[:10]:  # 只显示前10章
                report += f"### 第{chapter.get('chapter_num', '?')}章: {chapter.get('chapter_title', '未知')}\n"
                report += f"- **核心事件**: {chapter.get('core_event', '未知')}\n"
                report += f"- **预估字数**: {chapter.get('estimated_words', '未知')}\n\n"
            if len(chapter_plans) > 10:
                report += f"... 还有{len(chapter_plans) - 10}章\n\n"
        
        # 5. 伏笔规划
        foreshadow_plans = self._planning_state.get("foreshadow_plans", [])
        if foreshadow_plans:
            report += "## 五、伏笔规划\n\n"
            for i, foreshadow in enumerate(foreshadow_plans, 1):
                report += f"### 伏笔{i}: {foreshadow.get('foreshadow_name', '未知')}\n"
                report += f"- **埋设章节**: 第{foreshadow.get('plant_chapter', '?')}章\n"
                report += f"- **触发条件**: {foreshadow.get('trigger_condition', '未知')}\n"
                report += f"- **预计回收**: 第{foreshadow.get('resolve_chapter_range', '?')}章\n"
                report += f"- **内容**: {foreshadow.get('content', '未知')}\n\n"
        
        return report


# 全局实例
_architect_agent = None


def get_architect_agent() -> ArchitectAgent:
    """获取全局架构师实例(单例模式)"""
    global _architect_agent
    if _architect_agent is None:
        _architect_agent = ArchitectAgent()
    return _architect_agent
