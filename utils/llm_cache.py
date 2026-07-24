"""
LLM缓存机制(LLMCache)

核心职责:
- 实现多层缓存机制，大幅提高大语言模型(LLM)响应命中率
- 优化Token使用，最小化不必要的Token消耗
- 添加Token使用模式和缓存效果的监控

参考方案:
- MVR-cache (PKU-SDS-lab, 2026): 多向量检索 + 可学习提示词分割，命中率提升37%
- GPTCache: 语义缓存，embedding + 向量相似度
- 三层指纹方案: 结构化指纹 + 嵌入向量 + 动态校验

工作流程:
接收请求 → 第一层精确匹配(MD5) → 第二层语义匹配(embedding) → 第三层关键词匹配(Jaccard)
→ 全部未命中则调用LLM → 缓存结果到三层

设计思路:
- 第一层：精确匹配（MD5哈希，O(1)查询，最快）
- 第二层：语义匹配（embedding余弦相似度，捕捉语义等价）
- 第三层：关键词匹配（Jaccard相似度，降级方案）
- 前缀缓存：固定system prompt前缀，利用模型服务端KV cache
- 参数归一化：temperature>0.1不缓存（非确定性请求）

输出格式:
{
    "cached": bool,
    "cache_layer": "exact" | "semantic" | "keyword" | null,
    "similarity": float,
    "response": 响应内容,
    "token_usage": Token使用统计,
    "cache_stats": 缓存统计
}
"""

import json
import os
import sys
import hashlib
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import OrderedDict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


# ==================== 语义匹配模块（可选依赖） ====================

# 尝试导入 sentence-transformers（本地embedding，无需API调用）
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False
    SentenceTransformer = None
    np = None

# 尝试导入 jieba（中文分词）
try:
    import jieba
    import jieba.analyse
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    jieba = None


class SemanticIndex:
    """
    语义索引（基于embedding向量）
    
    核心功能:
    1. 将prompt转换为embedding向量
    2. 计算余弦相似度
    3. 支持批量查询
    
    依赖:
    - sentence-transformers（本地模型，无需API）
    - 模型: paraphrase-multilingual-MiniLM-L12-v2（支持中文，384维）
    """
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        """
        初始化语义索引
        
        Args:
            model_name: sentence-transformers模型名称
        """
        self.model = None
        self.embeddings = []  # List of (cache_key, embedding, prompt, response)
        self.model_name = model_name
        
        if SEMANTIC_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
            except Exception as e:
                print(f"加载语义模型失败: {e}")
    
    def is_available(self) -> bool:
        """检查语义索引是否可用"""
        return self.model is not None
    
    def encode(self, text: str) -> Optional[Any]:
        """
        将文本转换为embedding向量
        
        Args:
            text: 输入文本
        
        Returns:
            embedding向量，失败返回None
        """
        if not self.is_available():
            return None
        
        try:
            # 截断过长文本（模型最大长度512 tokens）
            text = text[:2000]
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            print(f"编码失败: {e}")
            return None
    
    def add(self, cache_key: str, prompt: str, response: str):
        """
        添加prompt到语义索引
        
        Args:
            cache_key: 缓存键
            prompt: 用户提示
            response: LLM响应
        """
        if not self.is_available():
            return
        
        embedding = self.encode(prompt)
        if embedding is not None:
            self.embeddings.append((cache_key, embedding, prompt, response))
    
    def search(self, query: str, top_k: int = 1, threshold: float = 0.92) -> List[Tuple[str, float, str]]:
        """
        语义搜索最相似的prompt
        
        Args:
            query: 查询文本
            top_k: 返回最相似的k个结果
            threshold: 相似度阈值（0-1），默认0.92
        
        Returns:
            List of (cache_key, similarity, response)
        """
        if not self.is_available() or not self.embeddings:
            return []
        
        query_embedding = self.encode(query)
        if query_embedding is None:
            return []
        
        # 计算余弦相似度
        similarities = []
        for cache_key, emb, prompt, response in self.embeddings:
            sim = self._cosine_similarity(query_embedding, emb)
            if sim >= threshold:
                similarities.append((cache_key, sim, response))
        
        # 按相似度降序排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def _cosine_similarity(self, a: Any, b: Any) -> float:
        """计算两个向量的余弦相似度"""
        if np is None:
            return 0.0
        
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(dot_product / (norm_a * norm_b))


class KeywordIndex:
    """
    关键词索引（基于Jaccard相似度）
    
    核心功能:
    1. 提取文本关键词（TF-IDF或TextRank）
    2. 计算Jaccard相似度
    3. 降级方案（无需embedding模型）
    
    依赖:
    - jieba（中文分词和关键词提取）
    """
    
    def __init__(self, top_k_keywords: int = 20):
        """
        初始化关键词索引
        
        Args:
            top_k_keywords: 每个prompt提取的关键词数量
        """
        self.top_k_keywords = top_k_keywords
        self.keywords_map = {}  # cache_key -> set of keywords
        self.responses = {}  # cache_key -> response
    
    def is_available(self) -> bool:
        """检查关键词索引是否可用"""
        return JIEBA_AVAILABLE
    
    def extract_keywords(self, text: str) -> set:
        """
        提取文本关键词
        
        Args:
            text: 输入文本
        
        Returns:
            关键词集合
        """
        if not JIEBA_AVAILABLE:
            return set()
        
        try:
            # 使用TextRank算法提取关键词
            keywords = jieba.analyse.textrank(text, topK=self.top_k_keywords, withWeight=False)
            return set(keywords)
        except Exception as e:
            print(f"提取关键词失败: {e}")
            return set()
    
    def add(self, cache_key: str, prompt: str, response: str):
        """
        添加prompt到关键词索引
        
        Args:
            cache_key: 缓存键
            prompt: 用户提示
            response: LLM响应
        """
        if not self.is_available():
            return
        
        keywords = self.extract_keywords(prompt)
        self.keywords_map[cache_key] = keywords
        self.responses[cache_key] = response
    
    def search(self, query: str, top_k: int = 1, threshold: float = 0.6) -> List[Tuple[str, float, str]]:
        """
        关键词搜索最相似的prompt
        
        Args:
            query: 查询文本
            top_k: 返回最相似的k个结果
            threshold: Jaccard相似度阈值（0-1），默认0.6
        
        Returns:
            List of (cache_key, similarity, response)
        """
        if not self.is_available() or not self.keywords_map:
            return []
        
        query_keywords = self.extract_keywords(query)
        if not query_keywords:
            return []
        
        # 计算Jaccard相似度
        similarities = []
        for cache_key, keywords in self.keywords_map.items():
            sim = self._jaccard_similarity(query_keywords, keywords)
            if sim >= threshold:
                response = self.responses.get(cache_key, "")
                similarities.append((cache_key, sim, response))
        
        # 按相似度降序排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def _jaccard_similarity(self, set1: set, set2: set) -> float:
        """计算两个集合的Jaccard相似度"""
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        if union == 0:
            return 0.0
        
        return intersection / union


class LLMCache:
    """
    LLM缓存机制类
    
    核心功能:
    1. 三层缓存：精确匹配 + 语义匹配 + 关键词匹配
    2. 前缀缓存：固定system prompt前缀，利用模型服务端KV cache
    3. 参数归一化：temperature>0.1不缓存（非确定性请求）
    4. 命中率统计：统计各层缓存命中率
    5. Token使用监控：统计Token使用情况
    
    使用场景:
    - 减少重复的LLM调用
    - 降低API成本
    - 提高响应速度
    
    使用流程:
    1. 调用get(prompt)获取缓存或调用LLM
    2. 内部自动按三层顺序检查缓存
    3. 命中则返回缓存，未命中则调用LLM并缓存
    4. 调用get_stats()获取统计信息
    """
    
    def __init__(self, max_size: int = 2000, ttl_hours: int = 168,
                 enable_semantic: bool = True, enable_keyword: bool = True,
                 semantic_threshold: float = 0.90, keyword_threshold: float = 0.66):
        self.max_size = max_size
        self.ttl_hours = ttl_hours
        self.cache = OrderedDict()  # 使用OrderedDict实现LRU
        
        # 三层缓存统计
        self.stats = {
            "total_requests": 0,
            "exact_hits": 0,  # 第一层：精确匹配命中
            "semantic_hits": 0,  # 第二层：语义匹配命中
            "keyword_hits": 0,  # 第三层：关键词匹配命中
            "cache_misses": 0,
            "total_tokens_used": 0,
            "cached_tokens_saved": 0
        }
        
        # 兼容旧字段
        self.stats["cache_hits"] = 0
        
        # 相似度阈值
        self.semantic_threshold = semantic_threshold
        self.keyword_threshold = keyword_threshold
        
        # 初始化索引
        self.semantic_index = SemanticIndex() if enable_semantic else None
        self.keyword_index = KeywordIndex() if enable_keyword else None
        
        # 前缀缓存（固定system prompt前缀）
        self.prefix_cache = {}  # prefix_hash -> system_prompt
        
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
                    
                    # 重建语义索引和关键词索引
                    if self.semantic_index and self.semantic_index.is_available():
                        for cache_key, entry in self.cache.items():
                            prompt = entry.get("prompt", "")
                            response = entry.get("response", "")
                            if prompt and response:
                                self.semantic_index.add(cache_key, prompt, response)
                    
                    if self.keyword_index and self.keyword_index.is_available():
                        for cache_key, entry in self.cache.items():
                            prompt = entry.get("prompt", "")
                            response = entry.get("response", "")
                            if prompt and response:
                                self.keyword_index.add(cache_key, prompt, response)
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
    
    def _normalize_text(self, text: str) -> str:
        """
        文本归一化（去除非语义差异）
        
        Args:
            text: 输入文本
        
        Returns:
            归一化后的文本
        """
        # 去除多余空白
        text = re.sub(r'\s+', ' ', text).strip()
        # 统一换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        # 去除非语义字段（如时间戳、request_id等）
        text = re.sub(r'\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\b', '', text)
        text = re.sub(r'\brequest_id=[a-zA-Z0-9]+\b', '', text)
        return text
    
    def _generate_key(self, prompt: str, system_prompt: str = None) -> str:
        """
        生成缓存键（基于归一化后的提示词哈希）
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
        
        Returns:
            缓存键（哈希值）
        """
        # 归一化文本
        normalized_prompt = self._normalize_text(prompt)
        normalized_system = self._normalize_text(system_prompt) if system_prompt else ""
        
        key_text = normalized_prompt
        if normalized_system:
            key_text = f"{normalized_system}|||{normalized_prompt}"
        
        # 使用BLAKE3（比MD5快3倍，抗碰撞更强）或MD5
        try:
            import blake3
            return blake3.blake3(key_text.encode('utf-8')).hexdigest()
        except ImportError:
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
    
    def _should_cache(self, temperature: float = None) -> bool:
        """
        判断是否应该缓存（参数归一化）
        
        Args:
            temperature: LLM温度参数
        
        Returns:
            是否应该缓存
        """
        # temperature > 0.1 视为非确定性请求，不缓存
        if temperature is not None and temperature > 0.1:
            return False
        return True
    
    def get(self, prompt: str, system_prompt: str = None, 
           llm_client=None, temperature: float = None) -> Dict[str, Any]:
        """
        获取LLM响应（优先从缓存）
        
        实现逻辑:
        1. 参数归一化：temperature>0.1不缓存
        2. 第一层：精确匹配（MD5哈希，O(1)查询）
        3. 第二层：语义匹配（embedding余弦相似度）
        4. 第三层：关键词匹配（Jaccard相似度）
        5. 全部未命中则调用LLM并缓存到三层
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            llm_client: LLM客户端（缓存未命中时使用）
            temperature: LLM温度参数（可选）
        
        Returns:
            响应结果字典
        """
        self.stats["total_requests"] += 1
        
        # 参数归一化：非确定性请求不缓存
        if not self._should_cache(temperature):
            self.stats["cache_misses"] += 1
            # 直接调用LLM
            return self._call_llm(prompt, system_prompt, llm_client, skip_cache=True)
        
        cache_key = self._generate_key(prompt, system_prompt)
        
        # 检查缓存
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            
            # 检查是否过期
            if not self._is_expired(cache_entry):
                # 缓存命中
                saved_tokens = cache_entry.get("token_count", 0)
                self.stats["exact_hits"] += 1
                self.stats["cache_hits"] += 1
                self.stats["cached_tokens_saved"] += saved_tokens

                # 移动到末尾（LRU）
                self.cache.move_to_end(cache_key)

                return {
                    "cached": True,
                    "cache_layer": "exact",
                    "similarity": 1.0,
                    "response": cache_entry["response"],
                    "token_usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0
                    },
                    "tokens_saved": saved_tokens,
                    "cache_stats": self.get_stats()
                }
        
        # ==================== 第二层：语义匹配 ====================
        if self.semantic_index and self.semantic_index.is_available():
            results = self.semantic_index.search(prompt, top_k=1, threshold=self.semantic_threshold)
            if results:
                cache_key_hit, similarity, response = results[0]
                
                # 检查缓存是否过期
                if cache_key_hit in self.cache and not self._is_expired(self.cache[cache_key_hit]):
                    saved_tokens = self.cache[cache_key_hit].get("token_count", 0)
                    self.stats["semantic_hits"] += 1
                    self.stats["cache_hits"] += 1
                    self.stats["cached_tokens_saved"] += saved_tokens
                    
                    # 移动到末尾（LRU）
                    self.cache.move_to_end(cache_key_hit)
                    
                    return {
                        "cached": True,
                        "cache_layer": "semantic",
                        "similarity": similarity,
                        "response": response,
                        "token_usage": {
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_tokens": 0
                        },
                        "tokens_saved": saved_tokens,
                        "cache_stats": self.get_stats()
                    }
        
        # ==================== 第三层：关键词匹配 ====================
        if self.keyword_index and self.keyword_index.is_available():
            results = self.keyword_index.search(prompt, top_k=1, threshold=self.keyword_threshold)
            if results:
                cache_key_hit, similarity, response = results[0]
                
                # 检查缓存是否过期
                if cache_key_hit in self.cache and not self._is_expired(self.cache[cache_key_hit]):
                    saved_tokens = self.cache[cache_key_hit].get("token_count", 0)
                    self.stats["keyword_hits"] += 1
                    self.stats["cache_hits"] += 1
                    self.stats["cached_tokens_saved"] += saved_tokens
                    
                    # 移动到末尾（LRU）
                    self.cache.move_to_end(cache_key_hit)
                    
                    return {
                        "cached": True,
                        "cache_layer": "keyword",
                        "similarity": similarity,
                        "response": response,
                        "token_usage": {
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_tokens": 0
                        },
                        "tokens_saved": saved_tokens,
                        "cache_stats": self.get_stats()
                    }
        
        # ==================== 全部未命中 ====================
        self.stats["cache_misses"] += 1
        return self._call_llm(prompt, system_prompt, llm_client, cache_key=cache_key)
    
    def _call_llm(self, prompt: str, system_prompt: str = None, 
                 llm_client=None, cache_key: str = None, skip_cache: bool = False) -> Dict[str, Any]:
        """
        调用LLM并缓存结果
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            llm_client: LLM客户端
            cache_key: 缓存键（可选）
            skip_cache: 是否跳过缓存（可选）
        
        Returns:
            响应结果字典
        """
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

            # 缓存结果（如果启用）
            if not skip_cache and cache_key:
                # 存储到主缓存
                self.cache[cache_key] = {
                    "prompt": prompt,
                    "system_prompt": system_prompt,
                    "response": response,
                    "token_count": token_count,
                    "cached_at": datetime.now().isoformat()
                }

                # 存储到语义索引
                if self.semantic_index and self.semantic_index.is_available():
                    self.semantic_index.add(cache_key, prompt, response)

                # 存储到关键词索引
                if self.keyword_index and self.keyword_index.is_available():
                    self.keyword_index.add(cache_key, prompt, response)

                # 维护缓存大小
                if len(self.cache) > self.max_size:
                    self.cache.popitem(last=False)  # 移除最旧的

                # 保存缓存
                self._save_cache()

            return {
                "cached": False,
                "cache_layer": None,
                "similarity": 0.0,
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
                "cache_layer": None,
                "similarity": 0.0,
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
        total_hits = self.stats["exact_hits"] + self.stats["semantic_hits"] + self.stats["keyword_hits"]
        hit_rate = 0
        if self.stats["total_requests"] > 0:
            hit_rate = total_hits / self.stats["total_requests"]
        
        return {
            "total_requests": self.stats["total_requests"],
            "cache_hits": total_hits,  # 兼容旧字段
            "exact_hits": self.stats["exact_hits"],
            "semantic_hits": self.stats["semantic_hits"],
            "keyword_hits": self.stats["keyword_hits"],
            "cache_misses": self.stats["cache_misses"],
            "hit_rate": f"{hit_rate:.2%}",
            "total_tokens_used": self.stats["total_tokens_used"],
            "cached_tokens_saved": self.stats["cached_tokens_saved"],
            "cache_size": len(self.cache),
            "max_cache_size": self.max_size,
            "semantic_available": self.semantic_index.is_available() if self.semantic_index else False,
            "keyword_available": self.keyword_index.is_available() if self.keyword_index else False
        }
    
    def clear_cache(self):
        """
        清空缓存
        
        功能说明:
        - 清除所有缓存条目
        - 重置缓存大小计数
        - 清空语义索引和关键词索引
        - 保存空缓存到文件
        
        使用场景:
        - 需要释放内存空间
        - 缓存数据已过期需要强制刷新
        - 调试或测试需要清空状态
        """
        self.cache.clear()
        if self.semantic_index:
            self.semantic_index.embeddings.clear()
        if self.keyword_index:
            self.keyword_index.keywords_map.clear()
            self.keyword_index.responses.clear()
        self._save_cache()
    
    def generate_cache_report(self) -> str:
        """
        生成缓存报告
        
        功能说明:
        - 生成Markdown格式的缓存统计报告
        - 包含各层缓存命中率、Token使用情况、容量使用率等关键指标
        - 可用于监控缓存效果和成本优化
        
        Returns:
            Markdown格式的缓存报告字符串
        """
        stats = self.get_stats()
        
        report = "# LLM缓存报告\n\n"
        
        report += "## 缓存统计\n\n"
        report += f"- 总请求数: {stats['total_requests']}\n"
        report += f"- 总命中数: {stats['cache_hits']}\n"
        report += f"  - 第一层（精确匹配）: {stats['exact_hits']}\n"
        report += f"  - 第二层（语义匹配）: {stats['semantic_hits']}\n"
        report += f"  - 第三层（关键词匹配）: {stats['keyword_hits']}\n"
        report += f"- 缓存未命中: {stats['cache_misses']}\n"
        report += f"- 命中率: {stats['hit_rate']}\n\n"
        
        report += "## Token使用统计\n\n"
        report += f"- 总Token使用: {stats['total_tokens_used']}\n"
        report += f"- 缓存节省Token: {stats['cached_tokens_saved']}\n"
        total_tokens = stats['total_tokens_used'] + stats['cached_tokens_saved']
        savings_rate = stats['cached_tokens_saved'] / max(1, total_tokens)
        report += f"- 节省比例: {savings_rate:.2%}\n\n"
        
        report += "## 缓存容量\n\n"
        report += f"- 当前缓存大小: {stats['cache_size']}\n"
        report += f"- 最大缓存大小: {stats['max_cache_size']}\n"
        usage_rate = stats['cache_size'] / stats['max_cache_size']
        report += f"- 使用率: {usage_rate:.2%}\n\n"
        
        report += "## 索引状态\n\n"
        report += f"- 语义索引: {'✓ 可用' if stats['semantic_available'] else '✗ 不可用'}\n"
        report += f"- 关键词索引: {'✓ 可用' if stats['keyword_available'] else '✗ 不可用'}\n"
        
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
            - layer_breakdown: 各层命中占比
            - recommendations: 优化建议列表
        
        评分标准:
        - 命中率权重: 60%
        - Token节省率权重: 40%
        - 评分 = 命中率 * 60 + Token节省率 * 40
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
        
        # 各层命中占比
        layer_breakdown = {}
        if stats["cache_hits"] > 0:
            layer_breakdown = {
                "exact": stats["exact_hits"] / stats["cache_hits"],
                "semantic": stats["semantic_hits"] / stats["cache_hits"],
                "keyword": stats["keyword_hits"] / stats["cache_hits"]
            }
        
        # 生成优化建议
        recommendations = []
        if hit_rate_percent < 50:
            recommendations.append("命中率较低，建议增加缓存容量或调整TTL时间")
        if not stats["semantic_available"]:
            recommendations.append("语义索引不可用，建议安装sentence-transformers: pip install sentence-transformers")
        if not stats["keyword_available"]:
            recommendations.append("关键词索引不可用，建议安装jieba: pip install jieba")
        if layer_breakdown.get("exact", 0) > 0.9:
            recommendations.append("精确匹配占比过高，语义匹配未充分利用，建议降低semantic_threshold")
        if layer_breakdown.get("keyword", 0) > 0.5:
            recommendations.append("关键词匹配占比过高，建议安装语义模型提升精度")
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
            "layer_breakdown": layer_breakdown,
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
