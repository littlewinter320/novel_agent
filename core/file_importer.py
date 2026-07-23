"""
文件导入与解析模块

核心职责：
- 支持多种格式文件的导入（txt/md/docx/pdf）
- 使用NLP技术（jieba分词）提取人物、事件、伏笔等关键信息
- 分析文笔指纹（句式长度、对话占比、心理描写、常用词汇、叙事视角等）
- 将提取的信息注入真相文件体系，实现知识复用

设计思路：
- 采用多策略人物识别：jieba词性标注 + 复姓识别 + 对话模式匹配
- 事件提取基于关键词识别（突然、发现、决定等）
- 伏笔提取基于悬念关键词（秘密、隐藏、未知等）
- 文笔指纹分析提供6个维度的量化指标，用于风格学习

使用场景：
- 用户导入已有小说文件，系统自动提取人物关系和剧情脉络
- 导入参考作品，学习其写作风格和技巧
- 导入大纲文件，初始化真相文件体系

关键算法：
- 人物识别：jieba词性标注识别人名词(nr/nr1/nr2) + 复姓匹配 + 对话模式提取
- 复姓识别：支持14个常见复姓（欧阳、司马、上官等）
- 对话提取：3种对话模式匹配（李明："你好"、"你好"李明问道、李明说："你好"）
- 章节分割：基于正则表达式匹配章节标题
- 文笔指纹：6维度分析（句式长度、对话占比、心理描写、环境描写、常用词汇、叙事视角）

输出数据结构：
{
    "file_path": "文件路径",
    "metadata": {
        "file_name": "文件名",
        "file_type": ".txt",
        "file_size": 12345,
        "total_words": 5000,
        "chinese_chars": 4500,
        "english_words": 500,
        "chapter_count": 10,
        "paragraph_count": 100
    },
    "content": "完整文本内容",
    "characters": [
        {
            "name": "李明",
            "mention_count": 50,
            "descriptions": ["李明走在街道上", "李明觉得有些意外"]
        }
    ],
    "events": [
        {
            "chapter": "第一章",
            "chapter_index": 1,
            "key_events": ["突然，他看到了一个熟悉的身影"]
        }
    ],
    "foreshadows": [
        {
            "content": "关于那个传说中的宝藏",
            "keyword": "秘密",
            "type": "foreshadow"
        }
    ],
    "style_fingerprint": {
        "sentence_lengths": {"avg": 15.5, "min": 3, "max": 45},
        "dialogue_ratio": 0.25,
        "psychology_ratio": 0.15,
        "environment_ratio": 0.10,
        "common_words": [("知道", 100), ("觉得", 80)],
        "narrative_perspective": "third_person"
    }
}
"""
import os
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class FileImporter:
    """
    文件导入与解析器
    
    核心功能：
    1. 多格式支持：txt/md/docx/pdf文件读取
    2. 人物提取：使用jieba NLP识别角色名称和关系
    3. 事件提取：基于关键词识别关键剧情事件
    4. 伏笔提取：识别悬念和伏笔线索
    5. 文笔分析：6维度量化分析写作风格
    6. 真相注入：将提取信息注入真相文件体系
    
    设计特点：
    - 采用多策略人物识别，提高准确率
    - 支持复姓识别（欧阳、司马等）
    - 支持多种对话格式提取
    - 文笔指纹提供量化指标，支持风格学习
    - 自动注入真相文件，实现知识复用
    
    使用流程：
    1. 调用import_file(file_path)导入文件
    2. 系统自动提取人物、事件、伏笔、文笔指纹
    3. 调用inject_to_truth_files()注入真相文件
    4. 后续创作可复用导入的知识和风格
    """
    
    def __init__(self):
        """初始化文件导入器"""
        self.supported_formats = config.SUPPORTED_FILE_FORMATS
    
    def import_file(self, file_path: str) -> Dict[str, Any]:
        """导入文件并提取所有信息
        
        Args:
            file_path: 文件路径
        
        Returns:
            包含所有提取信息的字典
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in self.supported_formats:
            raise ValueError(f"不支持的文件格式: {file_ext}")
        
        # 读取文件内容
        content = self._read_file(file_path, file_ext)
        
        # 提取元信息
        metadata = self.extract_metadata(file_path, content)
        
        # 提取人物
        characters = self.extract_characters(content)
        
        # 提取事件
        events = self.extract_events(content)
        
        # 提取伏笔
        foreshadows = self.extract_foreshadows(content)
        
        # 分析文笔指纹
        style_fingerprint = self.analyze_style_fingerprint(content)
        
        return {
            "file_path": file_path,
            "metadata": metadata,
            "content": content,
            "characters": characters,
            "events": events,
            "foreshadows": foreshadows,
            "style_fingerprint": style_fingerprint
        }
    
    def _read_file(self, file_path: str, file_ext: str) -> str:
        """读取文件内容
        
        Args:
            file_path: 文件路径
            file_ext: 文件扩展名
        
        Returns:
            文件文本内容
        """
        if file_ext == ".txt" or file_ext == ".md":
            return self._read_text_file(file_path)
        elif file_ext == ".docx":
            return self._read_docx_file(file_path)
        elif file_ext == ".pdf":
            return self._read_pdf_file(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_ext}")
    
    def _read_text_file(self, file_path: str) -> str:
        """读取纯文本文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _read_docx_file(self, file_path: str) -> str:
        """读取Word文档"""
        try:
            from docx import Document
        except ImportError:
            raise ImportError("请安装python-docx: pip install python-docx")
        
        doc = Document(file_path)
        text_parts = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)
        return '\n'.join(text_parts)
    
    def _read_pdf_file(self, file_path: str) -> str:
        """读取PDF文档"""
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("请安装pdfplumber: pip install pdfplumber")
        
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return '\n'.join(text_parts)
    
    def extract_metadata(self, file_path: str, content: str) -> Dict[str, Any]:
        """提取文件元信息
        
        Args:
            file_path: 文件路径
            content: 文件内容
        
        Returns:
            元信息字典
        """
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # 统计字数（中文字符 + 英文单词）
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        english_words = len(re.findall(r'[a-zA-Z]+', content))
        total_words = chinese_chars + english_words
        
        # 统计章节数
        chapter_count = self._count_chapters(content)
        
        return {
            "file_name": file_name,
            "file_type": file_ext,
            "file_size": os.path.getsize(file_path),
            "total_words": total_words,
            "chinese_chars": chinese_chars,
            "english_words": english_words,
            "chapter_count": chapter_count,
            "paragraph_count": len([p for p in content.split('\n') if p.strip()])
        }
    
    def _count_chapters(self, content: str) -> int:
        """统计章节数"""
        # 匹配常见章节标题格式
        patterns = [
            r'第[一二三四五六七八九十百千\d]+[章节回]',
            r'Chapter\s+\d+',
            r'第\s*\d+\s*[章节回]',
        ]
        
        count = 0
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            count += len(matches)
        
        return max(count, 1) if content.strip() else 0
    
    def extract_characters(self, content: str) -> List[Dict[str, Any]]:
        """提取人物信息（使用jieba词性标注）
        
        Args:
            content: 文件内容
        
        Returns:
            人物列表
        """
        import jieba.posseg as pseg
        
        characters = []
        character_names = {}  # name -> count
        
        # 常见复姓列表
        compound_surnames = {
            '欧阳', '司马', '上官', '诸葛', '司徒', '令狐', '独孤', '慕容',
            '皇甫', '尉迟', '长孙', '宇文', '公孙', '夏侯'
        }
        
        # 1. 使用jieba进行词性标注，识别人名词(nr)
        words = pseg.cut(content)
        for word, flag in words:
            # nr: 人名, nr1: 汉语姓氏, nr2: 汉语名字
            if flag in ['nr', 'nr1', 'nr2']:
                name = word.strip()
                # 过滤：长度2-4，纯中文
                if 2 <= len(name) <= 4 and re.match(r'^[\u4e00-\u9fff]+$', name):
                    if not self._is_common_word(name):
                        character_names[name] = character_names.get(name, 0) + 1
        
        # 2. 识别复姓人名
        for surname in compound_surnames:
            pattern = rf'{surname}[\u4e00-\u9fff]{{1,2}}'
            matches = re.findall(pattern, content)
            for name in matches:
                if not self._is_common_word(name):
                    character_names[name] = character_names.get(name, 0) + len(matches)
        
        # 3. 提取对话中的人物（多种格式）
        dialogue_patterns = [
            r'([^\s""]{1,10})[：:]["""\'](.+?)["""\']',  # 李明："你好"
            r'["""\'](.+?)["""\'].*?(\S{1,10})(?:问道|说道|说|喊|叫)',  # "你好"李明问道
            r'(\S{2,4})(?:问道|说道|说|喊|叫|笑).*?["""\'](.+?)["""\']',  # 李明说："你好"
        ]
        
        for pattern in dialogue_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                name = match[0].strip() if match[0] else match[1].strip()
                if 2 <= len(name) <= 4 and re.match(r'^[\u4e00-\u9fff]+$', name):
                    if not self._is_common_word(name):
                        character_names[name] = character_names.get(name, 0) + 1
        
        # 4. 过滤：只保留出现次数>=2的人名
        character_names = {name: count for name, count in character_names.items() if count >= 2}
        
        # 5. 构建人物信息
        for name, mention_count in character_names.items():
            descriptions = self._extract_character_descriptions(name, content)
            
            characters.append({
                "name": name,
                "mention_count": mention_count,
                "descriptions": descriptions[:5]
            })
        
        # 6. 按提及次数排序
        characters.sort(key=lambda x: x["mention_count"], reverse=True)
        
        return characters
    
    def _is_likely_character_name(self, name: str, content: str) -> bool:
        """判断是否可能是人物名称
        
        Args:
            name: 待判断的词
            content: 文本内容
        
        Returns:
            是否可能是人名
        """
        # 检查是否出现在人物相关语境中
        character_contexts = [
            f'{name}说', f'{name}道', f'{name}问', f'{name}笑',
            f'{name}走', f'{name}看', f'{name}想', f'{name}觉得',
            f'对{name}', f'跟{name}', f'和{name}', f'向{name}',
            f'{name}的', f'{name}了', f'{name}在', f'{name}是'
        ]
        
        for context in character_contexts:
            if context in content:
                return True
        
        return False
    
    def _is_common_word(self, word: str) -> bool:
        """判断是否为常见非人名词汇"""
        common_words = {
            "一个", "这个", "那个", "什么", "怎么", "为什么", "如何",
            "现在", "时候", "地方", "事情", "问题", "情况", "样子",
            "知道", "觉得", "认为", "看到", "听到", "说道", "问道",
            "已经", "正在", "将要", "可以", "能够", "应该", "必须"
        }
        return word in common_words
    
    def _extract_character_descriptions(self, name: str, content: str) -> List[str]:
        """提取人物相关描述"""
        descriptions = []
        
        # 查找包含该人名的句子
        sentences = re.split(r'[。！？\n]', content)
        
        for sentence in sentences:
            if name in sentence and len(sentence.strip()) > 10:
                descriptions.append(sentence.strip())
        
        return descriptions
    
    def extract_events(self, content: str) -> List[Dict[str, Any]]:
        """提取事件信息
        
        Args:
            content: 文件内容
        
        Returns:
            事件列表
        """
        events = []
        
        # 按章节分割内容
        chapters = self._split_by_chapters(content)
        
        for i, chapter in enumerate(chapters):
            # 提取章节标题
            title_match = re.match(r'(第[^\n]+[章节回][^\n]*)', chapter)
            title = title_match.group(1) if title_match else f"第{i+1}章"
            
            # 提取关键事件（通过关键词识别）
            event_keywords = [
                "突然", "忽然", "意外", "发现", "得知", "决定", "开始",
                "结束", "完成", "失败", "成功", "突破", "觉醒", "获得"
            ]
            
            event_sentences = []
            sentences = re.split(r'[。！？]', chapter)
            
            for sentence in sentences:
                for keyword in event_keywords:
                    if keyword in sentence and len(sentence.strip()) > 10:
                        event_sentences.append(sentence.strip())
                        break
            
            if event_sentences:
                events.append({
                    "chapter": title,
                    "chapter_index": i + 1,
                    "key_events": event_sentences[:5]  # 最多5个关键事件
                })
        
        return events
    
    def _split_by_chapters(self, content: str) -> List[str]:
        """按章节分割内容"""
        # 匹配章节标题
        chapter_pattern = r'(第[一二三四五六七八九十百千\d]+[章节回][^\n]*)'
        
        parts = re.split(chapter_pattern, content)
        
        chapters = []
        current_chapter = ""
        
        for part in parts:
            if re.match(chapter_pattern, part):
                if current_chapter:
                    chapters.append(current_chapter)
                current_chapter = part
            else:
                current_chapter += part
        
        if current_chapter:
            chapters.append(current_chapter)
        
        return chapters if chapters else [content]
    
    def extract_foreshadows(self, content: str) -> List[Dict[str, Any]]:
        """提取伏笔信息
        
        Args:
            content: 文件内容
        
        Returns:
            伏笔列表
        """
        foreshadows = []
        
        # 伏笔关键词
        foreshadow_keywords = [
            "秘密", "隐藏", "未知", "将来", "以后", "总有一天",
            "注定", "命运", "预言", "传说", "谜团", "悬念"
        ]
        
        sentences = re.split(r'[。！？\n]', content)
        
        for sentence in sentences:
            for keyword in foreshadow_keywords:
                if keyword in sentence and len(sentence.strip()) > 10:
                    foreshadows.append({
                        "content": sentence.strip(),
                        "keyword": keyword,
                        "type": "foreshadow"
                    })
                    break
        
        return foreshadows
    
    def analyze_style_fingerprint(self, content: str) -> Dict[str, Any]:
        """分析文笔指纹
        
        Args:
            content: 文件内容
        
        Returns:
            文笔指纹字典
        """
        # 1. 句式长度分布
        sentence_lengths = self._analyze_sentence_lengths(content)
        
        # 2. 对话占比
        dialogue_ratio = self._analyze_dialogue_ratio(content)
        
        # 3. 心理描写占比
        psychology_ratio = self._analyze_psychology_ratio(content)
        
        # 4. 常用词汇
        common_words = self._extract_common_words(content)
        
        # 5. 叙事视角
        narrative_perspective = self._detect_narrative_perspective(content)
        
        # 6. 环境描写密度
        environment_ratio = self._analyze_environment_ratio(content)
        
        return {
            "sentence_lengths": sentence_lengths,
            "dialogue_ratio": dialogue_ratio,
            "psychology_ratio": psychology_ratio,
            "environment_ratio": environment_ratio,
            "common_words": common_words,
            "narrative_perspective": narrative_perspective
        }
    
    def _analyze_sentence_lengths(self, content: str) -> Dict[str, Any]:
        """分析句式长度分布"""
        sentences = re.split(r'[。！？]', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return {"avg": 0, "min": 0, "max": 0, "distribution": {}}
        
        lengths = [len(s) for s in sentences]
        
        # 分类统计
        distribution = {
            "short": 0,    # <10字
            "medium": 0,   # 10-30字
            "long": 0      # >30字
        }
        
        for length in lengths:
            if length < 10:
                distribution["short"] += 1
            elif length <= 30:
                distribution["medium"] += 1
            else:
                distribution["long"] += 1
        
        return {
            "avg": sum(lengths) / len(lengths),
            "min": min(lengths),
            "max": max(lengths),
            "distribution": distribution,
            "total_sentences": len(sentences)
        }
    
    def _analyze_dialogue_ratio(self, content: str) -> float:
        """分析对话占比"""
        # 匹配对话内容
        dialogue_pattern = r'["""\']([^"""\'\n]+)["""\']'
        dialogues = re.findall(dialogue_pattern, content)
        
        dialogue_length = sum(len(d) for d in dialogues)
        total_length = len(content)
        
        return dialogue_length / total_length if total_length > 0 else 0
    
    def _analyze_psychology_ratio(self, content: str) -> float:
        """分析心理描写占比"""
        # 心理描写关键词
        psychology_keywords = [
            "想", "觉得", "认为", "感到", "心里", "心中", "内心",
            "思考", "琢磨", "猜测", "怀疑", "担心", "害怕"
        ]
        
        sentences = re.split(r'[。！？\n]', content)
        psychology_sentences = [
            s for s in sentences 
            if any(kw in s for kw in psychology_keywords)
        ]
        
        psychology_length = sum(len(s) for s in psychology_sentences)
        total_length = len(content)
        
        return psychology_length / total_length if total_length > 0 else 0
    
    def _analyze_environment_ratio(self, content: str) -> float:
        """分析环境描写密度"""
        # 环境描写关键词
        environment_keywords = [
            "天空", "阳光", "月亮", "风", "雨", "雪", "云",
            "树", "花", "草", "山", "水", "河", "海",
            "房间", "客厅", "卧室", "办公室", "街道", "城市"
        ]
        
        sentences = re.split(r'[。！？\n]', content)
        environment_sentences = [
            s for s in sentences 
            if any(kw in s for kw in environment_keywords)
        ]
        
        environment_length = sum(len(s) for s in environment_sentences)
        total_length = len(content)
        
        return environment_length / total_length if total_length > 0 else 0
    
    def _extract_common_words(self, content: str, top_n: int = 50) -> List[Tuple[str, int]]:
        """提取常用词汇"""
        # 提取中文词组（2-4字）
        words = re.findall(r'[\u4e00-\u9fff]{2,4}', content)
        
        # 过滤停用词
        stop_words = {
            "一个", "这个", "那个", "什么", "怎么", "为什么", "如何",
            "现在", "时候", "地方", "事情", "问题", "情况", "样子",
            "知道", "觉得", "认为", "看到", "听到", "说道", "问道"
        }
        
        words = [w for w in words if w not in stop_words]
        
        # 统计频率
        word_counter = Counter(words)
        
        return word_counter.most_common(top_n)
    
    def _detect_narrative_perspective(self, content: str) -> str:
        """检测叙事视角"""
        # 第一人称标志
        first_person = len(re.findall(r'[我咱]', content))
        
        # 第三人称标志（常见人名）
        third_person_names = len(re.findall(r'[\u4e00-\u9fff]{2,4}(?:说|想|看|走)', content))
        
        if first_person > third_person_names * 2:
            return "first_person"  # 第一人称
        else:
            return "third_person"  # 第三人称
    
    def inject_to_truth_files(self, import_result: Dict[str, Any]) -> Dict[str, Any]:
        """将提取的信息注入真相文件体系
        
        Args:
            import_result: import_file的返回结果
        
        Returns:
            注入结果
        """
        from core.truth_files import TruthFiles
        
        truth_files = TruthFiles()
        truth_files.load_all()
        
        injection_result = {
            "characters_injected": 0,
            "events_injected": 0,
            "foreshadows_injected": 0,
            "style_guide_updated": False
        }
        
        # 注入人物到角色矩阵
        for char in import_result.get("characters", []):
            character_id = f"char_{char['name']}"
            truth_files.update_file("character_matrix", {
                character_id: {
                    "name": char["name"],
                    "description": char["descriptions"][0] if char["descriptions"] else "",
                    "mention_count": char["mention_count"],
                    "source": "imported"
                }
            })
            injection_result["characters_injected"] += 1
        
        # 注入事件到剧情进度
        for event_group in import_result.get("events", []):
            for event in event_group.get("key_events", []):
                event_id = f"event_{len(truth_files.files.get('plot_progress', {}).get('events', {})) + 1}"
                truth_files.update_file("plot_progress", {
                    "events": {
                        event_id: {
                            "description": event,
                            "chapter": event_group["chapter"],
                            "source": "imported"
                        }
                    }
                })
                injection_result["events_injected"] += 1
        
        # 注入伏笔到伏笔钩子
        for foreshadow in import_result.get("foreshadows", []):
            foreshadow_id = f"foreshadow_{len(truth_files.files.get('foreshadow_hooks', {}).get('hooks', {})) + 1}"
            truth_files.update_file("foreshadow_hooks", {
                "hooks": {
                    foreshadow_id: {
                        "content": foreshadow["content"],
                        "keyword": foreshadow["keyword"],
                        "status": "planted",
                        "source": "imported"
                    }
                }
            })
            injection_result["foreshadows_injected"] += 1
        
        # 更新风格指南
        style_fingerprint = import_result.get("style_fingerprint", {})
        if style_fingerprint:
            truth_files.update_file("style_guide", {
                "fingerprint": style_fingerprint,
                "source": "imported"
            })
            injection_result["style_guide_updated"] = True
        
        # 保存所有文件
        truth_files.save_all()
        
        return injection_result


if __name__ == "__main__":
    # 测试代码
    importer = FileImporter()
    
    # 创建测试文件
    test_content = """
第一章 开始

李明走在街道上，心中想着今天的会议。突然，他看到了一个熟悉的身影。

"你怎么在这里？"李明问道。

王华转过身来，笑着说："我来找你啊。"

李明觉得有些意外，但还是很高兴见到老朋友。

第二章 意外

他们走进咖啡厅，开始交谈。王华告诉李明一个重要消息。

"我发现了那个秘密，"王华低声说，"关于那个传说中的宝藏。"

李明心中一震，这个秘密可能会改变他们的命运。
"""
    
    test_file = "test_novel.txt"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    # 测试导入
    result = importer.import_file(test_file)
    
    print(f"元信息: {result['metadata']}")
    print(f"\n人物: {result['characters']}")
    print(f"\n事件: {result['events']}")
    print(f"\n伏笔: {result['foreshadows']}")
    print(f"\n文笔指纹: {result['style_fingerprint']}")
    
    # 清理测试文件
    os.remove(test_file)
