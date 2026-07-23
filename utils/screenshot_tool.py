"""
截图工具模块(ScreenshotTool)

核心职责:
- 对网页进行截图
- 支持全页面截图和元素截图
- 将截图保存为图片文件
- 提供截图分析接口（结合多模态LLM）

工作流程:
指定URL → 打开页面 → 截图 → 保存图片 → 可选：LLM分析

设计思路:
- 使用Playwright进行截图（支持动态渲染）
- 支持自定义截图区域（全页面/可视区域/指定元素）
- 图片保存到 data/screenshots/ 目录
- 提供截图元数据（URL、时间、尺寸等）

关键算法:
- 自动滚动加载全页面内容
- 智能裁剪：去除空白区域
- 图片压缩：控制文件大小

输出格式:
{
    "url": "截图URL",
    "screenshot_path": "截图保存路径",
    "timestamp": "截图时间",
    "width": 宽度,
    "height": 高度,
    "file_size": 文件大小
}
"""

import json
import os
import sys
import time
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# 尝试导入Playwright
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None


class ScreenshotTool:
    """
    截图工具
    
    核心功能:
    1. 网页截图：支持全页面和可视区域
    2. 元素截图：截取指定DOM元素
    3. 图片保存：PNG/JPEG格式
    4. 元数据记录：URL、时间、尺寸等
    
    使用场景:
    - Scout Agent需要截图保存热门小说页面
    - 用户需要可视化查看爬取的数据
    - 调试时查看页面实际内容
    
    使用流程:
    1. 创建ScreenshotTool实例
    2. 调用take_screenshot(url)截图
    3. 返回截图信息（路径、尺寸等）
    """
    
    def __init__(self):
        """
        初始化截图工具
        
        初始化流程:
        1. 检查Playwright是否可用（可选，不可用时优雅降级）
        2. 创建截图保存目录
        3. 初始化浏览器（延迟初始化）
        """
        # 创建截图目录
        self.screenshot_dir = os.path.join(config.DATA_DIR, "screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        # 延迟初始化浏览器
        self.playwright = None
        self.browser = None
        self.page = None
        
        # 记录playwright可用性
        self.available = PLAYWRIGHT_AVAILABLE
        if not self.available:
            print("提示: playwright未安装，截图功能不可用（非关键功能）")
    
    def _init_browser(self):
        """初始化浏览器"""
        if not self.available:
            return False
        
        if self.browser is None:
            try:
                self.playwright = sync_playwright().start()
                self.browser = self.playwright.chromium.launch(headless=True)
                self.page = self.browser.new_page(viewport={"width": 1920, "height": 1080})
            except Exception as e:
                print(f"浏览器初始化失败: {e}")
                return False
        
        return True
    
    def take_screenshot(self, url: str, filename: str = None, 
                       full_page: bool = True, wait_seconds: int = 2) -> Dict[str, Any]:
        """
        对网页进行截图
        
        Args:
            url: 网页URL
            filename: 保存文件名（不含扩展名），默认自动生成
            full_page: 是否全页面截图（False则只截可视区域）
            wait_seconds: 等待页面加载时间（秒）
        
        Returns:
            截图信息字典
        """
        if not self._init_browser():
            return {"error": "截图功能不可用（playwright未安装或初始化失败）"}
        
        # 生成文件名
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}"
        
        screenshot_path = os.path.join(self.screenshot_dir, f"{filename}.png")
        
        try:
            # 打开页面
            self.page.goto(url, wait_until="networkidle")
            time.sleep(wait_seconds)  # 等待动态内容加载
            
            # 截图
            if full_page:
                self.page.screenshot(path=screenshot_path, full_page=True)
            else:
                self.page.screenshot(path=screenshot_path, full_page=False)
            
            # 获取文件信息
            file_size = os.path.getsize(screenshot_path)
            
            # 获取页面尺寸
            dimensions = self.page.evaluate("""() => {
                return {
                    width: Math.max(document.body.scrollWidth, document.documentElement.scrollWidth),
                    height: Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)
                }
            }""")
            
            return {
                "url": url,
                "screenshot_path": screenshot_path,
                "timestamp": datetime.now().isoformat(),
                "width": dimensions["width"],
                "height": dimensions["height"],
                "file_size": file_size,
                "full_page": full_page
            }
        
        except Exception as e:
            print(f"截图失败: {e}")
            return {"error": str(e)}
    
    def take_element_screenshot(self, url: str, selector: str, 
                               filename: str = None) -> Dict[str, Any]:
        """
        对指定元素进行截图
        
        Args:
            url: 网页URL
            selector: CSS选择器
            filename: 保存文件名
        
        Returns:
            截图信息字典
        """
        if not self._init_browser():
            return {"error": "截图功能不可用（playwright未安装或初始化失败）"}
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"element_{timestamp}"
        
        screenshot_path = os.path.join(self.screenshot_dir, f"{filename}.png")
        
        try:
            # 打开页面
            self.page.goto(url, wait_until="networkidle")
            time.sleep(2)
            
            # 查找元素
            element = self.page.query_selector(selector)
            if not element:
                return {"error": f"未找到元素: {selector}"}
            
            # 截图元素
            element.screenshot(path=screenshot_path)
            
            # 获取文件信息
            file_size = os.path.getsize(screenshot_path)
            box = element.bounding_box()
            
            return {
                "url": url,
                "selector": selector,
                "screenshot_path": screenshot_path,
                "timestamp": datetime.now().isoformat(),
                "width": box["width"] if box else 0,
                "height": box["height"] if box else 0,
                "file_size": file_size
            }
        
        except Exception as e:
            print(f"元素截图失败: {e}")
            return {"error": str(e)}
    
    def list_screenshots(self) -> list:
        """
        列出所有截图
        
        Returns:
            截图文件列表
        """
        if not os.path.exists(self.screenshot_dir):
            return []
        
        screenshots = []
        for filename in os.listdir(self.screenshot_dir):
            if filename.endswith(".png") or filename.endswith(".jpg"):
                filepath = os.path.join(self.screenshot_dir, filename)
                stat = os.stat(filepath)
                screenshots.append({
                    "filename": filename,
                    "path": filepath,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
                })
        
        return sorted(screenshots, key=lambda x: x["created_at"], reverse=True)
    
    def delete_screenshot(self, filename: str) -> bool:
        """
        删除截图
        
        Args:
            filename: 文件名
        
        Returns:
            是否删除成功
        """
        filepath = os.path.join(self.screenshot_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
    
    def close(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()


# 全局单例
_screenshot_tool: Optional[ScreenshotTool] = None


def get_screenshot_tool() -> ScreenshotTool:
    """获取全局ScreenshotTool单例"""
    global _screenshot_tool
    if _screenshot_tool is None:
        _screenshot_tool = ScreenshotTool()
    return _screenshot_tool


if __name__ == "__main__":
    # 测试截图工具
    tool = get_screenshot_tool()
    result = tool.take_screenshot("https://fanqienovel.com", full_page=False)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    tool.close()
