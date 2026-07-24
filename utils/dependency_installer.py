#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖自动安装模块

核心职责：
- 检测缺失的Python依赖包
- 自动调用pip安装缺失的依赖
- 支持联网安装和离线模式切换

设计思路：
- 启动时自动检测，无需用户手动检查
- 只安装缺失的包，避免重复安装
- 提供友好的安装进度提示
"""

import subprocess
import sys
import importlib.util
from typing import List, Dict, Tuple


class DependencyInstaller:
    """
    依赖安装器
    
    功能：
    1. 检测缺失依赖
    2. 自动安装缺失包
    3. 验证安装结果
    """
    
    def __init__(self):
        """初始化依赖安装器"""
        self.missing_deps = []
        self.installed_deps = []
        self.failed_deps = []
    
    def check_dependency(self, package_name: str, import_name: str = None) -> bool:
        """
        检测单个依赖是否已安装
        
        Args:
            package_name: pip包名（如 beautifulsoup4）
            import_name: 导入名（如 bs4），默认与package_name相同
        
        Returns:
            bool: True=已安装, False=未安装
        """
        if import_name is None:
            import_name = package_name
        
        try:
            # 使用真正的 import 来检测，确保模块可以正常导入
            __import__(import_name)
            return True
        except (ImportError, ModuleNotFoundError):
            return False
    
    def check_all_dependencies(self) -> List[Tuple[str, str]]:
        """
        检测所有必需依赖
        
        Returns:
            List[Tuple[str, str]]: 缺失的依赖列表 [(package_name, import_name), ...]
        """
        # 依赖映射：pip包名 -> 导入名
        dependencies = {
            'requests': 'requests',
            'beautifulsoup4': 'bs4',
            'openai': 'openai',
            'anthropic': 'anthropic',
            'python-docx': 'docx',
            'ebooklib': 'ebooklib',
            'pdfplumber': 'pdfplumber',
            'jieba': 'jieba',
            'playwright': 'playwright',
        }
        
        missing = []
        for package_name, import_name in dependencies.items():
            if not self.check_dependency(package_name, import_name):
                missing.append((package_name, import_name))
        
        self.missing_deps = missing
        return missing
    
    def install_playwright_browsers(self) -> bool:
        """
        安装Playwright浏览器（Chromium）
        
        Returns:
            bool: 安装成功返回True
        """
        if not self.check_dependency('playwright', 'playwright'):
            print("  Playwright未安装，跳过浏览器安装")
            return False
        
        try:
            print("  正在安装Playwright浏览器...", end=' ', flush=True)
            
            # 使用python -m playwright install chromium
            result = subprocess.run(
                [sys.executable, '-m', 'playwright', 'install', 'chromium'],
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时（浏览器较大）
            )
            
            if result.returncode == 0:
                print("✓")
                return True
            else:
                print("✗")
                print(f"    错误: {result.stderr[:100]}")
                return False
        
        except subprocess.TimeoutExpired:
            print("✗ (超时)")
            return False
        except Exception as e:
            print(f"✗ ({str(e)[:50]})")
            return False
    
    def install_package(self, package_name: str) -> bool:
        """
        安装单个依赖包
        
        Args:
            package_name: pip包名
        
        Returns:
            bool: True=安装成功, False=安装失败
        """
        try:
            print(f"  正在安装 {package_name}...", end=' ', flush=True)
            
            # 使用pip安装
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', package_name, '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple'],
                capture_output=True,
                text=True,
                timeout=120  # 2分钟超时
            )
            
            if result.returncode == 0:
                print("✓")
                self.installed_deps.append(package_name)
                return True
            else:
                print("✗")
                print(f"    错误: {result.stderr[:100]}")
                self.failed_deps.append(package_name)
                return False
        
        except subprocess.TimeoutExpired:
            print("✗ (超时)")
            self.failed_deps.append(package_name)
            return False
        except Exception as e:
            print(f"✗ ({str(e)[:50]})")
            self.failed_deps.append(package_name)
            return False
    
    def install_all_missing(self) -> Dict[str, List[str]]:
        """
        安装所有缺失的依赖
        
        Returns:
            Dict[str, List[str]]: 安装结果统计
        """
        if not self.missing_deps:
            self.check_all_dependencies()
        
        if not self.missing_deps:
            return {
                'installed': [],
                'failed': [],
                'skipped': []
            }
        
        print(f"\n检测到 {len(self.missing_deps)} 个缺失依赖，开始自动安装...")
        print("-" * 50)
        
        for package_name, import_name in self.missing_deps:
            self.install_package(package_name)
        
        # 如果 playwright 刚安装成功，自动安装浏览器
        if 'playwright' in self.installed_deps:
            print("\n安装Playwright浏览器（首次使用需要）...")
            self.install_playwright_browsers()
        
        print("-" * 50)
        print(f"安装完成: {len(self.installed_deps)} 成功, {len(self.failed_deps)} 失败")
        
        return {
            'installed': self.installed_deps,
            'failed': self.failed_deps,
            'skipped': []
        }
    
    def verify_installation(self) -> bool:
        """
        验证所有依赖是否已正确安装
        
        Returns:
            bool: True=全部安装成功, False=仍有缺失
        """
        remaining = self.check_all_dependencies()
        return len(remaining) == 0


def ensure_dependencies():
    """
    确保所有依赖已安装（供main.py调用）
    
    流程：
    1. 检测缺失依赖
    2. 自动安装
    3. 验证安装结果
    4. 如果仍有缺失，提示用户手动安装
    """
    installer = DependencyInstaller()
    
    # 检测缺失依赖
    missing = installer.check_all_dependencies()
    
    if not missing:
        # 所有依赖已安装，静默通过
        return True
    
    # 有缺失依赖，尝试自动安装
    result = installer.install_all_missing()
    
    # 验证安装结果
    if installer.verify_installation():
        print("\n✓ 所有依赖安装成功！\n")
        return True
    else:
        print("\n✗ 部分依赖安装失败，请手动安装：")
        for package_name, _ in installer.missing_deps:
            if package_name in result['failed']:
                print(f"  pip install {package_name}")
        print()
        return False


if __name__ == '__main__':
    # 测试模式
    print("依赖检测工具")
    print("=" * 50)
    ensure_dependencies()
