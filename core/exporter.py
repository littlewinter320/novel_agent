"""
导出器(Exporter)

核心职责:
- 导出为TXT（每章一个文件）
- 导出为Markdown
- 导出为EPUB
- 自动过滤内部工件

工作流程:
加载章节数据 → 过滤内部工件 → 导出为指定格式

设计思路:
- 支持多种导出格式
- 自动过滤内部工件（自检表、结算表、审计报告等）
- 使用标准库和第三方库实现

输出格式:
- TXT: 每章一个文本文件
- Markdown: 带格式的Markdown文件
- EPUB: 电子书格式
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class Exporter:
    """
    导出器类
    
    核心功能:
    1. TXT导出：每章一个文本文件
    2. Markdown导出：带格式的Markdown文件
    3. EPUB导出：电子书格式
    
    使用场景:
    - 生成完成后导出为可读格式
    - 分享给读者
    - 存档
    
    使用流程:
    1. 调用export_txt(output_dir)导出TXT
    2. 调用export_markdown(output_file)导出Markdown
    3. 调用export_epub(output_file)导出EPUB
    """
    
    def __init__(self):
        """
        初始化导出器
        
        初始化流程:
        1. 初始化章节数据存储
        """
        self.chapters = []
    
    def _filter_internal_artifacts(self, chapter: Dict[str, Any]) -> Dict[str, Any]:
        """
        过滤内部工件
        
        实现逻辑:
        1. 移除自检表、结算表、审计报告等内部数据
        2. 只保留章节正文和基本信息
        
        Args:
            chapter: 章节数据字典
        
        Returns:
            过滤后的章节数据
        """
        filtered = {
            "chapter_num": chapter.get("chapter_num"),
            "chapter_title": chapter.get("chapter_title"),
            "chapter_content": chapter.get("chapter_content", "")
        }
        
        return filtered
    
    def export_txt(self, chapters: List[Dict[str, Any]],
                  output_dir: str) -> Dict[str, Any]:
        """
        导出为TXT格式（每章一个文件）
        
        实现逻辑:
        1. 创建输出目录
        2. 过滤内部工件
        3. 每章写入一个文本文件
        
        Args:
            chapters: 章节数据列表
            output_dir: 输出目录
        
        Returns:
            导出结果字典
        """
        os.makedirs(output_dir, exist_ok=True)
        
        exported_files = []
        
        for chapter in chapters:
            filtered = self._filter_internal_artifacts(chapter)
            chapter_num = filtered.get("chapter_num", 0)
            chapter_title = filtered.get("chapter_title", f"第{chapter_num}章")
            content = filtered.get("chapter_content", "")
            
            # 生成文件名
            filename = f"第{chapter_num:03d}章_{chapter_title}.txt"
            filepath = os.path.join(output_dir, filename)
            
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"{chapter_title}\n\n")
                    f.write(content)
                
                exported_files.append(filepath)
            except Exception as e:
                print(f"导出章节{chapter_num}失败: {e}")
        
        return {
            "exported": True,
            "format": "txt",
            "output_dir": output_dir,
            "file_count": len(exported_files),
            "files": exported_files
        }
    
    def export_markdown(self, chapters: List[Dict[str, Any]],
                       output_file: str) -> Dict[str, Any]:
        """
        导出为Markdown格式
        
        实现逻辑:
        1. 过滤内部工件
        2. 构建Markdown内容
        3. 写入文件
        
        Args:
            chapters: 章节数据列表
            output_file: 输出文件路径
        
        Returns:
            导出结果字典
        """
        # 构建Markdown内容
        md_content = "# 小说作品\n\n"
        md_content += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        md_content += "---\n\n"
        
        for chapter in chapters:
            filtered = self._filter_internal_artifacts(chapter)
            chapter_num = filtered.get("chapter_num", 0)
            chapter_title = filtered.get("chapter_title", f"第{chapter_num}章")
            content = filtered.get("chapter_content", "")
            
            md_content += f"## {chapter_title}\n\n"
            md_content += content
            md_content += "\n\n---\n\n"
        
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            return {
                "exported": True,
                "format": "markdown",
                "output_file": output_file,
                "chapter_count": len(chapters)
            }
        except Exception as e:
            return {
                "exported": False,
                "error": str(e)
            }
    
    def export_epub(self, chapters: List[Dict[str, Any]],
                   output_file: str,
                   book_title: str = "小说作品",
                   author: str = "AI创作") -> Dict[str, Any]:
        """
        导出为EPUB格式
        
        实现逻辑:
        1. 使用ebooklib库创建EPUB
        2. 过滤内部工件
        3. 添加章节
        4. 保存文件
        
        Args:
            chapters: 章节数据列表
            output_file: 输出文件路径
            book_title: 书名
            author: 作者
        
        Returns:
            导出结果字典
        """
        try:
            from ebooklib import epub
            
            # 创建书籍
            book = epub.EpubBook()
            
            # 设置元数据
            book.set_identifier('novel-agent-export')
            book.set_title(book_title)
            book.set_language('zh')
            book.add_author(author)
            
            # 创建章节
            epub_chapters = []
            for chapter in chapters:
                filtered = self._filter_internal_artifacts(chapter)
                chapter_num = filtered.get("chapter_num", 0)
                chapter_title = filtered.get("chapter_title", f"第{chapter_num}章")
                content = filtered.get("chapter_content", "")
                
                # 创建EPUB章节
                epub_chapter = epub.EpubHtml(
                    title=chapter_title,
                    file_name=f'chapter_{chapter_num:03d}.xhtml',
                    lang='zh'
                )
                epub_chapter.content = f'<h1>{chapter_title}</h1><p>{content}</p>'
                
                book.add_item(epub_chapter)
                epub_chapters.append(epub_chapter)
            
            # 设置目录
            book.toc = epub_chapters
            
            # 添加导航文件
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            
            # 保存
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            epub.write_epub(output_file, book)
            
            return {
                "exported": True,
                "format": "epub",
                "output_file": output_file,
                "chapter_count": len(chapters)
            }
        except ImportError:
            return {
                "exported": False,
                "error": "缺少ebooklib库，请安装: pip install ebooklib"
            }
        except Exception as e:
            return {
                "exported": False,
                "error": str(e)
            }


# 全局实例
_exporter = None


def get_exporter() -> Exporter:
    """获取全局导出器实例（单例模式）"""
    global _exporter
    if _exporter is None:
        _exporter = Exporter()
    return _exporter
