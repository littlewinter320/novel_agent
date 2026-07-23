"""
三层记忆系统模块

核心职责：
- 实现类人脑的三层记忆架构：热记忆（工作记忆）、温记忆（短期持久化）、冷记忆（长期归档）
- 管理会话内外的上下文连续性，确保跨会话的信息不丢失
- 提供记忆沉淀机制，将重要信息从热记忆转入温/冷记忆
- 支持记忆的检索和查询，为章节生成提供上下文

设计思路：
- 热记忆（Hot Memory）：类似CPU缓存，存储当前会话的对话和决策，速度快但容量有限（最多100条）
- 温记忆（Warm Memory）：类似内存，存储用户画像、知识库索引、Skill索引等跨会话信息，持久化到JSON文件
- 冷记忆（Cold Memory）：类似硬盘，按章节存储历史摘要和关键事件，支持关键词搜索
- 记忆沉淀（settle_memories）：会话结束时，将热记忆中的重要决策转入温记忆，实现信息的层级流转

使用场景：
- MainAgent在每次对话后调用add_hot_memory()记录对话内容
- 会话结束时调用settle_memories()沉淀重要信息
- Writer Agent生成章节时调用get_context_for_generation()获取上下文
- 用户查询历史信息时调用search_cold_memory()搜索冷记忆

关键算法：
- 热记忆限制：使用滑动窗口机制，保留最近100条记录
- 冷记忆搜索：线性扫描所有冷记忆文件，匹配摘要或关键事件中的关键词
- 记忆沉淀：遍历热记忆，提取type为"decision"的记录转入温记忆
"""
import os
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class MemorySystem:
    """
    三层记忆系统管理器
    
    核心功能：
    1. 热记忆管理：存储当前会话的对话、事件、决策（最多100条）
    2. 温记忆管理：存储用户画像、知识库索引、Skill索引、重要决策（持久化）
    3. 冷记忆管理：按章节存储历史摘要和关键事件（文件存储）
    4. 记忆沉淀：会话结束时将热记忆中的重要信息转入温记忆
    5. 上下文查询：为章节生成提供完整的上下文信息
    
    设计特点：
    - 三层架构模拟人脑记忆机制，平衡速度和容量
    - 热记忆使用内存列表，读写速度快
    - 温记忆使用JSON文件持久化，支持跨会话访问
    - 冷记忆按章节分文件存储，便于管理和检索
    - 提供统一的查询接口，屏蔽底层存储细节
    
    使用流程：
    1. 初始化时自动加载温记忆（_load_warm_memory）
    2. 会话过程中通过add_hot_memory()记录对话
    3. 会话结束时调用settle_memories()沉淀重要信息
    4. 需要上下文时调用get_context_for_generation()
    """
    
    def __init__(self):
        """初始化记忆系统"""
        self.hot_memory = []  # 热记忆：当前会话上下文
        self.warm_memory = {}  # 温记忆：跨会话持久化
        self.cold_memory_dir = config.COLD_MEMORY_DIR
        
        # 确保冷记忆目录存在
        os.makedirs(self.cold_memory_dir, exist_ok=True)
        
        # 加载温记忆
        self._load_warm_memory()
    
    # ========== 热记忆操作 ==========
    
    def add_hot_memory(self, content: str, memory_type: str = "dialogue") -> None:
        """添加热记忆
        
        Args:
            content: 记忆内容
            memory_type: 记忆类型（dialogue/event/decision）
        """
        self.hot_memory.append({
            "content": content,
            "type": memory_type,
            "timestamp": datetime.now().isoformat()
        })
        
        # 限制热记忆大小（最多保留100条）
        if len(self.hot_memory) > 100:
            self.hot_memory = self.hot_memory[-100:]
    
    def get_hot_memory(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的热记忆
        
        Args:
            limit: 返回条数
        
        Returns:
            热记忆列表
        """
        return self.hot_memory[-limit:]
    
    def clear_hot_memory(self) -> None:
        """清空热记忆（会话结束时调用）"""
        self.hot_memory = []
    
    # ========== 温记忆操作 ==========
    
    def _load_warm_memory(self) -> None:
        """加载温记忆"""
        if os.path.exists(config.WARM_MEMORY_FILE):
            try:
                with open(config.WARM_MEMORY_FILE, 'r', encoding='utf-8') as f:
                    self.warm_memory = json.load(f)
            except Exception:
                self.warm_memory = {}
        
        # 确保必要字段存在
        if "user_profile" not in self.warm_memory:
            self.warm_memory["user_profile"] = {}
        if "knowledge_index" not in self.warm_memory:
            self.warm_memory["knowledge_index"] = {}
        if "skill_index" not in self.warm_memory:
            self.warm_memory["skill_index"] = {}
        if "important_decisions" not in self.warm_memory:
            self.warm_memory["important_decisions"] = []
    
    def _save_warm_memory(self) -> None:
        """保存温记忆"""
        with open(config.WARM_MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.warm_memory, f, ensure_ascii=False, indent=2)
    
    def update_user_profile(self, key: str, value: Any) -> None:
        """更新用户画像
        
        Args:
            key: 画像字段
            value: 字段值
        """
        self.warm_memory["user_profile"][key] = value
        self._save_warm_memory()
    
    def get_user_profile(self) -> Dict[str, Any]:
        """获取用户画像"""
        return self.warm_memory.get("user_profile", {})
    
    def update_knowledge_index(self, genre: str, keywords: List[str]) -> None:
        """更新知识库索引
        
        Args:
            genre: 题材类型
            keywords: 关键词列表
        """
        self.warm_memory["knowledge_index"][genre] = {
            "keywords": keywords,
            "last_updated": datetime.now().isoformat()
        }
        self._save_warm_memory()
    
    def get_knowledge_index(self, genre: str = None) -> Dict[str, Any]:
        """获取知识库索引
        
        Args:
            genre: 题材类型（可选，不传则返回全部）
        
        Returns:
            知识库索引
        """
        if genre:
            return self.warm_memory.get("knowledge_index", {}).get(genre, {})
        return self.warm_memory.get("knowledge_index", {})
    
    def update_skill_index(self, skill_id: str, skill_info: Dict[str, Any]) -> None:
        """更新Skill索引
        
        Args:
            skill_id: Skill ID
            skill_info: Skill信息
        """
        self.warm_memory["skill_index"][skill_id] = skill_info
        self._save_warm_memory()
    
    def get_skill_index(self, skill_id: str = None) -> Dict[str, Any]:
        """获取Skill索引"""
        if skill_id:
            return self.warm_memory.get("skill_index", {}).get(skill_id, {})
        return self.warm_memory.get("skill_index", {})
    
    def add_important_decision(self, decision: str, context: str = "") -> None:
        """添加重要决策记录
        
        Args:
            decision: 决策内容
            context: 决策背景
        """
        self.warm_memory["important_decisions"].append({
            "decision": decision,
            "context": context,
            "timestamp": datetime.now().isoformat()
        })
        
        # 限制决策记录数量（最多保留50条）
        if len(self.warm_memory["important_decisions"]) > 50:
            self.warm_memory["important_decisions"] = self.warm_memory["important_decisions"][-50:]
        
        self._save_warm_memory()
    
    def get_important_decisions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取重要决策记录"""
        return self.warm_memory.get("important_decisions", [])[-limit:]
    
    # ========== 冷记忆操作 ==========
    
    def add_cold_memory(self, chapter_num: int, summary: str, key_events: List[str] = None) -> None:
        """添加冷记忆（章节摘要）
        
        Args:
            chapter_num: 章节号
            summary: 章节摘要
            key_events: 关键事件列表
        """
        cold_memory_file = os.path.join(self.cold_memory_dir, f"chapter_{chapter_num}.json")
        
        cold_data = {
            "chapter_num": chapter_num,
            "summary": summary,
            "key_events": key_events or [],
            "timestamp": datetime.now().isoformat()
        }
        
        with open(cold_memory_file, 'w', encoding='utf-8') as f:
            json.dump(cold_data, f, ensure_ascii=False, indent=2)
    
    def get_cold_memory(self, chapter_num: int) -> Optional[Dict[str, Any]]:
        """获取指定章节的冷记忆
        
        Args:
            chapter_num: 章节号
        
        Returns:
            冷记忆数据
        """
        cold_memory_file = os.path.join(self.cold_memory_dir, f"chapter_{chapter_num}.json")
        
        if not os.path.exists(cold_memory_file):
            return None
        
        try:
            with open(cold_memory_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def search_cold_memory(self, keyword: str, limit: int = 5) -> List[Dict[str, Any]]:
        """搜索冷记忆（关键词匹配）
        
        Args:
            keyword: 搜索关键词
            limit: 返回条数
        
        Returns:
            匹配的冷记忆列表
        """
        results = []
        
        # 遍历所有冷记忆文件
        for filename in os.listdir(self.cold_memory_dir):
            if not filename.startswith("chapter_") or not filename.endswith(".json"):
                continue
            
            file_path = os.path.join(self.cold_memory_dir, filename)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 关键词匹配（摘要或关键事件）
                if keyword in data.get("summary", "") or any(keyword in event for event in data.get("key_events", [])):
                    results.append(data)
            except Exception:
                continue
        
        # 按章节号排序
        results.sort(key=lambda x: x.get("chapter_num", 0), reverse=True)
        
        return results[:limit]
    
    def get_recent_cold_memory(self, limit: int = 5) -> List[Dict[str, Any]]:
        """获取最近的冷记忆
        
        Args:
            limit: 返回条数
        
        Returns:
            冷记忆列表
        """
        results = []
        
        for filename in os.listdir(self.cold_memory_dir):
            if not filename.startswith("chapter_") or not filename.endswith(".json"):
                continue
            
            file_path = os.path.join(self.cold_memory_dir, filename)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                results.append(data)
            except Exception:
                continue
        
        # 按章节号排序
        results.sort(key=lambda x: x.get("chapter_num", 0), reverse=True)
        
        return results[:limit]
    
    # ========== 记忆沉淀 ==========
    
    def settle_memories(self) -> None:
        """沉淀记忆：会话结束时将热记忆中的重要信息转入温/冷记忆"""
        if not self.hot_memory:
            return
        
        # 提取重要决策
        for item in self.hot_memory:
            if item.get("type") == "decision":
                self.add_important_decision(
                    decision=item["content"],
                    context=f"来自会话记录 ({item.get('timestamp', '')})"
                )
        
        # 清空热记忆
        self.clear_hot_memory()
    
    # ========== 综合查询 ==========
    
    def get_context_for_generation(self, current_chapter: int) -> Dict[str, Any]:
        """为章节生成提供上下文
        
        Args:
            current_chapter: 当前章节号
        
        Returns:
            上下文字典
        """
        context = {
            "hot_memory": self.get_hot_memory(limit=20),
            "user_profile": self.get_user_profile(),
            "important_decisions": self.get_important_decisions(limit=10),
            "recent_cold_memory": self.get_recent_cold_memory(limit=5)
        }
        
        # 如果有前一章的冷记忆，加入上下文
        if current_chapter > 1:
            prev_chapter_memory = self.get_cold_memory(current_chapter - 1)
            if prev_chapter_memory:
                context["previous_chapter"] = prev_chapter_memory
        
        return context
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆系统统计信息"""
        cold_memory_count = len([f for f in os.listdir(self.cold_memory_dir) 
                                 if f.startswith("chapter_") and f.endswith(".json")])
        
        return {
            "hot_memory_count": len(self.hot_memory),
            "warm_memory_keys": list(self.warm_memory.keys()),
            "cold_memory_count": cold_memory_count,
            "important_decisions_count": len(self.warm_memory.get("important_decisions", []))
        }
