"""
小说数据库模块(NovelDatabase)

核心职责:
- 存储爬取的小说数据
- 支持数据查询和检索
- 与知识库系统整合
- 支持数据更新和去重

工作流程:
爬取数据 → 数据清洗 → 入库存储 → 索引构建 → 查询检索

设计思路:
- 使用SQLite作为数据库（轻量级，无需额外安装）
- 支持小说基本信息、章节信息、标签信息
- 提供全文检索功能
- 支持数据版本管理

关键算法:
- 数据去重：基于标题+作者的唯一性检查
- 增量更新：只更新变化的数据
- 索引优化：加速查询

数据库结构:
- novels: 小说基本信息
- chapters: 章节信息
- tags: 标签信息
- novel_tags: 小说-标签关联
- crawl_logs: 爬取日志
"""

import sqlite3
import json
import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class NovelDatabase:
    """
    小说数据库
    
    核心功能:
    1. 数据存储：小说、章节、标签
    2. 数据查询：按条件检索
    3. 数据更新：增量更新
    4. 数据去重：避免重复存储
    
    使用场景:
    - 存储爬取的小说数据
    - 为Scout Agent提供数据支持
    - 为知识库提供素材
    
    使用流程:
    1. 创建NovelDatabase实例
    2. 调用save_novel()存储小说
    3. 调用query_novels()查询数据
    """
    
    def __init__(self, db_path: str = None):
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径，默认使用config配置
        """
        if db_path is None:
            db_path = os.path.join(config.DATA_DIR, "novels.db")
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建小说表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS novels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                platform TEXT,
                genre TEXT,
                heat TEXT,
                brief TEXT,
                url TEXT,
                cover_url TEXT,
                word_count INTEGER,
                status TEXT,
                last_updated TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(title, author, platform)
            )
        """)
        
        # 创建章节表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id INTEGER,
                chapter_num INTEGER,
                title TEXT,
                content TEXT,
                word_count INTEGER,
                url TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (novel_id) REFERENCES novels(id)
            )
        """)
        
        # 创建标签表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)
        
        # 创建小说-标签关联表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS novel_tags (
                novel_id INTEGER,
                tag_id INTEGER,
                PRIMARY KEY (novel_id, tag_id),
                FOREIGN KEY (novel_id) REFERENCES novels(id),
                FOREIGN KEY (tag_id) REFERENCES tags(id)
            )
        """)
        
        # 创建爬取日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crawl_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                genre TEXT,
                url TEXT,
                status TEXT,
                message TEXT,
                novel_count INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_novels_genre ON novels(genre)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_novels_platform ON novels(platform)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_novels_heat ON novels(heat)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chapters_novel_id ON chapters(novel_id)")
        
        conn.commit()
        conn.close()
    
    def save_novel(self, novel_data: Dict[str, Any]) -> int:
        """
        保存小说数据
        
        Args:
            novel_data: 小说数据字典
        
        Returns:
            小说ID（如果已存在则返回现有ID）
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查是否已存在
            cursor.execute("""
                SELECT id FROM novels 
                WHERE title = ? AND author = ? AND platform = ?
            """, (novel_data.get("title"), novel_data.get("author"), novel_data.get("platform")))
            
            result = cursor.fetchone()
            
            if result:
                # 更新现有记录
                novel_id = result[0]
                cursor.execute("""
                    UPDATE novels SET
                        heat = ?,
                        brief = ?,
                        url = ?,
                        cover_url = ?,
                        word_count = ?,
                        status = ?,
                        last_updated = ?
                    WHERE id = ?
                """, (
                    novel_data.get("heat"),
                    novel_data.get("brief"),
                    novel_data.get("url"),
                    novel_data.get("cover_url"),
                    novel_data.get("word_count"),
                    novel_data.get("status"),
                    datetime.now().isoformat(),
                    novel_id
                ))
            else:
                # 插入新记录
                cursor.execute("""
                    INSERT INTO novels (title, author, platform, genre, heat, brief, url, cover_url, word_count, status, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    novel_data.get("title"),
                    novel_data.get("author"),
                    novel_data.get("platform"),
                    novel_data.get("genre"),
                    novel_data.get("heat"),
                    novel_data.get("brief"),
                    novel_data.get("url"),
                    novel_data.get("cover_url"),
                    novel_data.get("word_count"),
                    novel_data.get("status"),
                    datetime.now().isoformat()
                ))
                novel_id = cursor.lastrowid
            
            # 保存标签
            if "tags" in novel_data and novel_data["tags"]:
                self._save_tags(cursor, novel_id, novel_data["tags"])
            
            conn.commit()
            return novel_id
        
        except Exception as e:
            print(f"保存小说失败: {e}")
            conn.rollback()
            return -1
        finally:
            conn.close()
    
    def _save_tags(self, cursor, novel_id: int, tags: List[str]):
        """保存标签"""
        # 删除旧标签关联
        cursor.execute("DELETE FROM novel_tags WHERE novel_id = ?", (novel_id,))
        
        # 添加新标签
        for tag_name in tags:
            # 检查标签是否存在
            cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
            result = cursor.fetchone()
            
            if result:
                tag_id = result[0]
            else:
                # 创建新标签
                cursor.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))
                tag_id = cursor.lastrowid
            
            # 关联小说和标签
            cursor.execute("INSERT INTO novel_tags (novel_id, tag_id) VALUES (?, ?)", (novel_id, tag_id))
    
    def save_chapter(self, novel_id: int, chapter_data: Dict[str, Any]) -> int:
        """
        保存章节数据
        
        Args:
            novel_id: 小说ID
            chapter_data: 章节数据字典
        
        Returns:
            章节ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查是否已存在
            cursor.execute("""
                SELECT id FROM chapters 
                WHERE novel_id = ? AND chapter_num = ?
            """, (novel_id, chapter_data.get("chapter_num")))
            
            result = cursor.fetchone()
            
            if result:
                # 更新现有记录
                chapter_id = result[0]
                cursor.execute("""
                    UPDATE chapters SET
                        title = ?,
                        content = ?,
                        word_count = ?,
                        url = ?
                    WHERE id = ?
                """, (
                    chapter_data.get("title"),
                    chapter_data.get("content"),
                    chapter_data.get("word_count"),
                    chapter_data.get("url"),
                    chapter_id
                ))
            else:
                # 插入新记录
                cursor.execute("""
                    INSERT INTO chapters (novel_id, chapter_num, title, content, word_count, url)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    novel_id,
                    chapter_data.get("chapter_num"),
                    chapter_data.get("title"),
                    chapter_data.get("content"),
                    chapter_data.get("word_count"),
                    chapter_data.get("url")
                ))
                chapter_id = cursor.lastrowid
            
            conn.commit()
            return chapter_id
        
        except Exception as e:
            print(f"保存章节失败: {e}")
            conn.rollback()
            return -1
        finally:
            conn.close()
    
    def query_novels(self, genre: str = None, platform: str = None, 
                    limit: int = 10, order_by: str = "heat") -> List[Dict[str, Any]]:
        """
        查询小说数据
        
        Args:
            genre: 题材筛选
            platform: 平台筛选
            limit: 返回数量限制
            order_by: 排序字段（heat/word_count/last_updated）
        
        Returns:
            小说列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 构建查询
            query = "SELECT * FROM novels WHERE 1=1"
            params = []
            
            if genre:
                query += " AND genre = ?"
                params.append(genre)
            
            if platform:
                query += " AND platform = ?"
                params.append(platform)
            
            # 排序
            if order_by in ["heat", "word_count", "last_updated"]:
                query += f" ORDER BY {order_by} DESC"
            else:
                query += " ORDER BY last_updated DESC"
            
            # 限制数量
            query += " LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                novel = dict(zip(columns, row))
                # 获取标签
                novel["tags"] = self._get_novel_tags(cursor, novel["id"])
                results.append(novel)
            
            return results
        
        except Exception as e:
            print(f"查询小说失败: {e}")
            return []
        finally:
            conn.close()
    
    def _get_novel_tags(self, cursor, novel_id: int) -> List[str]:
        """获取小说标签"""
        cursor.execute("""
            SELECT t.name FROM tags t
            JOIN novel_tags nt ON t.id = nt.tag_id
            WHERE nt.novel_id = ?
        """, (novel_id,))
        
        return [row[0] for row in cursor.fetchall()]
    
    def log_crawl(self, platform: str, genre: str, url: str, 
                 status: str, message: str, novel_count: int):
        """
        记录爬取日志
        
        Args:
            platform: 平台名称
            genre: 题材
            url: 爬取URL
            status: 状态（success/failed）
            message: 消息
            novel_count: 爬取小说数量
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO crawl_logs (platform, genre, url, status, message, novel_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (platform, genre, url, status, message, novel_count))
            
            conn.commit()
        
        except Exception as e:
            print(f"记录爬取日志失败: {e}")
        finally:
            conn.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取数据库统计信息
        
        Returns:
            统计信息字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # 小说总数
            cursor.execute("SELECT COUNT(*) FROM novels")
            stats["total_novels"] = cursor.fetchone()[0]
            
            # 按平台统计
            cursor.execute("""
                SELECT platform, COUNT(*) as count 
                FROM novels 
                GROUP BY platform
            """)
            stats["by_platform"] = dict(cursor.fetchall())
            
            # 按题材统计
            cursor.execute("""
                SELECT genre, COUNT(*) as count 
                FROM novels 
                WHERE genre IS NOT NULL
                GROUP BY genre
            """)
            stats["by_genre"] = dict(cursor.fetchall())
            
            # 章节总数
            cursor.execute("SELECT COUNT(*) FROM chapters")
            stats["total_chapters"] = cursor.fetchone()[0]
            
            # 标签总数
            cursor.execute("SELECT COUNT(*) FROM tags")
            stats["total_tags"] = cursor.fetchone()[0]
            
            # 最近爬取
            cursor.execute("""
                SELECT * FROM crawl_logs 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            columns = [desc[0] for desc in cursor.description]
            stats["recent_crawls"] = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            return stats
        
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            return {}
        finally:
            conn.close()
    
    def export_to_json(self, output_path: str = None) -> str:
        """
        导出数据为JSON文件
        
        Args:
            output_path: 输出文件路径
        
        Returns:
            输出文件路径
        """
        if output_path is None:
            output_path = os.path.join(config.DATA_DIR, "novels_export.json")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 导出所有小说
            cursor.execute("SELECT * FROM novels")
            columns = [desc[0] for desc in cursor.description]
            novels = []
            
            for row in cursor.fetchall():
                novel = dict(zip(columns, row))
                novel["tags"] = self._get_novel_tags(cursor, novel["id"])
                novels.append(novel)
            
            # 写入JSON文件
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump({
                    "exported_at": datetime.now().isoformat(),
                    "total_count": len(novels),
                    "novels": novels
                }, f, ensure_ascii=False, indent=2)
            
            return output_path
        
        except Exception as e:
            print(f"导出失败: {e}")
            return ""
        finally:
            conn.close()


# 全局单例
_novel_database: Optional[NovelDatabase] = None


def get_novel_database() -> NovelDatabase:
    """获取全局NovelDatabase单例"""
    global _novel_database
    if _novel_database is None:
        _novel_database = NovelDatabase()
    return _novel_database


if __name__ == "__main__":
    # 测试数据库
    db = get_novel_database()
    
    # 保存测试数据
    test_novel = {
        "title": "测试小说",
        "author": "测试作者",
        "platform": "番茄小说",
        "genre": "都市",
        "heat": "10000",
        "brief": "这是一个测试小说",
        "url": "https://example.com",
        "tags": ["测试", "都市"]
    }
    
    novel_id = db.save_novel(test_novel)
    print(f"保存小说ID: {novel_id}")
    
    # 查询数据
    novels = db.query_novels(genre="都市", limit=5)
    print(f"查询结果: {len(novels)} 条")
    
    # 获取统计
    stats = db.get_statistics()
    print(f"统计信息: {json.dumps(stats, ensure_ascii=False, indent=2)}")
