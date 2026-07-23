"""
用户画像系统模块

核心职责：
- 持续学习和记录用户的写作偏好、习惯和满意度
- 管理用户的修改历史，分析修改模式以改进生成质量
- 提供用户画像查询接口，为个性化生成提供数据支撑
- 支持风格学习器，适应用户的写作风格偏好

设计思路：
- 用户画像持久化到JSON文件，支持跨会话访问
- 偏好管理采用分类+权重机制，支持多级偏好（如：题材偏好权重0.8，风格偏好权重0.6）
- 修改历史记录用户对所有内容的修改，用于分析用户的修改模式（如：经常修改对话风格、经常修改剧情节奏等）
- 满意度日志记录用户对每章的满意度评分，用于统计和改进
- 写作习惯记录用户的词汇偏好、句式结构、对话风格等

使用场景：
- StyleEngineer优化文风时，查询用户偏好和写作习惯
- Writer Agent生成章节时，参考用户画像调整生成策略
- 用户修改内容后，调用record_modification()记录修改
- 用户对章节评分后，调用record_satisfaction()记录满意度

关键算法：
- 偏好更新：使用指数加权平均，新偏好值 = 旧值 * (1 - weight) + 新值 * weight
- 修改模式分析：统计修改原因的出现频率，识别用户的常见修改模式
- 满意度统计：计算最近N章的平均满意度，以及各方面（剧情/人物/风格/节奏）的平均分
"""
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class UserProfile:
    """
    用户画像管理器
    
    核心功能：
    1. 偏好管理：记录和查询用户的题材、风格、节奏等偏好
    2. 写作习惯：学习用户的词汇偏好、句式结构、对话风格
    3. 修改历史：记录用户对所有内容的修改，分析修改模式
    4. 满意度日志：记录用户对每章的满意度评分
    5. 综合查询：提供完整的用户画像和学习摘要
    
    设计特点：
    - 偏好采用分类+权重机制，支持多级偏好
    - 修改历史限制为最近20条，避免文件过大
    - 满意度日志限制为最近10条，平衡数据量和统计价值
    - 提供修改模式分析，识别用户的常见修改原因
    
    使用流程：
    1. 初始化时自动加载用户画像（_load_profile）
    2. 用户表达偏好时调用update_preference()
    3. 用户修改内容时调用record_modification()
    4. 用户评分时调用record_satisfaction()
    5. 需要个性化生成时调用get_profile()或get_learning_summary()
    """
    
    def __init__(self):
        """初始化用户画像"""
        self.profile_file = config.USER_PROFILE_FILE
        self.profile = self._load_profile()
    
    def _load_profile(self) -> Dict[str, Any]:
        """加载用户画像"""
        if os.path.exists(self.profile_file):
            try:
                with open(self.profile_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # 默认画像结构
        return {
            "preferences": {},
            "writing_habits": {},
            "modification_history": [],
            "satisfaction_log": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    
    def _save_profile(self) -> None:
        """保存用户画像"""
        self.profile["updated_at"] = datetime.now().isoformat()
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.profile_file), exist_ok=True)
        
        with open(self.profile_file, 'w', encoding='utf-8') as f:
            json.dump(self.profile, f, ensure_ascii=False, indent=2)
    
    # ========== 偏好管理 ==========
    
    def update_preference(self, category: str, value: Any, weight: float = 1.0) -> None:
        """更新用户偏好
        
        Args:
            category: 偏好类别（genre/style/pacing/character_type等）
            value: 偏好值
            weight: 权重（0-1，用于多级偏好）
        """
        if category not in self.profile["preferences"]:
            self.profile["preferences"][category] = {
                "value": value,
                "weight": weight,
                "update_count": 0,
                "last_updated": datetime.now().isoformat()
            }
        else:
            # 更新现有偏好
            pref = self.profile["preferences"][category]
            pref["value"] = value
            pref["weight"] = max(0.1, min(1.0, weight))
            pref["update_count"] += 1
            pref["last_updated"] = datetime.now().isoformat()
        
        self._save_profile()
    
    def get_preference(self, category: str, default: Any = None) -> Any:
        """获取用户偏好
        
        Args:
            category: 偏好类别
            default: 默认值
        
        Returns:
            偏好值
        """
        pref = self.profile["preferences"].get(category)
        if pref:
            return pref["value"]
        return default
    
    def get_all_preferences(self) -> Dict[str, Any]:
        """获取所有偏好"""
        return {k: v["value"] for k, v in self.profile["preferences"].items()}
    
    # ========== 写作习惯 ==========
    
    def update_habit(self, habit_type: str, data: Dict[str, Any]) -> None:
        """更新写作习惯
        
        Args:
            habit_type: 习惯类型（vocabulary/sentence_structure/dialogue_style等）
            data: 习惯数据
        """
        if habit_type not in self.profile["writing_habits"]:
            self.profile["writing_habits"][habit_type] = {
                "data": data,
                "sample_count": 0,
                "last_updated": datetime.now().isoformat()
            }
        
        habit = self.profile["writing_habits"][habit_type]
        habit["data"] = data
        habit["sample_count"] += 1
        habit["last_updated"] = datetime.now().isoformat()
        
        self._save_profile()
    
    def get_habit(self, habit_type: str) -> Optional[Dict[str, Any]]:
        """获取写作习惯
        
        Args:
            habit_type: 习惯类型
        
        Returns:
            习惯数据
        """
        habit = self.profile["writing_habits"].get(habit_type)
        if habit:
            return habit["data"]
        return None
    
    def get_all_habits(self) -> Dict[str, Any]:
        """获取所有写作习惯"""
        return {k: v["data"] for k, v in self.profile["writing_habits"].items()}
    
    # ========== 修改历史 ==========
    
    def record_modification(self, chapter_num: int, original: str, modified: str, 
                           reason: str = "", context: str = "") -> None:
        """记录用户修改
        
        Args:
            chapter_num: 章节号
            original: 原始内容
            modified: 修改后内容
            reason: 修改原因
            context: 修改上下文
        """
        modification = {
            "chapter_num": chapter_num,
            "original": original[:200],  # 只保存前200字符
            "modified": modified[:200],
            "reason": reason,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
        
        self.profile["modification_history"].append(modification)
        
        # 限制历史记录数量（最多保留20条）
        if len(self.profile["modification_history"]) > 20:
            self.profile["modification_history"] = self.profile["modification_history"][-20:]
        
        self._save_profile()
    
    def get_modifications(self, chapter_num: int = None, limit: int = 10) -> List[Dict[str, Any]]:
        """获取修改记录
        
        Args:
            chapter_num: 章节号（可选，不传则返回全部）
            limit: 返回条数
        
        Returns:
            修改记录列表
        """
        if chapter_num:
            mods = [m for m in self.profile["modification_history"] 
                    if m["chapter_num"] == chapter_num]
        else:
            mods = self.profile["modification_history"]
        
        return mods[-limit:]
    
    def get_modification_patterns(self) -> Dict[str, int]:
        """获取修改模式统计"""
        patterns = {}
        
        for mod in self.profile["modification_history"]:
            reason = mod.get("reason", "未说明")
            patterns[reason] = patterns.get(reason, 0) + 1
        
        return patterns
    
    # ========== 满意度日志 ==========
    
    def record_satisfaction(self, chapter_num: int, satisfaction: float, 
                           feedback: str = "", aspects: Dict[str, float] = None) -> None:
        """记录用户满意度
        
        Args:
            chapter_num: 章节号
            satisfaction: 总体满意度（0-1）
            feedback: 用户反馈
            aspects: 各方面满意度（plot/character/style/pacing等）
        """
        record = {
            "chapter_num": chapter_num,
            "satisfaction": satisfaction,
            "feedback": feedback,
            "aspects": aspects or {},
            "timestamp": datetime.now().isoformat()
        }
        
        self.profile["satisfaction_log"].append(record)
        
        # 限制日志数量（最多保留100条）
        if len(self.profile["satisfaction_log"]) > 10:
            self.profile["satisfaction_log"] = self.profile["satisfaction_log"][-10:]
        
        self._save_profile()
    
    def get_satisfaction_stats(self, recent_n: int = 10) -> Dict[str, Any]:
        """获取满意度统计
        
        Args:
            recent_n: 统计最近N章
        
        Returns:
            满意度统计信息
        """
        recent_logs = self.profile["satisfaction_log"][-recent_n:]
        
        if not recent_logs:
            return {
                "avg_satisfaction": 0,
                "total_records": 0,
                "aspect_averages": {}
            }
        
        # 计算平均满意度
        avg_satisfaction = sum(r["satisfaction"] for r in recent_logs) / len(recent_logs)
        
        # 计算各方面平均满意度
        aspect_sums = {}
        aspect_counts = {}
        
        for record in recent_logs:
            for aspect, score in record.get("aspects", {}).items():
                aspect_sums[aspect] = aspect_sums.get(aspect, 0) + score
                aspect_counts[aspect] = aspect_counts.get(aspect, 0) + 1
        
        aspect_averages = {
            aspect: aspect_sums[aspect] / aspect_counts[aspect]
            for aspect in aspect_sums
        }
        
        return {
            "avg_satisfaction": avg_satisfaction,
            "total_records": len(recent_logs),
            "aspect_averages": aspect_averages
        }
    
    # ========== 综合查询 ==========
    
    def get_profile(self) -> Dict[str, Any]:
        """获取完整用户画像"""
        return {
            "preferences": self.get_all_preferences(),
            "writing_habits": self.get_all_habits(),
            "recent_modifications": self.get_modifications(limit=5),
            "satisfaction_stats": self.get_satisfaction_stats(),
            "modification_patterns": self.get_modification_patterns()
        }
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """获取学习摘要（用于风格学习器）"""
        return {
            "preferred_genres": [self.get_preference("genre")],
            "preferred_styles": [self.get_preference("style")],
            "common_modifications": self.get_modification_patterns(),
            "avg_satisfaction": self.get_satisfaction_stats()["avg_satisfaction"],
            "writing_habits": self.get_all_habits()
        }
    
    def reset(self) -> None:
        """重置用户画像"""
        self.profile = {
            "preferences": {},
            "writing_habits": {},
            "modification_history": [],
            "satisfaction_log": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self._save_profile()
