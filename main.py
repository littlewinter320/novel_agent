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
            print("请在config.py中设置LLM_PROVIDER")
            return False
        
        # 检查API密钥
        if not config.LLM_API_KEY:
            print("错误：未检测到API密钥")
            print("请在config.py中设置LLM_API_KEY")
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
        检测用户输入是否包含爬取或搜索意图

        返回：
            {
                "need_crawl": bool,           # 是否需要爬取/搜索
                "search_type": str,           # search_type: "keyword" | "ranking" | "normal"
                "platform": str,              # 平台（fanqie/qidian/qimao）
                "genre": str,                 # 题材
                "length": str,                # 篇幅（短篇/中篇/长篇）
                "keywords": list,             # 用户输入的搜索关键词
                "user_input": str             # 原始用户输入
            }
        """
        # 平台关键词映射（返回爬虫模块期望的英文标识符）
        platform_keywords = {
            "fanqie": ["番茄", "fanqie", "番茄小说", "番茄网"],
            "qidian": ["起点", "qidian", "起点中文网", "起点网"],
            "qimao": ["七猫", "qimao", "七猫小说", "七猫网"],
        }
        
        # 题材关键词映射（扩充更多口语化表达）
        genre_keywords = {
            "游戏": ["游戏", "网游", "系统流", "升级", "副本", "电竞", "网游之"],
            "玄幻": ["玄幻", "修仙", "仙侠", "修真", "玄幻小说", "修仙小说"],
            "都市": ["都市", "现代", "城市", "职场", "都市小说", "现代都市"],
            "科幻": ["科幻", "未来", "太空", "星际", "科幻小说", "末世"],
            "历史": ["历史", "古代", "穿越", "架空", "历史小说", "古代言情"],
            "悬疑": ["悬疑", "推理", "侦探", "恐怖", "悬疑小说", "惊悚"],
            "言情": ["言情", "爱情", "甜宠", "虐恋", "言情小说"],
            "重生": ["重生", "重生之", "重生小说"],
            "穿越": ["穿越", "穿越小说", "穿越时空"],
            "宫斗": ["宫斗", "宫斗小说"],
            "宅斗": ["宅斗", "宅斗小说"],
            "古言": ["古言", "古代言情"],
        }

        # 篇幅约束映射
        # 短篇: ≤50万字  中篇: 50~200万字  长篇: ≥200万字
        length_keywords = {
            "短篇": ["短篇", "短一点", "不要太长", "字数少", "50万以内", "50万字以内", "短篇小说"],
            "中篇": ["中篇", "中等长度", "100万字", "100~200万", "中篇小说"],
            "长篇": ["长篇", "长篇大论", "200万字", "200万字以上", "长篇小说"],
        }

        # 扩充触发词列表，支持更多口语化表达
        # 意图词 + 领域词的组合方式，提高识别准确率
        intent_triggers = [
            # 意图词：表示用户想要做什么
            "查看", "爬取", "最新", "热门", "爆款", "排行榜", "榜单",
            "有什么", "推荐", "搜索", "找找", "看看", "寻找", "找",
            "匹配", "筛选", "查询", "搜索一下", "搜搜", "搜",
            "想看", "想读", "了解", "了解一下", "关注",
            # 领域词：表示用户关注的领域
            "小说", "书", "网文", "作品", "书籍",
            # 组合表达
            "有什么好看的", "有什么推荐", "推荐几本",
            "什么好看", "哪本好看", "热门的", "最近火的",
        ]

        # 检测是否有爬取/搜索意图
        has_intent = any(trigger in user_input for trigger in intent_triggers)

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

        # 识别篇幅约束
        detected_length = ""
        for length, keywords in length_keywords.items():
            if any(kw in user_input for kw in keywords):
                detected_length = length
                break

        # 提取用户输入中的搜索关键词（去除已识别的平台/题材/篇幅词）
        # 保留用户真正想搜索的内容
        all_known_keywords = set()
        for keywords in platform_keywords.values():
            all_known_keywords.update(keywords)
        for keywords in genre_keywords.values():
            all_known_keywords.update(keywords)
        for keywords in length_keywords.values():
            all_known_keywords.update(keywords)
        all_known_keywords.update(intent_triggers)

        # 从用户输入中提取真正的搜索关键词
        import re
        # 先去除常见标点和空格
        clean_input = re.sub(r'[，。！？、；：\s]+', ' ', user_input).strip()
        # 去除已识别的关键词，保留剩余部分作为搜索关键词
        remaining = clean_input
        for kw in sorted(all_known_keywords, key=len, reverse=True):
            remaining = remaining.replace(kw, '')
        # 去除多余空格
        remaining = ' '.join(remaining.split()).strip()

        # 判断搜索类型
        # 1. 如果有剩余关键词，优先按关键词搜索
        # 2. 如果只有题材+平台，按榜单爬取
        # 3. 否则为普通对话
        search_type = "normal"
        search_keywords = []
        
        if remaining:
            # 用户有明确的搜索词（如"末日生存"、"无敌流"等）
            search_type = "keyword"
            search_keywords = [remaining]
            # 如果剩余词太长，尝试按标点分割成多个关键词
            if len(remaining) > 10:
                search_keywords = re.split(r'[，。！？、；：\s]+', user_input)
                search_keywords = [k.strip() for k in search_keywords if k.strip()]
                # 过滤掉已知关键词
                search_keywords = [k for k in search_keywords if k not in all_known_keywords]
        elif has_intent and (detected_genre or detected_platform):
            # 用户只提到了题材或平台，按榜单爬取
            search_type = "ranking"

        return {
            "need_crawl": has_intent,
            "search_type": search_type,
            "platform": detected_platform,
            "genre": detected_genre,
            "length": detected_length,
            "keywords": search_keywords,
            "user_input": user_input
        }
    
    def _handle_smart_conversation(self, user_input: str) -> bool:
        """
        智能对话处理：自动识别意图并执行
        
        流程：
        1. 检测用户意图（关键词搜索 / 榜单爬取 / 普通对话）
        2. 关键词搜索：优先使用用户提供的词进行联网搜索
        3. 榜单爬取：根据平台+题材爬取排行榜数据
        4. 普通对话：直接使用LLM回复
        """
        if not self.llm_client:
            print("LLM未初始化")
            return True
        
        try:
            # 1. 检测爬取/搜索意图
            intent = self._detect_crawl_intent(user_input)
            
            # 2. 根据搜索类型执行不同策略
            # 优先级：关键词搜索 > 榜单爬取 > 普通对话
            if intent["search_type"] == "keyword":
                # 用户提供了明确的搜索关键词，优先联网搜索
                return self._handle_keyword_search(intent)
            elif intent["search_type"] == "ranking" and (intent["platform"] or intent["genre"]):
                # 用户只提到平台或题材，爬取排行榜
                return self._handle_crawl_and_analyze(intent)
            elif intent["need_crawl"]:
                # 有爬取意图但未明确搜索类型，尝试关键词搜索或降级到榜单
                if intent["keywords"]:
                    return self._handle_keyword_search(intent)
                elif intent["platform"] or intent["genre"]:
                    return self._handle_crawl_and_analyze(intent)
            
            # 3. 普通对话
            return self._handle_normal_conversation(user_input)
            
        except Exception as e:
            print(f"错误:{e}")
            return True
    
    def _handle_keyword_search(self, intent: Dict[str, Any]) -> bool:
        """
        根据用户提供的关键词进行联网搜索（核心优化：支持任意关键词搜索）
        
        流程：
        1. 显示进度 → 2. 使用用户关键词联网搜索 → 3. 数据入库 → 4. 截图 → 5. 篇幅筛选 → 6. LLM分析
        """
        platform = intent["platform"] or "fanqie"
        keywords = intent["keywords"] or []
        user_input = intent["user_input"]
        length = intent.get("length", "")
        
        # 如果没有关键词，尝试从用户输入中提取
        if not keywords:
            keywords = [user_input]
        
        # 使用第一个关键词进行搜索（可以扩展为多关键词搜索）
        search_keyword = keywords[0]

        # 步骤1：使用关键词搜索
        self.progress.start_task(f"正在搜索关键词「{search_keyword}」...", total=3)
        
        self.progress.update_progress(1, f"连接{platform}搜索...")
        search_result = self.scraper.search_by_keyword(platform, search_keyword, limit=10)

        if "error" in search_result:
            self.progress.fail_task(f"搜索失败: {search_result['error']}")
            # 降级：使用LLM直接分析或尝试榜单爬取
            print(f"\n无法通过关键词搜索获取数据，尝试其他方式...")
            # 如果有关联题材，尝试按题材爬取榜单
            if intent.get("genre"):
                intent["search_type"] = "ranking"
                return self._handle_crawl_and_analyze(intent)
            return self._handle_normal_conversation(user_input)

        novels = search_result.get("novels", [])
        self.progress.update_progress(2, f"搜索到{len(novels)}部相关小说")

        # 步骤2：数据入库
        self.progress.update_progress(3, "数据入库中...")
        saved_count = 0
        for novel in novels:
            novel["platform"] = platform
            novel["genre"] = intent.get("genre", "")
            novel_id = self.novel_db.save_novel(novel)
            if novel_id > 0:
                saved_count += 1

        # 记录爬取日志
        search_url = search_result.get("url", "")
        self.novel_db.log_crawl(platform, f"搜索:{search_keyword}", search_url, "success", f"搜索{len(novels)}部小说", len(novels))
        self.progress.complete_task(f"数据入库完成，新增/更新{saved_count}部小说")

        # 步骤3：截图（如果浏览器可用）
        screenshot_path = None
        if search_result.get("url"):
            self.progress.start_task("正在截取搜索结果页面...", total=1)
            screenshot_result = self.screenshot_tool.take_screenshot(
                search_result["url"],
                filename=f"{platform}_search_{search_keyword[:10]}"
            )
            if "error" not in screenshot_result:
                screenshot_path = screenshot_result.get("screenshot_path")
                self.progress.complete_task(f"截图已保存: {screenshot_path}")
            else:
                self.progress.fail_task("截图失败（浏览器未安装，非关键功能）")

        # 步骤4：根据篇幅要求筛选小说
        if length:
            self.progress.start_task(f"正在筛选{length}小说...", total=1)
            filtered_novels = self._filter_novels_by_length(novels, length)
            if filtered_novels:
                self.progress.complete_task(f"筛选完成，找到{len(filtered_novels)}部符合条件的小说")
                novels = filtered_novels
            else:
                self.progress.fail_task(f"未找到符合{length}要求的小说")

        # 步骤5：LLM综合分析
        self.progress.start_task("正在生成分析报告...", total=1)
        analysis = self._generate_keyword_analysis(novels, search_keyword, platform, user_input, length)
        self.progress.complete_task("分析完成")

        # 输出结果
        print(f"\n{analysis}")

        # 保存对话历史
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": analysis})

        return True
    
    def _generate_keyword_analysis(self, novels: list, keyword: str, platform: str,
                                  user_input: str, length: str = "") -> str:
        """让LLM基于关键词搜索结果生成分析报告"""
        novel_data = json.dumps(novels[:10], ensure_ascii=False, indent=2)

        # 构建篇幅约束说明
        length_constraint = ""
        if length == "短篇":
            length_constraint = """
【重要约束】用户要求短篇作品（≤50万字）。
**关键要求**：
- 如果小说数据中有 `word_count` 字段，必须严格筛选字数≤50万字的作品
- 如果数据中**没有字数信息**，你必须在回答开头明确声明："**注意：爬取的数据中未提供字数信息，无法确定篇幅是否符合要求。以下推荐未经验证篇幅。**"
- 绝对不要假装知道字数，不要编造字数信息
"""
        elif length == "中篇":
            length_constraint = """
【重要约束】用户要求中篇作品（50-200万字）。
**关键要求**：
- 如果小说数据中有 `word_count` 字段，必须严格筛选字数在50-200万字之间的作品
- 如果数据中**没有字数信息**，你必须在回答开头明确声明："**注意：爬取的数据中未提供字数信息，无法确定篇幅是否符合要求。以下推荐未经验证篇幅。**"
- 绝对不要假装知道字数，不要编造字数信息
"""
        elif length == "长篇":
            length_constraint = """
【重要约束】用户要求长篇作品（≥200万字）。
**关键要求**：
- 如果小说数据中有 `word_count` 字段，必须严格筛选字数≥200万字的作品
- 如果数据中**没有字数信息**，你必须在回答开头明确声明："**注意：爬取的数据中未提供字数信息，无法确定篇幅是否符合要求。以下推荐未经验证篇幅。**"
- 绝对不要假装知道字数，不要编造字数信息
"""

        prompt = f"""你是一个专业的网络小说市场分析师。基于以下从{platform}实时搜索的「{keyword}」相关小说数据，为用户提供分析。

用户问题：{user_input}
{length_constraint}
实时搜索结果（关键词：{keyword}）：
{novel_data}

**重要检查**：
请先检查上述数据中每部小说是否包含 `word_count` 字段。
- 如果所有小说都**没有** `word_count` 字段，你必须在回答的**第一行**用粗体声明："**注意：爬取的数据中未提供字数信息，无法按篇幅筛选。以下推荐未经验证篇幅。**"
- 如果部分小说有 `word_count`，只推荐符合篇幅要求的作品
- 绝对不要编造或猜测字数

请基于以上真实搜索数据回答用户问题，要求：
1. 引用具体的小说名称和数据
2. 分析这些作品与关键词「{keyword}」的关联性
3. 分析这些作品的共同爆火特征（如果有关键词相关的特征请特别指出）
4. 给出创作建议（特别是如何写好「{keyword}」相关的小说）
5. 如果不是爽文方向，特别说明如何在保持吸引力的同时避免纯爽文套路
6. 如果有篇幅约束且有字数数据，必须严格遵守并筛选符合要求的作品

注意：以上数据是从{platform}实时搜索的真实数据，请基于此分析。"""
        
        try:
            response = self.llm_client.chat_with_system(
                system_prompt="你是专业的网络小说市场分析师，基于真实搜索数据提供分析。",
                user_message=prompt,
                history=[]
            )
            return response
        except Exception as e:
            return f"分析生成失败: {e}"
    
    def _handle_crawl_and_analyze(self, intent: Dict[str, Any]) -> bool:
        """
        爬取数据并分析（核心流程）

        流程：
        1. 显示进度 → 2. 爬取数据 → 3. 数据入库 → 4. 截图 → 5. 更新知识库 → 6. 篇幅筛选 → 7. LLM分析
        """
        platform = intent["platform"] or "fanqie"
        genre = intent["genre"] or "游戏"
        user_input = intent["user_input"]
        length = intent.get("length", "")

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

        # 步骤5：根据篇幅要求筛选小说
        if length:
            self.progress.start_task(f"正在筛选{length}小说...", total=1)
            filtered_novels = self._filter_novels_by_length(novels, length)
            if filtered_novels:
                self.progress.complete_task(f"筛选完成，找到{len(filtered_novels)}部符合条件的小说")
                novels = filtered_novels
            else:
                self.progress.fail_task(f"未找到符合{length}要求的小说")
                # 即使筛选失败，也继续分析，让LLM说明情况

        # 步骤6：LLM综合分析
        self.progress.start_task("正在生成分析报告...", total=1)
        analysis = self._generate_analysis(novels, genre, platform, user_input, length)
        self.progress.complete_task("分析完成")

        # 输出结果
        print(f"\n{analysis}")

        # 保存对话历史
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": analysis})

        return True

    def _parse_word_count(self, word_count_str: str) -> int:
        """
        解析字数字符串为数字（单位：万字）

        Args:
            word_count_str: 字数字符串，如"50万字"、"100万"、"2000000字"

        Returns:
            字数（万字），解析失败返回0
        """
        if not word_count_str:
            return 0

        import re

        # 匹配"X万字"或"X万"
        match = re.search(r'(\d+(?:\.\d+)?)\s*万', word_count_str)
        if match:
            return float(match.group(1))

        # 匹配"X字"（转换为万字）
        match = re.search(r'(\d+)\s*字', word_count_str)
        if match:
            return int(match.group(1)) / 10000

        return 0

    def _filter_novels_by_length(self, novels: list, length: str) -> list:
        """
        根据篇幅要求筛选小说

        Args:
            novels: 小说列表
            length: 篇幅要求（短篇/中篇/长篇）

        Returns:
            筛选后的小说列表
        """
        if not length:
            return novels

        # 篇幅范围定义（单位：万字）
        length_ranges = {
            "短篇": (0, 50),      # ≤50万字
            "中篇": (50, 200),    # 50-200万字
            "长篇": (200, float('inf'))  # ≥200万字
        }

        if length not in length_ranges:
            return novels

        min_words, max_words = length_ranges[length]
        filtered = []

        for novel in novels:
            word_count_str = novel.get("word_count", "")
            word_count = self._parse_word_count(word_count_str)

            # 如果有字数信息，进行筛选
            if word_count > 0:
                if min_words <= word_count <= max_words:
                    filtered.append(novel)
            # 如果没有字数信息，暂时保留，让LLM判断
            # 但标记为"字数未知"
            else:
                novel["word_count_note"] = "字数未知"
                filtered.append(novel)

        return filtered
    
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
                          user_input: str, length: str = "") -> str:
        """让LLM基于真实爬取数据生成分析报告"""
        novel_data = json.dumps(novels[:10], ensure_ascii=False, indent=2)

        # 构建篇幅约束说明
        length_constraint = ""
        if length == "短篇":
            length_constraint = """
【重要约束】用户要求短篇作品（≤50万字）。
**关键要求**：
- 如果小说数据中有 `word_count` 字段，必须严格筛选字数≤50万字的作品
- 如果数据中**没有字数信息**，你必须在回答开头明确声明："**注意：爬取的数据中未提供字数信息，无法确定篇幅是否符合要求。以下推荐未经验证篇幅。**"
- 绝对不要假装知道字数，不要编造字数信息
"""
        elif length == "中篇":
            length_constraint = """
【重要约束】用户要求中篇作品（50-200万字）。
**关键要求**：
- 如果小说数据中有 `word_count` 字段，必须严格筛选字数在50-200万字之间的作品
- 如果数据中**没有字数信息**，你必须在回答开头明确声明："**注意：爬取的数据中未提供字数信息，无法确定篇幅是否符合要求。以下推荐未经验证篇幅。**"
- 绝对不要假装知道字数，不要编造字数信息
"""
        elif length == "长篇":
            length_constraint = """
【重要约束】用户要求长篇作品（≥200万字）。
**关键要求**：
- 如果小说数据中有 `word_count` 字段，必须严格筛选字数≥200万字的作品
- 如果数据中**没有字数信息**，你必须在回答开头明确声明："**注意：爬取的数据中未提供字数信息，无法确定篇幅是否符合要求。以下推荐未经验证篇幅。**"
- 绝对不要假装知道字数，不要编造字数信息
"""

        prompt = f"""你是一个专业的网络小说市场分析师。基于以下从{platform}实时爬取的{genre}类热门小说数据，为用户提供分析。

用户问题：{user_input}
{length_constraint}
实时爬取的热门小说数据：
{novel_data}

**重要检查**：
请先检查上述数据中每部小说是否包含 `word_count` 字段。
- 如果所有小说都**没有** `word_count` 字段，你必须在回答的**第一行**用粗体声明："**注意：爬取的数据中未提供字数信息，无法按篇幅筛选。以下推荐未经验证篇幅。**"
- 如果部分小说有 `word_count`，只推荐符合篇幅要求的作品
- 绝对不要编造或猜测字数

请基于以上真实数据回答用户问题，要求：
1. 引用具体的小说名称和数据
2. 分析这些作品的共同爆火特征
3. 给出创作建议
4. 如果不是爽文方向，特别说明如何在保持吸引力的同时避免纯爽文套路
5. 如果有篇幅约束且有字数数据，必须严格遵守并筛选符合要求的作品

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
