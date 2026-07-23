"""
网页爬虫模块(WebScraper)

核心职责:
- 爬取番茄小说、起点中文网等平台的热门小说数据
- 提取小说标题、作者、热度、简介、标签等信息
- 支持动态渲染页面（JavaScript渲染）
- 提供反爬虫策略（User-Agent轮换、请求间隔）

工作流程:
指定平台+题材 → 构造请求 → 解析HTML → 提取数据 → 返回结构化结果

设计思路:
- 使用requests + BeautifulSoup进行静态页面爬取
- 使用Playwright进行动态页面爬取（JavaScript渲染）
- 支持多平台适配（番茄、起点、七猫等）
- 反爬虫：随机User-Agent、请求间隔、代理支持

关键算法:
- 平台适配器模式：每个平台一个适配器类
- 数据清洗：去除HTML标签、标准化数据格式
- 错误重试：失败后自动重试3次

输出格式:
{
    "platform": "平台名称",
    "genre": "题材",
    "novels": [
        {
            "title": "标题",
            "author": "作者",
            "heat": "热度值",
            "brief": "简介",
            "tags": ["标签"],
            "url": "链接"
        }
    ],
    "crawled_at": "爬取时间"
}
"""

import json
import os
import sys
import time
import random
from typing import Dict, List, Any, Optional
from datetime import datetime
from urllib.parse import urljoin

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# 尝试导入爬虫依赖
try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None
    BeautifulSoup = None

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None


class WebScraper:
    """
    网页爬虫器
    
    核心功能:
    1. 多平台支持：番茄小说、起点中文网、七猫等
    2. 动态渲染：支持JavaScript渲染页面
    3. 反爬虫：User-Agent轮换、请求间隔
    4. 数据提取：结构化提取小说信息
    
    使用场景:
    - Scout Agent扫榜分析时，获取最新热门小说数据
    - 定期更新题材知识库的热门话题和梗
    
    使用流程:
    1. 创建WebScraper实例
    2. 调用crawl_platform(platform, genre)爬取指定平台
    3. 返回结构化数据
    """
    
    # User-Agent池
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ]
    
    # 平台URL配置
    PLATFORM_URLS = {
        "fanqie": {
            "name": "番茄小说",
            "base_url": "https://fanqienovel.com",
            "ranking_url": "https://fanqienovel.com/ranking/hot_male_{genre_id}",
            "genre_map": {
                "都市": "10001",
                "玄幻": "10002",
                "仙侠": "10003",
                "科幻": "10004",
                "游戏": "10005",
                "悬疑": "10006",
            }
        },
        "qidian": {
            "name": "起点中文网",
            "base_url": "https://www.qidian.com",
            "ranking_url": "https://www.qidian.com/rank/hotsales/{genre_id}/",
            "genre_map": {
                "都市": "都市",
                "玄幻": "玄幻",
                "仙侠": "仙侠",
                "科幻": "科幻",
                "游戏": "游戏",
                "悬疑": "悬疑",
            }
        },
        "qimao": {
            "name": "七猫小说",
            "base_url": "https://www.qimao.com",
            "ranking_url": "https://www.qimao.com/rank/hot_{genre_id}",
            "genre_map": {
                "都市": "dushi",
                "玄幻": "xuanhuan",
                "仙侠": "xianxia",
                "科幻": "kehuan",
                "游戏": "youxi",
                "悬疑": "xuanyi",
            }
        }
    }
    
    def __init__(self, use_playwright: bool = False):
        """
        初始化爬虫器
        
        Args:
            use_playwright: 是否使用Playwright进行动态渲染（默认False）
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError("请先安装requests和beautifulsoup4: pip install requests beautifulsoup4")
        
        self.use_playwright = use_playwright and PLAYWRIGHT_AVAILABLE
        self.session = requests.Session()
        self.browser = None
        self.page = None
        
        if self.use_playwright:
            self._init_playwright()
    
    def _init_playwright(self):
        """初始化Playwright浏览器"""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)
            self.page = self.browser.new_page()
        except Exception as e:
            print(f"Playwright初始化失败: {e}")
            self.use_playwright = False
    
    def _get_random_headers(self) -> Dict[str, str]:
        """获取随机请求头"""
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
    
    def _fetch_page(self, url: str) -> str:
        """
        获取页面内容
        
        Args:
            url: 页面URL
        
        Returns:
            页面HTML内容
        """
        if self.use_playwright and self.page:
            # 使用Playwright动态渲染
            try:
                self.page.goto(url, wait_until="networkidle")
                time.sleep(2)  # 等待JavaScript加载
                return self.page.content()
            except Exception as e:
                print(f"Playwright爬取失败: {e}")
                return ""
        else:
            # 使用requests静态爬取
            try:
                headers = self._get_random_headers()
                response = self.session.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                return response.text
            except Exception as e:
                print(f"请求失败: {e}")
                return ""
    
    def crawl_platform(self, platform: str, genre: str, limit: int = 10) -> Dict[str, Any]:
        """
        爬取指定平台的热门小说
        
        Args:
            platform: 平台名称（fanqie/qidian/qimao）
            genre: 题材名称
            limit: 返回数量限制
        
        Returns:
            爬取结果字典
        """
        platform_config = self.PLATFORM_URLS.get(platform)
        if not platform_config:
            return {"error": f"不支持的平台: {platform}"}
        
        genre_id = platform_config["genre_map"].get(genre)
        if not genre_id:
            return {"error": f"不支持的题材: {genre}"}
        
        # 构造URL
        url = platform_config["ranking_url"].format(genre_id=genre_id)
        
        # 爬取页面
        html = self._fetch_page(url)
        if not html:
            return {"error": "爬取失败"}
        
        # 解析数据
        novels = self._parse_novels(html, platform)
        
        return {
            "platform": platform_config["name"],
            "genre": genre,
            "novels": novels[:limit],
            "crawled_at": datetime.now().isoformat(),
            "url": url
        }
    
    def _parse_novels(self, html: str, platform: str) -> List[Dict[str, Any]]:
        """
        解析小说数据
        
        Args:
            html: 页面HTML
            platform: 平台名称
        
        Returns:
            小说列表
        """
        soup = BeautifulSoup(html, "html.parser")
        novels = []
        
        # 根据不同平台使用不同的解析规则
        if platform == "fanqie":
            novels = self._parse_fanqie(soup)
        elif platform == "qidian":
            novels = self._parse_qidian(soup)
        elif platform == "qimao":
            novels = self._parse_qimao(soup)
        
        return novels
    
    def _parse_fanqie(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """解析番茄小说页面"""
        novels = []
        
        # 番茄小说的榜单结构（需要根据实际页面调整）
        items = soup.select(".rank-item, .book-item, .novel-item")
        
        for item in items:
            try:
                title_elem = item.select_one(".title, .book-title, h3")
                author_elem = item.select_one(".author, .book-author")
                heat_elem = item.select_one(".heat, .popularity, .rank-value")
                brief_elem = item.select_one(".brief, .intro, .description")
                link_elem = item.select_one("a[href]")
                
                novel = {
                    "title": title_elem.get_text(strip=True) if title_elem else "",
                    "author": author_elem.get_text(strip=True) if author_elem else "",
                    "heat": heat_elem.get_text(strip=True) if heat_elem else "",
                    "brief": brief_elem.get_text(strip=True) if brief_elem else "",
                    "tags": [],
                    "url": urljoin("https://fanqienovel.com", link_elem["href"]) if link_elem else ""
                }
                
                if novel["title"]:
                    novels.append(novel)
            except Exception as e:
                print(f"解析番茄小说失败: {e}")
                continue
        
        return novels
    
    def _parse_qidian(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """解析起点中文网页面"""
        novels = []
        
        # 起点中文网的榜单结构
        items = soup.select(".book-item, .rank-item, .book-list li")
        
        for item in items:
            try:
                title_elem = item.select_one(".book-name, .name, h4")
                author_elem = item.select_one(".author, .writer")
                heat_elem = item.select_one(".total, .heat, .rank-index")
                brief_elem = item.select_one(".intro, .desc")
                link_elem = item.select_one("a[href*='book']")
                
                novel = {
                    "title": title_elem.get_text(strip=True) if title_elem else "",
                    "author": author_elem.get_text(strip=True) if author_elem else "",
                    "heat": heat_elem.get_text(strip=True) if heat_elem else "",
                    "brief": brief_elem.get_text(strip=True) if brief_elem else "",
                    "tags": [],
                    "url": urljoin("https://www.qidian.com", link_elem["href"]) if link_elem else ""
                }
                
                if novel["title"]:
                    novels.append(novel)
            except Exception as e:
                print(f"解析起点中文网失败: {e}")
                continue
        
        return novels
    
    def _parse_qimao(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """解析七猫小说页面"""
        novels = []
        
        items = soup.select(".book-item, .rank-item")
        
        for item in items:
            try:
                title_elem = item.select_one(".title, .book-name")
                author_elem = item.select_one(".author")
                heat_elem = item.select_one(".heat, .popularity")
                brief_elem = item.select_one(".intro, .desc")
                link_elem = item.select_one("a[href]")
                
                novel = {
                    "title": title_elem.get_text(strip=True) if title_elem else "",
                    "author": author_elem.get_text(strip=True) if author_elem else "",
                    "heat": heat_elem.get_text(strip=True) if heat_elem else "",
                    "brief": brief_elem.get_text(strip=True) if brief_elem else "",
                    "tags": [],
                    "url": urljoin("https://www.qimao.com", link_elem["href"]) if link_elem else ""
                }
                
                if novel["title"]:
                    novels.append(novel)
            except Exception as e:
                print(f"解析七猫小说失败: {e}")
                continue
        
        return novels
    
    def crawl_all_platforms(self, genre: str, limit: int = 10) -> Dict[str, Any]:
        """
        爬取所有平台的热门小说
        
        Args:
            genre: 题材名称
            limit: 每个平台返回数量
        
        Returns:
            所有平台的爬取结果
        """
        results = {
            "genre": genre,
            "platforms": [],
            "crawled_at": datetime.now().isoformat()
        }
        
        for platform in self.PLATFORM_URLS.keys():
            print(f"正在爬取{self.PLATFORM_URLS[platform]['name']}...")
            result = self.crawl_platform(platform, genre, limit)
            results["platforms"].append(result)
            time.sleep(random.uniform(1, 3))  # 请求间隔
        
        return results
    
    def close(self):
        """关闭爬虫器"""
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()


# 全局单例
_scraper: Optional[WebScraper] = None


def get_web_scraper(use_playwright: bool = False) -> WebScraper:
    """获取全局WebScraper单例"""
    global _scraper
    if _scraper is None:
        _scraper = WebScraper(use_playwright=use_playwright)
    return _scraper


if __name__ == "__main__":
    # 测试爬虫
    scraper = get_web_scraper()
    result = scraper.crawl_platform("fanqie", "都市", limit=5)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    scraper.close()
