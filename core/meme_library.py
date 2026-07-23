"""
梗库(MemeLibrary)

核心职责:
- 分类存储各种梗（打脸梗、升级梗、感情梗、悬疑梗等），每类10+变体
- 新鲜度追踪：记录每个梗的使用时间，近期用过的降低优先级
- 梗的组合创新：组合2-3个梗创造新变体

工作流程:
加载梗库数据 → 获取梗 → 追踪新鲜度 → 组合创新

设计思路:
- 使用JSON文件存储梗库数据
- 支持动态添加新梗
- 追踪每个梗的使用时间和章节
- 近期用过的梗降低优先级
- 支持梗的组合创新

输出格式:
{
    "meme": 选择的梗,
    "category": 梗类别,
    "freshness": 新鲜度,
    "combination": 组合创新结果
}
"""

import json
import os
import sys
import random
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class MemeLibrary:
    """
    梗库类
    
    核心功能:
    1. 梗管理：加载、保存、添加梗
    2. 梗获取：按类别获取梗
    3. 新鲜度追踪：记录使用时间和章节
    4. 组合创新：组合多个梗创造新变体
    
    使用场景:
    - 写手生成章节时，获取合适的梗
    - 避免重复使用同一个梗
    - 创造新的梗组合
    
    使用流程:
    1. 初始化时加载梗库数据
    2. 调用get_meme(category)获取梗
    3. 调用track_freshness()追踪新鲜度
    4. 调用suggest_combination()获取组合建议
    """
    
    # 默认梗库数据
    DEFAULT_MEMES = {
        "打脸梗": [
            "反派嘲讽主角无能，结果被主角一招击败",
            "富二代炫耀财富，主角随手拿出更贵的东西",
            "天才嘲笑主角是废物，主角展现更强天赋",
            "长老说主角不可能通过测试，主角不仅通过还打破记录",
            "情敌炫耀自己的优势，主角在关键时刻胜出",
            "老师断定学生没出息，学生后来成为大佬",
            "对手设置陷阱，主角反将一军",
            "众人嘲笑主角的选择，最后证明主角是对的",
            "专家说某事不可能，主角偏偏做到了",
            "敌人以为胜券在握，结果发现中了主角的计"
        ],
        "升级梗": [
            "主角在生死关头突破瓶颈",
            "主角意外获得奇遇，实力大增",
            "主角服用神丹妙药，修为暴涨",
            "主角领悟高深功法，实力飞跃",
            "主角在战斗中顿悟，突破境界",
            "主角获得传承，实力暴增",
            "主角经历磨难，浴火重生",
            "主角融合多种功法，创造新技能",
            "主角在绝境中觉醒特殊能力",
            "主角通过特殊试炼，实力大进"
        ],
        "感情梗": [
            "英雄救美，两人因此结缘",
            "误会解除，感情升温",
            "共同经历生死，感情加深",
            "一方受伤，另一方悉心照料",
            "分离多年，重逢时感情依旧",
            "默默守护，最终感动对方",
            "误会重重，最终真相大白",
            "为对方牺牲，感动天地",
            "青梅竹马，终成眷属",
            "一见钟情，再见倾心"
        ],
        "悬疑梗": [
            "神秘人物突然出现，身份成谜",
            "发现神秘线索，指向更大的阴谋",
            "看似简单的事件背后隐藏秘密",
            "关键人物突然失踪",
            "发现隐藏的密室或宝藏",
            "收到神秘信件或预言",
            "发现身世之谜",
            "看似死去的人重新出现",
            "发现组织内部的叛徒",
            "揭开历史真相的一角"
        ],
        "日常梗": [
            "主角做饭意外好吃，惊艳众人",
            "主角逛街遇到有趣的事",
            "主角参加比赛，轻松获胜",
            "主角帮助路人，获得好人卡",
            "主角睡觉被吵醒，发现大事发生",
            "主角购物时遇到打折，捡到便宜",
            "主角无聊时发明新东西",
            "主角和朋友聚会，发生趣事",
            "主角养宠物，宠物特别聪明",
            "主角学习新技能，快速掌握"
        ],
        "反转梗": [
            "看似好人其实是反派",
            "看似弱者其实是高手",
            "看似失败其实是胜利",
            "看似死亡其实是假死",
            "看似敌人其实是盟友",
            "看似绝境其实是机遇",
            "看似普通物品其实是神器",
            "看似简单任务其实是陷阱",
            "看似偶然其实是必然",
            "看似结束其实是开始"
        ]
    }
    
    def __init__(self):
        """
        初始化梗库
        
        初始化流程:
        1. 加载梗库数据
        2. 初始化使用记录
        """
        self.memes = self._load_memes()
        self.usage_records = {}  # 梗使用记录
    
    def _load_memes(self) -> Dict[str, List[str]]:
        """
        加载梗库数据
        
        Returns:
            梗库字典
        """
        memes_file = os.path.join(config.DATA_DIR, "meme_library.json")
        
        if os.path.exists(memes_file):
            try:
                with open(memes_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载梗库数据失败: {e}")
                return self.DEFAULT_MEMES.copy()
        else:
            # 创建默认数据文件
            self._save_memss(self.DEFAULT_MEMES)
            return self.DEFAULT_MEMES.copy()
    
    def _save_memss(self, memes: Dict[str, List[str]]):
        """
        保存梗库数据到JSON文件
        
        Args:
            memes: 梗库字典
        """
        memes_file = os.path.join(config.DATA_DIR, "meme_library.json")
        os.makedirs(os.path.dirname(memes_file), exist_ok=True)
        
        try:
            with open(memes_file, 'w', encoding='utf-8') as f:
                json.dump(memes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存梗库数据失败: {e}")
    
    def get_meme(self, category: str, chapter_num: int = None) -> Dict[str, Any]:
        """
        获取梗（按类别）
        
        实现逻辑:
        1. 获取该类别的所有梗
        2. 根据新鲜度选择梗（近期用过的降低优先级）
        3. 随机选择一个梗
        4. 记录使用
        
        Args:
            category: 梗类别
            chapter_num: 当前章节号（可选）
        
        Returns:
            梗结果字典
        """
        memes_list = self.memes.get(category, [])
        
        if not memes_list:
            return {
                "category": category,
                "meme": None,
                "freshness": 0,
                "note": "该类别无梗"
            }
        
        # 根据新鲜度选择（近期用过的降低优先级）
        weighted_memes = []
        for meme in memes_list:
            freshness = self._calculate_freshness(meme, chapter_num)
            # 新鲜度越高，权重越大
            weight = freshness
            weighted_memes.extend([meme] * max(1, int(weight * 10)))
        
        # 随机选择一个梗
        selected_meme = random.choice(weighted_memes) if weighted_memes else random.choice(memes_list)
        
        # 记录使用
        if chapter_num is not None:
            self.track_freshness(selected_meme, chapter_num)
        
        freshness = self._calculate_freshness(selected_meme, chapter_num)
        
        return {
            "category": category,
            "meme": selected_meme,
            "freshness": freshness,
            "alternatives": [m for m in memes_list if m != selected_meme][:3]
        }
    
    def _calculate_freshness(self, meme: str, current_chapter: int = None) -> float:
        """
        计算梗的新鲜度
        
        实现逻辑:
        1. 获取梗的使用记录
        2. 计算距离上次使用的章节数
        3. 章节数越大，新鲜度越高
        
        Args:
            meme: 梗内容
            current_chapter: 当前章节号
        
        Returns:
            新鲜度（0-1之间）
        """
        if current_chapter is None:
            return 1.0
        
        usage_record = self.usage_records.get(meme, {})
        last_used_chapter = usage_record.get("last_used_chapter", 0)
        
        if last_used_chapter == 0:
            return 1.0  # 从未使用过，新鲜度最高
        
        # 计算章节差
        chapter_diff = current_chapter - last_used_chapter
        
        # 新鲜度随章节差增加而增加
        # 使用config.MEME_STALE_THRESHOLD作为阈值
        freshness = min(1.0, chapter_diff / config.MEME_STALE_THRESHOLD)
        
        return freshness
    
    def track_freshness(self, meme: str, chapter_num: int):
        """
        追踪梗的新鲜度（记录使用）
        
        Args:
            meme: 梗内容
            chapter_num: 章节号
        """
        if meme not in self.usage_records:
            self.usage_records[meme] = {}
        
        self.usage_records[meme]["last_used_chapter"] = chapter_num
        self.usage_records[meme]["last_used_time"] = datetime.now().isoformat()
        self.usage_records[meme]["usage_count"] = self.usage_records[meme].get("usage_count", 0) + 1
    
    def suggest_combination(self, categories: List[str] = None) -> Dict[str, Any]:
        """
        建议梗的组合创新
        
        实现逻辑:
        1. 从指定类别中各选择一个梗
        2. 组合2-3个梗创造新变体
        3. 使用LLM生成组合后的梗
        
        Args:
            categories: 梗类别列表（默认选择2-3个类别）
        
        Returns:
            组合建议字典
        """
        if categories is None:
            # 随机选择2-3个类别
            all_categories = list(self.memes.keys())
            num_categories = random.randint(2, min(3, len(all_categories)))
            categories = random.sample(all_categories, num_categories)
        
        # 从每个类别选择一个梗
        selected_memes = []
        for category in categories:
            meme_result = self.get_meme(category)
            if meme_result.get("meme"):
                selected_memes.append({
                    "category": category,
                    "meme": meme_result["meme"]
                })
        
        if len(selected_memes) < 2:
            return {
                "combination": None,
                "note": "无法组合，梗数量不足"
            }
        
        # 使用LLM生成组合后的梗
        combination_prompt = f"""请将以下{len(selected_memes)}个梗组合成一个新的梗：

"""
        for i, meme_info in enumerate(selected_memes, 1):
            combination_prompt += f"{i}. [{meme_info['category']}] {meme_info['meme']}\n"
        
        combination_prompt += """
请创造一个新的梗，要求：
1. 融合所有梗的特点
2. 有创新性
3. 具体可执行
4. 符合网络小说风格

请用一句话描述组合后的新梗。"""
        
        try:
            from utils.llm_client import get_llm_client
            llm_client = get_llm_client()
            combination = llm_client.generate(combination_prompt)
            
            return {
                "combination": combination.strip(),
                "source_memes": selected_memes,
                "categories": categories
            }
        except Exception as e:
            print(f"梗组合失败: {e}")
            return {
                "combination": None,
                "source_memes": selected_memes,
                "note": f"组合失败: {e}"
            }
    
    def add_meme(self, category: str, new_meme: str) -> bool:
        """
        添加新梗
        
        Args:
            category: 梗类别
            new_meme: 新梗内容
        
        Returns:
            是否添加成功
        """
        if category not in self.memes:
            self.memes[category] = []
        
        if new_meme not in self.memes[category]:
            self.memes[category].append(new_meme)
            self._save_memss(self.memes)
            return True
        
        return False
    
    def get_all_memes(self) -> Dict[str, List[str]]:
        """
        获取所有梗
        
        Returns:
            梗库字典
        """
        return self.memes.copy()
    
    def get_categories(self) -> List[str]:
        """
        获取所有梗类别
        
        Returns:
            类别列表
        """
        return list(self.memes.keys())


# 全局实例
_meme_library = None


def get_meme_library() -> MemeLibrary:
    """获取全局梗库实例（单例模式）"""
    global _meme_library
    if _meme_library is None:
        _meme_library = MemeLibrary()
    return _meme_library
