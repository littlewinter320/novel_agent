"""
LLM缓存机制(LLMCache)

核心职责:
- 实现缓存机制，提高大语言模型(LLM)响应命中率
- 优化Token使用，最小化不必要的Token消耗
- 添加Token使用模式和缓存效果的监控

工作流程:
接收请求 → 检查缓存 → 命中则返回缓存 → 未命中则调用LLM → 缓存结果

设计思路:
- 使用LRU缓存策略（最近最少使用）
- 基于提示词哈希进行缓存匹配
- 支持缓存过期时间
- 统计缓存命中率和Token使用情况

输出格式:
{
    "cached": bool,
    "response": 响应内容,
    "token_usage": Token使用统计,
    "cache_stats": 缓存统计
}
"""

import json
import os
import sys
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import OrderedDict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class LLMCache:
    """
    LLM缓存机制类
    
    核心功能:
    1. 缓存管理：存储和检索LLM响应
    2. 命中率统计：统计缓存命中率
    3. Token使用监控：统计Token使用情况
    4. 缓存过期：支持缓存过期机制
    
    使用场景:
    - 减少重复的LLM调用
    - 降低API成本
    - 提高响应速度
    
    使用流程:
    1. 调用get(prompt)获取缓存或调用LLM
    2. 内部自动检查缓存
    3. 命中则返回缓存，未命中则调用LLM并缓存
    4. 调用get_stats()获取统计信息
    """
    
    def __init__(self, max_size: int = 1000, ttl_hours: int = 24):
        """
        初始化LLM缓存

        Args:
            max_size: 最大缓存条目数（默认1000）
            ttl_hours: 缓存过期时间（小时，默认24小时）
        """
        self.max_size = max_size
        self.ttl_hours = ttl_hours
        self.cache = OrderedDict()  # 使用OrderedDict实现LRU
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_tokens_used": 0,
            "cached_tokens_saved": 0
        }
        self._load_cache()
    
    def _load_cache(self):
        """
        从文件加载缓存
        """
        cache_file = os.path.join(config.DATA_DIR, "llm_cache.json")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.cache = OrderedDict(data.get("cache", {}))
                    self.stats = data.get("stats", self.stats)
            except Exception as e:
                print(f"加载缓存失败: {e}")
    
    def _save_cache(self):
        """
        保存缓存到文件
        """
        cache_file = os.path.join(config.DATA_DIR, "llm_cache.json")
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "cache": dict(self.cache),
                    "stats": self.stats
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存缓存失败: {e}")
    
    def _generate_key(self, prompt: str, system_prompt: str = None) -> str:
        """
        生成缓存键（基于提示词哈希）
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
        
        Returns:
            缓存键（哈希值）
        """
        key_text = prompt
        if system_prompt:
            key_text = f"{system_prompt}|||{prompt}"
        
        return hashlib.md5(key_text.encode('utf-8')).hexdigest()
    
    def _is_expired(self, cache_entry: Dict[str, Any]) -> bool:
        """
        检查缓存是否过期
        
        Args:
            cache_entry: 缓存条目
        
        Returns:
            是否过期
        """
        cached_at = cache_entry.get("cached_at")
        if not cached_at:
            return True
        
        try:
            cached_time = datetime.fromisoformat(cached_at)
            expiration_time = cached_time + timedelta(hours=self.ttl_hours)
            return datetime.now() > expiration_time
        except Exception:
            return True
    
    def get(self, prompt: str, system_prompt: str = None, 
           llm_client=None) -> Dict[str, Any]:
        """
        获取LLM响应（优先从缓存）
        
        实现逻辑:
        1. 生成缓存键
        2. 检查缓存
        3. 命中且未过期则返回缓存
        4. 未命中或过期则调用LLM并缓存
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            llm_client: LLM客户端（缓存未命中时使用）
        
        Returns:
            响应结果字典
        """
        self.stats["total_requests"] += 1
        cache_key = self._generate_key(prompt, system_prompt)
        
        # 检查缓存
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            
            # 检查是否过期
            if not self._is_expired(cache_entry):
                # 缓存命中
                saved_tokens = cache_entry.get("token_count", 0)
                self.stats["cache_hits"] += 1
                self.stats["cached_tokens_saved"] += saved_tokens

                # 移动到末尾（LRU）
                self.cache.move_to_end(cache_key)

                return {
                    "cached": True,
                    "response": cache_entry["response"],
                    "token_usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0
                    },
                    "tokens_saved": saved_tokens,
                    "cache_stats": self.get_stats()
                }
        
        # 缓存未命中或过期
        self.stats["cache_misses"] += 1
        
        # 调用LLM
        if llm_client is None:
            from utils.llm_client import get_llm_client
            llm_client = get_llm_client()
        
        try:
            response = llm_client.generate(prompt, system_prompt)

            # 估算Token使用（简化处理）
            prompt_tokens = len(prompt) // 2
            completion_tokens = len(response) // 2
            token_count = prompt_tokens + completion_tokens
            self.stats["total_tokens_used"] += token_count

            # 缓存结果
            self.cache[cache_key] = {
                "response": response,
                "token_count": token_count,
                "cached_at": datetime.now().isoformat()
            }

            # 维护缓存大小
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)  # 移除最旧的

            # 保存缓存
            self._save_cache()

            return {
                "cached": False,
                "response": response,
                "token_usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": token_count
                },
                "cache_stats": self.get_stats()
            }
        except Exception as e:
            print(f"LLM调用失败: {e}")
            return {
                "cached": False,
                "response": f"错误: {e}",
                "token_usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                },
                "cache_stats": self.get_stats(),
                "error": str(e)
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        hit_rate = 0
        if self.stats["total_requests"] > 0:
            hit_rate = self.stats["cache_hits"] / self.stats["total_requests"]
        
        return {
            "total_requests": self.stats["total_requests"],
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "hit_rate": f"{hit_rate:.2%}",
            "total_tokens_used": self.stats["total_tokens_used"],
            "cached_tokens_saved": self.stats["cached_tokens_saved"],
            "cache_size": len(self.cache),
            "max_cache_size": self.max_size
        }
    
    def clear_cache(self):
        """
        清空缓存
        
        功能说明:
        - 清除所有缓存条目
        - 重置缓存大小计数
        - 保存空缓存到文件
        
        使用场景:
        - 需要释放内存空间
        - 缓存数据已过期需要强制刷新
        - 调试或测试需要清空状态
        """
        self.cache.clear()
        self._save_cache()
    
    def generate_cache_report(self) -> str:
        """
        生成缓存报告
        
        功能说明:
        - 生成Markdown格式的缓存统计报告
        - 包含缓存命中率、Token使用情况、容量使用率等关键指标
        - 可用于监控缓存效果和成本优化
        
        Returns:
            Markdown格式的缓存报告字符串
        
        报告内容:
        - 缓存统计: 总请求数、命中数、未命中数、命中率
        - Token使用统计: 总使用量、节省量、节省比例
        - 缓存容量: 当前大小、最大大小、使用率
        
        使用场景:
        - 定期生成报告评估缓存效果
        - 分析Token消耗和成本优化
        - 监控系统运行状态
        """
        stats = self.get_stats()
        
        report = "# LLM缓存报告\n\n"
        
        report += "## 缓存统计\n\n"
        report += f"- 总请求数: {stats['total_requests']}\n"
        report += f"- 缓存命中: {stats['cache_hits']}\n"
        report += f"- 缓存未命中: {stats['cache_misses']}\n"
        report += f"- 命中率: {stats['hit_rate']}\n\n"
        
        report += "## Token使用统计\n\n"
        report += f"- 总Token使用: {stats['total_tokens_used']}\n"
        report += f"- 缓存节省Token: {stats['cached_tokens_saved']}\n"
        report += f"- 节省比例: {stats['cached_tokens_saved'] / max(1, stats['total_tokens_used']):.2%}\n\n"
        
        report += "## 缓存容量\n\n"
        report += f"- 当前缓存大小: {stats['cache_size']}\n"
        report += f"- 最大缓存大小: {stats['max_cache_size']}\n"
        report += f"- 使用率: {stats['cache_size'] / stats['max_cache_size']:.2%}\n"
        
        return report
    
    def get_cache_efficiency(self) -> Dict[str, Any]:
        """
        获取缓存效率指标
        
        功能说明:
        - 计算缓存效率评分(0-100分)
        - 评估缓存策略的有效性
        - 提供优化建议
        
        Returns:
            缓存效率指标字典，包含:
            - efficiency_score: 效率评分(0-100)
            - hit_rate_percent: 命中率百分比
            - token_savings_percent: Token节省百分比
            - recommendations: 优化建议列表
        
        评分标准:
        - 命中率权重: 60%
        - Token节省率权重: 40%
        - 评分 = 命中率 * 60 + Token节省率 * 40
        
        使用场景:
        - 评估缓存策略效果
        - 识别优化机会
        - 监控系统健康度
        """
        stats = self.get_stats()
        
        # 计算命中率百分比
        hit_rate_percent = 0
        if stats["total_requests"] > 0:
            hit_rate_percent = (stats["cache_hits"] / stats["total_requests"]) * 100
        
        # 计算Token节省百分比
        token_savings_percent = 0
        total_tokens = stats["total_tokens_used"] + stats["cached_tokens_saved"]
        if total_tokens > 0:
            token_savings_percent = (stats["cached_tokens_saved"] / total_tokens) * 100
        
        # 计算效率评分
        efficiency_score = (hit_rate_percent * 0.6) + (token_savings_percent * 0.4)
        
        # 生成优化建议
        recommendations = []
        if hit_rate_percent < 50:
            recommendations.append("命中率较低，建议增加缓存容量或调整TTL时间")
        if token_savings_percent < 30:
            recommendations.append("Token节省率较低，建议优化缓存策略")
        if stats["cache_size"] > stats["max_cache_size"] * 0.8:
            recommendations.append("缓存使用率较高，建议增加max_size参数")
        if not recommendations:
            recommendations.append("缓存运行良好，无需调整")
        
        return {
            "efficiency_score": round(efficiency_score, 2),
            "hit_rate_percent": round(hit_rate_percent, 2),
            "token_savings_percent": round(token_savings_percent, 2),
            "recommendations": recommendations
        }


# 全局实例
_llm_cache = None


def get_llm_cache() -> LLMCache:
    """获取全局LLM缓存实例（单例模式）"""
    global _llm_cache
    if _llm_cache is None:
        _llm_cache = LLMCache()
    return _llm_cache
