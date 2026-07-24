"""
网络搜索模块(WebSearch)

核心职责:
- 通过DuckDuckGo搜索引擎获取真实网页结果
- 支持获取指定链接的网页内容
- 为Agent提供实时信息获取能力

设计思路:
- 使用DuckDuckGo搜索（免费、无需API key、速度快）
- 使用requests + BeautifulSoup获取网页内容
- 搜索结果经过筛选和整理

输出格式:
{
    "query": "搜索关键词",
    "results": [搜索结果列表],
    "source": "duckduckgo" | "web_fetch"
}
"""

import json
import os
import sys
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# 尝试导入依赖
try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None
    BeautifulSoup = None

# 尝试导入DuckDuckGo搜索
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    DDGS = None


class WebSearch:
    """
    网络搜索器

    核心功能:
    1. DuckDuckGo搜索：通过DuckDuckGo获取真实搜索结果
    2. 网页内容获取：获取指定URL的网页内容
    3. 平台搜索：针对小说平台的搜索优化

    使用场景:
    - Scout Agent搜索热门小说
    - 用户给链接，获取网页信息
    - 搜索特定平台的小说数据
    """

    # User-Agent池
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]

    # 主流小说平台
    PLATFORMS = {
        "番茄小说": "fanqienovel.com",
        "起点中文网": "qidian.com",
        "七猫小说": "qimao.com",
        "晋江文学城": "jjwxc.net",
        "纵横中文网": "zongheng.com",
    }

    def __init__(self):
        """
        初始化搜索器

        初始化流程:
        1. 检查依赖是否可用
        2. 初始化HTTP会话
        """
        self.llm_client = None
        if REQUESTS_AVAILABLE:
            self.session = requests.Session()
        else:
            self.session = None

    def set_llm_client(self, llm_client):
        """设置LLM客户端（用于降级方案）"""
        self.llm_client = llm_client

    def search(self, query: str, platform: str = None, genre: str = None, max_results: int = 10) -> Dict[str, Any]:
        """
        搜索信息（核心方法）

        实现逻辑:
        1. 优先使用DuckDuckGo搜索
        2. 如果不可用，降级为LLM搜索
        3. 返回结构化结果

        Args:
            query: 搜索关键词
            platform: 目标平台（可选）
            genre: 题材（可选）
            max_results: 最大结果数（默认10）

        Returns:
            搜索结果字典
        """
        # 构造完整查询
        full_query = self._build_query(query, platform, genre)

        # 优先使用DuckDuckGo搜索
        if DDGS_AVAILABLE:
            return self._search_duckduckgo(full_query, max_results)

        # 降级为LLM搜索
        if self.llm_client:
            return self._search_llm(query, platform, genre)

        return {"error": "无可用搜索方式", "results": []}

    def _build_query(self, query: str, platform: str = None, genre: str = None) -> str:
        """构造完整查询"""
        parts = []
        if platform:
            parts.append(platform)
        if genre:
            parts.append(f"{genre}题材")
        parts.append(query)
        return " ".join(parts)

    def _search_duckduckgo(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """
        使用DuckDuckGo搜索

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            搜索结果字典
        """
        try:
            with DDGS() as ddgs:
                # 执行搜索
                results = list(ddgs.text(query, max_results=max_results))

                # 整理结果
                formatted_results = []
                for r in results:
                    formatted_results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                        "source": "duckduckgo"
                    })

                return {
                    "query": query,
                    "results": formatted_results,
                    "source": "duckduckgo",
                    "searched_at": datetime.now().isoformat()
                }

        except Exception as e:
            return {"error": f"DuckDuckGo搜索失败: {e}", "results": []}

    def _search_llm(self, query: str, platform: str = None, genre: str = None) -> Dict[str, Any]:
        """
        使用LLM搜索（降级方案）

        Args:
            query: 搜索关键词
            platform: 目标平台
            genre: 题材

        Returns:
            搜索结果字典
        """
        search_prompt = self._build_search_prompt(query, platform, genre)

        try:
            response = self.llm_client.generate(search_prompt)

            # 尝试解析JSON
            try:
                results = json.loads(response)
                return {
                    "query": query,
                    "platform": platform,
                    "genre": genre,
                    "results": results if isinstance(results, list) else [results],
                    "source": "llm_search",
                    "searched_at": datetime.now().isoformat()
                }
            except json.JSONDecodeError:
                return {
                    "query": query,
                    "platform": platform,
                    "genre": genre,
                    "results": [{"content": response}],
                    "source": "llm_search",
                    "searched_at": datetime.now().isoformat()
                }

        except Exception as e:
            return {"error": str(e), "results": []}

    def _build_search_prompt(self, query: str, platform: str = None, genre: str = None) -> str:
        """构造LLM搜索提示词"""
        platform_text = f"在{platform}平台" if platform else ""
        genre_text = f"{genre}题材" if genre else ""

        prompt = f"""请搜索{platform_text}{genre_text}的以下信息：

搜索需求：{query}

要求：
1. 搜索最新的、最热门的作品
2. 提供作品名称、作者、热度、简介
3. 如果有链接，请提供
4. 分析作品的爆火特征

请以JSON数组格式返回，每部作品包含：
{{
    "title": "作品名称",
    "author": "作者",
    "platform": "平台",
    "heat": "热度/评分",
    "brief": "简介（100字以内）",
    "tags": ["标签"],
    "url": "链接（如果有）"
}}

只返回JSON数组，不要其他内容。"""

        return prompt

    def fetch_url(self, url: str) -> Dict[str, Any]:
        """
        获取指定URL的网页内容

        实现逻辑:
        1. 发送HTTP请求获取网页
        2. 解析HTML提取正文
        3. 返回结构化内容

        Args:
            url: 网页URL

        Returns:
            网页内容字典
        """
        if not REQUESTS_AVAILABLE:
            return {"error": "requests未安装", "content": ""}

        try:
            # 设置请求头
            headers = {
                "User-Agent": self.USER_AGENTS[0],
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }

            # 发送请求
            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # 提取标题
            title = soup.title.string if soup.title else ""

            # 提取正文
            content = self._extract_content(soup, url)

            # 提取链接
            links = self._extract_links(soup, url)

            return {
                "url": url,
                "title": title.strip() if title else "",
                "content": content,
                "links": links[:10],
                "fetched_at": datetime.now().isoformat()
            }

        except Exception as e:
            return {"error": str(e), "content": ""}

    def _extract_content(self, soup, url: str) -> str:
        """提取网页正文"""
        # 尝试常见的内容选择器
        content_selectors = [
            'article', '.article', '.content', '.post-content',
            '.entry-content', '.chapter-content', '.read-content',
            '#content', '#chapter-content', 'main'
        ]

        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                text = content_elem.get_text(separator='\n', strip=True)
                text = re.sub(r'\s+', '\n', text)
                if len(text) > 100:
                    return text[:5000]

        # 如果没找到，尝试提取body
        body = soup.body
        if body:
            text = body.get_text(separator='\n', strip=True)
            text = re.sub(r'\s+', '\n', text)
            return text[:5000]

        return ""

    def _extract_links(self, soup, base_url: str) -> List[Dict[str, str]]:
        """提取网页中的链接"""
        links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            text = a_tag.get_text(strip=True)

            if not text or len(text) < 2:
                continue

            if href.startswith('http'):
                full_url = href
            elif href.startswith('/'):
                from urllib.parse import urljoin
                full_url = urljoin(base_url, href)
            else:
                continue

            links.append({
                "text": text,
                "url": full_url
            })

            if len(links) >= 10:
                break

        return links

    def search_platform(self, platform: str, genre: str,
                       constraints: str = None) -> Dict[str, Any]:
        """
        搜索指定平台的小说

        Args:
            platform: 平台名称（如"番茄小说"）
            genre: 题材（如"仙侠"）
            constraints: 额外约束（如"女频"、"短篇"）

        Returns:
            搜索结果
        """
        query = f"{genre}题材的热门小说"
        if constraints:
            query = f"{constraints} {query}"

        return self.search(query, platform=platform, genre=genre)


# 全局单例
_web_search: Optional[WebSearch] = None


def get_web_search() -> WebSearch:
    """获取全局WebSearch单例"""
    global _web_search
    if _web_search is None:
        _web_search = WebSearch()
    return _web_search


if __name__ == "__main__":
    # 测试搜索
    search = get_web_search()

    # 测试DuckDuckGo搜索
    result = search.search("番茄小说 仙侠 热门")
    print(json.dumps(result, ensure_ascii=False, indent=2))
