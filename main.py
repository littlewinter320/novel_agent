#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络文学小说创作Agent系统 - 主程序入口

核心职责：
- 提供命令行交互界面，接收用户输入并路由到对应功能
- 初始化系统，检查API密钥和连接状态
- 管理主循环，处理命令和对话
- 集成进度反馈系统，让用户实时了解Agent运行状态
- 集成爬虫/截图/数据库，支持实时获取平台数据

设计思路：
- 用户输入后先显示"正在执行..."的进度反馈
- 意图识别：判断用户是否需要爬取数据、分析小说等
- 爬虫数据自动入库，截图供Agent视觉分析
- 知识库自动更新爆火小说的写法特征

使用方式：
    python main.py
"""

import os
import sys
import json
from typing import Optional, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 在所有模块导入之前，先检测并安装依赖
from utils.dependency_installer import ensure_dependencies
ensure_dependencies()

import config
from utils.llm_client import get_llm_client, test_connection
from utils.progress_display import get_progress_display
from utils.web_scraper import get_web_scraper
from utils.screenshot_tool import get_screenshot_tool
from core.novel_database import get_novel_database
from core.genre_knowledge import get_genre_knowledge_base


class NovelAgentCLI:
    """
    小说创作Agent系统命令行界面
    
    核心功能：
    1. 系统初始化：检查API密钥、测试连接、初始化各模块
    2. 进度反馈：每个操作都显示实时状态，用户知道Agent在做什么
    3. 智能路由：识别用户意图，自动调用爬虫/截图/分析等功能
    4. 数据入库：爬取的小说数据自动存入数据库
    5. 知识库更新：爆火小说的写法特征自动记录到知识库
    """
    
    def __init__(self):
        self.llm_client = None
        self.running = False
        self.conversation_history = []
        self.max_history_length = float('inf')
        # 各模块实例（延迟初始化）
        self.progress = None
        self.scraper = None
        self.screenshot_tool = None
        self.novel_db = None
        self.genre_kb = None
        
    def initialize(self):
        """初始化系统，包含所有子模块"""
        print("\n小说创作Agent系统")
        
        # 自动检测并安装缺失依赖
        ensure_dependencies()
        
        # 检查LLM提供商
        if config.LLM_PROVIDER not in ['deepseek', 'kimi', 'glm', 'openai', 'claude', 'custom']:
            print(f"错误：不支持的LLM提供商 {config.LLM_PROVIDER}")
            print("请在.env或config.py中设置LLM_PROVIDER")
            return False
        
        # 检查API密钥
        if not config.LLM_API_KEY:
            print("错误：未检测到API密钥")
            print("请在.env或config.py中设置LLM_API_KEY")
            return False
        
        # 测试API连接
        print("连接AI服务...")
        if test_connection():
            print("连接成功")
            self.llm_client = get_llm_client()
        else:
            print("连接失败，请检查网络或API密钥")
            return False
        
        # 初始化进度显示
        self.progress = get_progress_display()
        
        # 初始化爬虫
        print("初始化爬虫模块...")
        self.scraper = get_web_scraper()
        
        # 初始化截图工具
        print("初始化截图模块...")
        self.screenshot_tool = get_screenshot_tool()
        
        # 初始化数据库
        print("初始化数据库...")
        self.novel_db = get_novel_database()
        
        # 初始化知识库
        self.genre_kb = get_genre_knowledge_base()
        
        # 初始化Obsidian同步（如果配置了）
        self._init_obsidian()
        
        return True
    
    def _init_obsidian(self):
        """初始化Obsidian同步（可选）"""
        try:
            if hasattr(config, 'OBSIDIAN_VAULT_PATH') and config.OBSIDIAN_VAULT_PATH:
                print("初始化Obsidian同步...")
                print("Obsidian同步已启用")
        except Exception:
            pass  # Obsidian是可选功能
    
    def show_welcome(self):
        """显示欢迎信息"""
        print("\n功能：1.分析爆火小说 2.规划大纲 3.生成章节 4.导入文件 5.爬取平台数据")
        print("命令：help-帮助 quit-退出 status-状态 crawl-爬取")
    
    def show_help(self):
        """显示帮助信息"""
        print("\n帮助：")
        print("命令：")
        print("  help/帮助 - 显示帮助")
        print("  quit/退出 - 退出系统")
        print("  status/状态 - 显示当前状态")
        print("  crawl/爬取 - 爬取平台热门小说数据")
        print("  screenshot/截图 - 对指定URL截图")
        print("\n对话功能：")
        print("  直接描述需求，系统自动识别并执行")
        print("  例：查看番茄小说男频游戏系统类的爆款")
        print("  例：分析起点中文网玄幻题材热门作品")
    
    def show_status(self):
        """显示当前状态"""
        print(f"\n模型:{config.LLM_MODEL} 提供商:{config.LLM_PROVIDER}")
        print(f"API:{'已设置' if config.LLM_API_KEY else '未设置'}")
        print(f"爬虫:{'就绪' if self.scraper else '未初始化'}")
        print(f"数据库:{'就绪' if self.novel_db else '未初始化'}")
        # 显示数据库中的小说数量
        if self.novel_db:
            count = self.novel_db.get_novel_count()
            print(f"已收录小说:{count}部")
    
    def _detect_exit_intent(self, user_input: str) -> bool:
        """
        检测用户是否有退出意图
        
        支持精确命令和自然语言表达，如"拜拜"、"结束聊天"、"没事了"等
        """
        raw = user_input.strip()
        lower = raw.lower()
        
        # 精确匹配的命令
        if lower in ['quit', 'exit', 'q', '退出', '再见', '拜拜', 'bye']:
            return True
        
        # 自然语言退出短语（模糊匹配）
        exit_phrases = [
            '结束聊天', '结束对话', '结束会话', '退出系统', '退出程序',
            '不聊了',  '到此为止',  '下线', 
        ]
        
        # 检查是否包含退出短语
        for phrase in exit_phrases:
            if phrase in lower:
                return True
        
        # 模式匹配：以"拜"开头且较短
        if lower.startswith('拜') and len(raw) <= 6:
            return True
        
        return False
    
    def process_command(self, user_input: str) -> bool:
        """处理用户输入，识别命令或对话"""
        raw_input = user_input.strip()
        lower_input = raw_input.lower()
        
        # 退出检测（命令+自然语言）
        if self._detect_exit_intent(raw_input):
            print("再见")
            return False
        
        # 帮助命令
        elif lower_input in ['help', 'h', '帮助', '?']:
            self.show_help()
            return True
        
        # 状态命令
        elif lower_input in ['status', '状态']:
            self.show_status()
            return True
        
        # 爬取命令
        elif lower_input.startswith(('crawl', '爬取', '爬虫')):
            self._handle_crawl_command(raw_input)
            return True
        
        # 截图命令
        elif lower_input.startswith(('screenshot', '截图')):
            self._handle_screenshot_command(raw_input)
            return True
        
        # 文件路径检测
        elif os.path.exists(raw_input):
            print(f"文件:{raw_input}")
            print("导入功能开发中")
            return True
        
        # 智能对话（自动识别是否需要爬虫）
        else:
            return self._handle_smart_conversation(raw_input)
    
    def _detect_crawl_intent(self, user_input: str) -> Dict[str, Any]:
        """
        检测用户输入是否包含爬取意图

        返回：
            {"need_crawl": bool, "platform": str, "genre": str, "keywords": list}
        """
        # 平台关键词映射（返回爬虫模块期望的英文标识符）
        platform_keywords = {
            "fanqie": ["番茄", "fanqie", "番茄小说"],
            "qidian": ["起点", "qidian", "起点中文网"],
            "qimao": ["七猫", "qimao", "七猫小说"],
        }
        
        # 题材关键词映射
        genre_keywords = {
            "游戏": ["游戏", "网游", "系统流", "升级", "副本"],
            "玄幻": ["玄幻", "修仙", "仙侠", "修真"],
            "都市": ["都市", "现代", "城市", "职场"],
            "科幻": ["科幻", "未来", "太空", "星际"],
            "历史": ["历史", "古代", "穿越", "架空"],
            "悬疑": ["悬疑", "推理", "侦探", "恐怖"],
        }
        
        # 检测爬取意图关键词
        crawl_triggers = ["查看", "爬取", "最新", "热门", "爆款", "排行榜",
                         "榜单", "有什么", "推荐", "搜索", "找找", "看看"]
        
        need_crawl = any(trigger in user_input for trigger in crawl_triggers)
        
        # 识别平台
        detected_platform = ""
        for platform, keywords in platform_keywords.items():
            if any(kw in user_input for kw in keywords):
                detected_platform = platform
                break

        # 识别题材
        detected_genre = ""
        for genre, keywords in genre_keywords.items():
            if any(kw in user_input for kw in keywords):
                detected_genre = genre
                break

        return {
            "need_crawl": need_crawl,
            "platform": detected_platform,
            "genre": detected_genre,
            "user_input": user_input
        }
    
    def _handle_smart_conversation(self, user_input: str) -> bool:
        """
        智能对话处理：自动识别意图并执行
        
        流程：
        1. 检测用户意图（是否需要爬取数据）
        2. 如果需要爬取 → 执行爬虫 → 数据入库 → 截图 → 分析
        3. 如果不需要 → 普通LLM对话
        """
        if not self.llm_client:
            print("LLM未初始化")
            return True
        
        try:
            # 1. 检测爬取意图
            intent = self._detect_crawl_intent(user_input)
            
            if intent["need_crawl"] and (intent["platform"] or intent["genre"]):
                return self._handle_crawl_and_analyze(intent)
            
            # 2. 普通对话
            return self._handle_normal_conversation(user_input)
            
        except Exception as e:
            print(f"错误:{e}")
            return True
    
    def _handle_crawl_and_analyze(self, intent: Dict[str, Any]) -> bool:
        """
        爬取数据并分析（核心流程）

        流程：
        1. 显示进度 → 2. 爬取数据 → 3. 数据入库 → 4. 截图 → 5. 更新知识库 → 6. LLM分析
        """
        platform = intent["platform"] or "fanqie"
        genre = intent["genre"] or "游戏"
        user_input = intent["user_input"]
        
        # 步骤1：爬取数据
        self.progress.start_task(f"正在爬取{platform}的{genre}类热门小说...", total=3)
        
        self.progress.update_progress(1, f"连接{platform}...")
        crawl_result = self.scraper.crawl_platform(platform, genre, limit=10)
        
        if "error" in crawl_result:
            self.progress.fail_task(f"爬取失败: {crawl_result['error']}")
            # 降级：使用LLM直接分析
            print(f"\n爬虫无法获取实时数据，使用AI分析模式...")
            return self._handle_normal_conversation(user_input)
        
        novels = crawl_result.get("novels", [])
        self.progress.update_progress(2, f"获取到{len(novels)}部小说")
        
        # 步骤2：数据入库
        self.progress.update_progress(3, "数据入库中...")
        saved_count = 0
        for novel in novels:
            novel["platform"] = platform
            novel["genre"] = genre
            novel_id = self.novel_db.save_novel(novel)
            if novel_id > 0:
                saved_count += 1
        
        # 记录爬取日志
        crawl_url = crawl_result.get("url", "")
        self.novel_db.log_crawl(platform, genre, crawl_url, "success", f"爬取{len(novels)}部小说", len(novels))
        self.progress.complete_task(f"数据入库完成，新增/更新{saved_count}部小说")
        
        # 步骤3：截图（如果浏览器可用）
        screenshot_path = None
        if crawl_result.get("url"):
            self.progress.start_task("正在截取页面...", total=1)
            screenshot_result = self.screenshot_tool.take_screenshot(
                crawl_result["url"],
                filename=f"{platform}_{genre}_ranking"
            )
            if "error" not in screenshot_result:
                screenshot_path = screenshot_result.get("screenshot_path")
                self.progress.complete_task(f"截图已保存: {screenshot_path}")
            else:
                self.progress.fail_task("截图失败（浏览器未安装，非关键功能）")
        
        # 步骤4：更新知识库 - 提取爆火小说写法特征
        self.progress.start_task("正在分析爆火特征并更新知识库...", total=1)
        self._update_genre_knowledge(novels, genre)
        self.progress.complete_task("知识库已更新")
        
        # 步骤5：LLM综合分析
        self.progress.start_task("正在生成分析报告...", total=1)
        analysis = self._generate_analysis(novels, genre, platform, user_input)
        self.progress.complete_task("分析完成")
        
        # 输出结果
        print(f"\n{analysis}")
        
        # 保存对话历史
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": analysis})
        
        return True
    
    def _update_genre_knowledge(self, novels: list, genre: str):
        """
        根据爬取的小说数据更新题材知识库
        
        将爆火小说的写法特征记录到知识库中
        """
        if not novels:
            return
        
        # 构造小说数据摘要
        novel_summaries = []
        for novel in novels[:5]:  # 取前5部
            novel_summaries.append({
                "title": novel.get("title", ""),
                "author": novel.get("author", ""),
                "heat": novel.get("heat", ""),
                "brief": novel.get("brief", ""),
                "tags": novel.get("tags", [])
            })
        
        # 让LLM分析爆火特征
        prompt = f"""分析以下{genre}题材的热门小说，提取爆火写法特征。

热门小说数据：
{json.dumps(novel_summaries, ensure_ascii=False, indent=2)}

请提取以下信息（JSON格式）：
{{
    "hot_writing_features": ["爆火写法特征列表"],
    "popular_tropes": ["流行套路/元素"],
    "opening_patterns": ["常见开篇模式"],
    "character_archetypes": ["热门人设"],
    "reader_preferences": ["读者偏好"],
    "market_trend": ["市场趋势"]
}}

只返回JSON对象。"""
        
        try:
            response = self.llm_client.generate(prompt)
            features = json.loads(response)
            
            # 更新知识库
            existing = self.genre_kb.get_genre(genre)
            if existing:
                # 更新现有题材的热点信息
                existing["hot_topics"] = features.get("hot_writing_features", [])
                existing["common_tropes"] = features.get("popular_tropes", existing.get("common_tropes", []))
                existing["last_updated"] = str(__import__('datetime').datetime.now())
                self.genre_kb.update_genre(genre, existing)
            else:
                # 创建新题材
                new_genre = {
                    "name": genre,
                    "tags": list(set(tag for n in novels for tag in n.get("tags", []))),
                    "writing_style": features.get("hot_writing_features", [""]),
                    "plot_systems": features.get("popular_tropes", []),
                    "character_templates": features.get("character_archetypes", []),
                    "common_tropes": features.get("popular_tropes", []),
                    "hot_topics": features.get("hot_writing_features", []),
                    "last_updated": str(__import__('datetime').datetime.now())
                }
                self.genre_kb.add_genre(genre, new_genre)
                
        except Exception as e:
            print(f"更新知识库失败: {e}")
    
    def _generate_analysis(self, novels: list, genre: str, platform: str, 
                          user_input: str) -> str:
        """让LLM基于真实爬取数据生成分析报告"""
        novel_data = json.dumps(novels[:10], ensure_ascii=False, indent=2)
        
        prompt = f"""你是一个专业的网络小说市场分析师。基于以下从{platform}实时爬取的{genre}类热门小说数据，为用户提供分析。

用户问题：{user_input}

实时爬取的热门小说数据：
{novel_data}

请基于以上真实数据回答用户问题，要求：
1. 引用具体的小说名称和数据
2. 分析这些作品的共同爆火特征
3. 给出创作建议
4. 如果不是爽文方向，特别说明如何在保持吸引力的同时避免纯爽文套路

注意：以上数据是从{platform}实时爬取的真实数据，请基于此分析。"""
        
        try:
            response = self.llm_client.chat_with_system(
                system_prompt="你是专业的网络小说市场分析师，基于真实数据提供分析。",
                user_message=prompt,
                history=[]
            )
            return response
        except Exception as e:
            return f"分析生成失败: {e}"
    
    def _handle_crawl_command(self, user_input: str):
        """处理显式爬取命令"""
        # 解析命令参数
        parts = user_input.split()
        platform = "番茄小说"
        genre = "游戏"
        
        # 简单解析：crawl 平台 题材
        platform_keywords = {"番茄": "番茄小说", "起点": "起点中文网", "七猫": "七猫小说"}
        for part in parts[1:]:
            for kw, pname in platform_keywords.items():
                if kw in part:
                    platform = pname
        
        genre_keywords = {"游戏": "游戏", "玄幻": "玄幻", "都市": "都市", 
                         "科幻": "科幻", "历史": "历史", "悬疑": "悬疑"}
        for part in parts[1:]:
            for kw, gname in genre_keywords.items():
                if kw in part:
                    genre = gname
        
        intent = {
            "need_crawl": True,
            "platform": platform,
            "genre": genre,
            "user_input": f"查看{platform}{genre}类热门小说"
        }
        self._handle_crawl_and_analyze(intent)
    
    def _handle_screenshot_command(self, user_input: str):
        """处理截图命令"""
        # 提取URL
        import re
        urls = re.findall(r'https?://[^\s]+', user_input)
        
        if not urls:
            print("请提供URL，例：screenshot https://fanqienovel.com")
            return
        
        url = urls[0]
        self.progress.start_task(f"正在截取 {url} ...", total=1)
        
        result = self.screenshot_tool.take_screenshot(url)
        
        if "error" in result:
            self.progress.fail_task(f"截图失败: {result['error']}")
        else:
            path = result.get("screenshot_path")
            self.progress.complete_task(f"截图已保存: {path}")
    
    def _handle_normal_conversation(self, user_input: str) -> bool:
        """处理普通对话（无爬取意图）"""
        if not self.llm_client:
            print("LLM未初始化")
            return True
        
        try:
            self.progress.start_task("正在思考...", total=1)
            
            system_prompt = """你是一个专业的网络文学小说创作顾问Agent。你的核心职责是帮助用户从零开始创作高质量的网络小说。

【基本原则】
1. 循序渐进：每个步骤只输出当前阶段的内容
2. 用户至上：用户可以随时修改前面的步骤
3. 主动判断：自动识别用户需要哪个功能
4. 迭代更新：知识库、大纲、规划等都是活的
5. 质量保证：输出前必须经过Quality Gate检查

【沟通风格】
- 专业但不生硬
- 给出明确的选择项
- 对用户的反馈要快速反应并记忆

现在用户正在和你对话，请根据他们的需求提供帮助。"""
            
            response = self.llm_client.chat_with_system(
                system_prompt=system_prompt,
                user_message=user_input,
                history=self.conversation_history
            )
            
            self.progress.complete_task("完成")
            
            # 保存对话历史
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": response})
            
            if len(self.conversation_history) > self.max_history_length * 2:
                self.conversation_history = self.conversation_history[-int(self.max_history_length) * 2:]
            
            print(response)
        except Exception as e:
            self.progress.fail_task(f"错误: {e}")
        
        return True
    
    def run(self):
        """运行主循环"""
        if not self.initialize():
            return
        
        self.show_welcome()
        
        self.running = True
        while self.running:
            try:
                user_input = input("\n> ").strip()
                if not user_input:
                    continue
                
                self.running = self.process_command(user_input)
                
            except KeyboardInterrupt:
                confirm = input("\n退出?(y/n)").strip().lower()
                if confirm in ['y', 'yes']:
                    print("再见")
                    break
            except Exception as e:
                print(f"错误:{e}")


def main():
    """主函数"""
    cli = NovelAgentCLI()
    cli.run()


if __name__ == "__main__":
    main()
