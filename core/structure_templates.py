"""
结构模板库(StructureTemplates)

核心职责:
- 维护章节结构模板（正叙型、倒叙型、多线型、悬念型、日常型、战斗型）
- 章节节奏变化规则（连续2章快节奏→第3章慢节奏缓冲）
- 结尾钩子多样性（悬念型、反转型、情感型、预兆型、循环型）

工作流程:
加载模板数据 → 获取模板 → 检查节奏平衡 → 获取结尾钩子

设计思路:
- 使用JSON文件存储模板数据
- 支持动态添加新模板
- 追踪最近章节的节奏类型
- 自动建议节奏调整
- 提供多种结尾钩子类型

输出格式:
{
    "template": 选择的模板,
    "template_type": 模板类型,
    "structure": 结构描述,
    "ending_hook": 结尾钩子
}
"""

import json
import os
import sys
import random
from typing import Dict, List, Any, Optional
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class StructureTemplates:
    """
    结构模板库类
    
    核心功能:
    1. 模板管理：加载、保存、添加模板
    2. 模板获取：按类型获取模板
    3. 节奏检查：检查最近章节的节奏平衡
    4. 结尾钩子：提供多种结尾钩子类型
    
    使用场景:
    - 写手生成章节时，选择合适的结构模板
    - 保持章节节奏的多样性
    - 提供丰富的结尾钩子
    
    使用流程:
    1. 初始化时加载模板数据
    2. 调用get_template(template_type)获取模板
    3. 调用check_rhythm_balance(recent_chapters)检查节奏
    4. 调用get_ending_hook_type()获取结尾钩子
    """
    
    # 默认模板数据
    DEFAULT_TEMPLATES = {
        "正叙型": {
            "description": "按时间顺序叙述，从起因到结果",
            "structure": [
                "开篇：交代背景和时间",
                "发展：事件逐步推进",
                "高潮：冲突达到顶点",
                "结局：问题解决"
            ],
            "pacing": "中等",
            "suitable_for": ["日常剧情", "成长剧情", "感情发展"]
        },
        "倒叙型": {
            "description": "先展示结果，再回溯原因",
            "structure": [
                "开篇：展示惊人结果",
                "回溯：回到事件起点",
                "发展：揭示事件经过",
                "高潮：解释结果成因"
            ],
            "pacing": "快节奏",
            "suitable_for": ["悬疑剧情", "反转剧情", "揭秘剧情"]
        },
        "多线型": {
            "description": "多条剧情线并行，交替叙述",
            "structure": [
                "线索A：主线剧情推进",
                "线索B：副线剧情推进",
                "交汇：两条线索相遇",
                "高潮：多线汇聚"
            ],
            "pacing": "变化",
            "suitable_for": ["复杂剧情", "群像剧", "多主角"]
        },
        "悬念型": {
            "description": "以悬念为核心，逐步揭示真相",
            "structure": [
                "开篇：抛出悬念",
                "探索：寻找线索",
                "误导：制造假象",
                "揭示：真相大白"
            ],
            "pacing": "慢热",
            "suitable_for": ["悬疑剧情", "推理剧情", "探秘剧情"]
        },
        "日常型": {
            "description": "以日常生活为主，轻松愉快",
            "structure": [
                "开篇：日常场景",
                "事件：小插曲",
                "发展：趣事展开",
                "结局：温馨收尾"
            ],
            "pacing": "慢节奏",
            "suitable_for": ["日常剧情", "轻松剧情", "感情铺垫"]
        },
        "战斗型": {
            "description": "以战斗为核心，节奏紧凑",
            "structure": [
                "开篇：遭遇敌人",
                "试探：初步交锋",
                "激战：全力对战",
                "结局：胜负分晓"
            ],
            "pacing": "快节奏",
            "suitable_for": ["战斗剧情", "对决剧情", "危机剧情"]
        }
    }
    
    # 结尾钩子类型
    ENDING_HOOKS = {
        "悬念型": [
            "突然出现神秘人物",
            "发现意想不到的线索",
            "收到神秘信件或预言",
            "听到奇怪的声音",
            "看到不可思议的景象"
        ],
        "反转型": [
            "看似好人露出真面目",
            "以为胜利却发现是陷阱",
            "死去的人重新出现",
            "信任的人背叛",
            "真相与想象完全相反"
        ],
        "情感型": [
            "主角做出重大决定",
            "感情关系发生变化",
            "角色说出感人的话",
            "面临艰难的选择",
            "回忆起重要的往事"
        ],
        "预兆型": [
            "出现不祥的预兆",
            "感觉到危险临近",
            "收到警告信息",
            "梦境预示未来",
            "占卜显示凶兆"
        ],
        "循环型": [
            "回到故事开始的地方",
            "遇到与开篇相似的场景",
            "历史即将重演",
            "命运的轮回",
            "新的循环即将开始"
        ]
    }
    
    def __init__(self):
        """
        初始化结构模板库
        
        初始化流程:
        1. 加载模板数据
        2. 初始化节奏追踪
        """
        self.templates = self._load_templates()
        self.rhythm_history = []  # 节奏历史记录
    
    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        加载模板数据
        
        Returns:
            模板字典
        """
        templates_file = os.path.join(config.DATA_DIR, "structure_templates.json")
        
        if os.path.exists(templates_file):
            try:
                with open(templates_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载模板数据失败: {e}")
                return self.DEFAULT_TEMPLATES.copy()
        else:
            # 创建默认数据文件
            self._save_templates(self.DEFAULT_TEMPLATES)
            return self.DEFAULT_TEMPLATES.copy()
    
    def _save_templates(self, templates: Dict[str, Dict[str, Any]]):
        """
        保存模板数据到JSON文件
        
        Args:
            templates: 模板字典
        """
        templates_file = os.path.join(config.DATA_DIR, "structure_templates.json")
        os.makedirs(os.path.dirname(templates_file), exist_ok=True)
        
        try:
            with open(templates_file, 'w', encoding='utf-8') as f:
                json.dump(templates, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存模板数据失败: {e}")
    
    def get_template(self, template_type: str = None) -> Dict[str, Any]:
        """
        获取结构模板
        
        实现逻辑:
        1. 如果指定类型，返回该类型模板
        2. 如果未指定，根据节奏平衡选择
        3. 记录选择的模板类型
        
        Args:
            template_type: 模板类型（可选）
        
        Returns:
            模板结果字典
        """
        if template_type and template_type in self.templates:
            template = self.templates[template_type]
        else:
            # 根据节奏平衡选择
            suggested_type = self._suggest_template_type()
            template = self.templates.get(suggested_type, list(self.templates.values())[0])
            template_type = suggested_type
        
        # 记录节奏
        pacing = template.get("pacing", "中等")
        self.rhythm_history.append(pacing)
        
        # 保持历史记录在最近10章
        if len(self.rhythm_history) > 10:
            self.rhythm_history = self.rhythm_history[-10:]
        
        return {
            "template_type": template_type,
            "template": template,
            "description": template.get("description", ""),
            "structure": template.get("structure", []),
            "pacing": pacing
        }
    
    def _suggest_template_type(self) -> str:
        """
        建议模板类型（基于节奏平衡）
        
        实现逻辑:
        1. 统计最近章节的节奏类型
        2. 如果连续多章快节奏，建议慢节奏
        3. 如果连续多章慢节奏，建议快节奏
        
        Returns:
            建议的模板类型
        """
        if len(self.rhythm_history) < 2:
            # 历史不足，随机选择
            return random.choice(list(self.templates.keys()))
        
        # 统计最近节奏
        recent_rhythms = self.rhythm_history[-3:]
        fast_count = recent_rhythms.count("快节奏")
        slow_count = recent_rhythms.count("慢节奏")
        
        # 如果连续快节奏，建议慢节奏
        if fast_count >= 2:
            # 选择慢节奏模板
            slow_templates = [t for t, data in self.templates.items() 
                            if data.get("pacing") == "慢节奏"]
            if slow_templates:
                return random.choice(slow_templates)
        
        # 如果连续慢节奏，建议快节奏
        if slow_count >= 2:
            # 选择快节奏模板
            fast_templates = [t for t, data in self.templates.items() 
                            if data.get("pacing") == "快节奏"]
            if fast_templates:
                return random.choice(fast_templates)
        
        # 否则随机选择
        return random.choice(list(self.templates.keys()))
    
    def check_rhythm_balance(self, recent_chapters: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        检查节奏平衡
        
        实现逻辑:
        1. 统计最近章节的节奏类型
        2. 检查是否过于单一
        3. 提供调整建议
        
        Args:
            recent_chapters: 最近章节列表（可选）
        
        Returns:
            节奏检查结果字典
        """
        if recent_chapters:
            # 从章节中提取节奏信息
            rhythms = [ch.get("pacing", "中等") for ch in recent_chapters[-5:]]
        else:
            rhythms = self.rhythm_history[-5:]
        
        if not rhythms:
            return {
                "is_balanced": True,
                "rhythm_distribution": {},
                "suggestion": "章节数不足，无法判断"
            }
        
        # 统计节奏分布
        rhythm_counts = {}
        for rhythm in rhythms:
            rhythm_counts[rhythm] = rhythm_counts.get(rhythm, 0) + 1
        
        # 检查是否过于单一
        is_balanced = True
        suggestion = ""
        
        if len(rhythms) >= 3:
            # 检查最近3章是否都是同一节奏
            if len(set(rhythms[-3:])) == 1:
                is_balanced = False
                last_rhythm = rhythms[-1]
                if last_rhythm == "快节奏":
                    suggestion = "建议下一章使用慢节奏，避免读者疲劳"
                elif last_rhythm == "慢节奏":
                    suggestion = "建议下一章使用快节奏，提升紧张感"
                else:
                    suggestion = "建议变换节奏，保持多样性"
        
        return {
            "is_balanced": is_balanced,
            "rhythm_distribution": rhythm_counts,
            "recent_rhythms": rhythms,
            "suggestion": suggestion
        }
    
    def get_ending_hook_type(self, hook_type: str = None) -> Dict[str, Any]:
        """
        获取结尾钩子
        
        实现逻辑:
        1. 如果指定类型，返回该类型的钩子
        2. 如果未指定，随机选择类型
        3. 从该类型中随机选择一个钩子
        
        Args:
            hook_type: 钩子类型（可选）
        
        Returns:
            结尾钩子结果字典
        """
        if hook_type and hook_type in self.ENDING_HOOKS:
            hooks = self.ENDING_HOOKS[hook_type]
        else:
            # 随机选择类型
            hook_type = random.choice(list(self.ENDING_HOOKS.keys()))
            hooks = self.ENDING_HOOKS[hook_type]
        
        # 随机选择一个钩子
        selected_hook = random.choice(hooks)
        
        return {
            "hook_type": hook_type,
            "hook": selected_hook,
            "alternatives": [h for h in hooks if h != selected_hook][:3]
        }
    
    def add_template(self, template_type: str, template_data: Dict[str, Any]) -> bool:
        """
        添加新模板
        
        Args:
            template_type: 模板类型
            template_data: 模板数据
        
        Returns:
            是否添加成功
        """
        if template_type not in self.templates:
            self.templates[template_type] = template_data
            self._save_templates(self.templates)
            return True
        
        return False
    
    def get_all_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有模板
        
        Returns:
            模板字典
        """
        return self.templates.copy()
    
    def get_template_types(self) -> List[str]:
        """
        获取所有模板类型
        
        Returns:
            类型列表
        """
        return list(self.templates.keys())


# 全局实例
_structure_templates = None


def get_structure_templates() -> StructureTemplates:
    """获取全局结构模板库实例（单例模式）"""
    global _structure_templates
    if _structure_templates is None:
        _structure_templates = StructureTemplates()
    return _structure_templates
