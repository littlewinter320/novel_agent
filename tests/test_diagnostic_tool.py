"""
DiagnosticTool 单元测试

测试诊断工具的核心功能:
- 生成系统诊断报告
- 执行健康检查
- 导出报告
"""
import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# 添加项目路径
test_dir = os.path.dirname(os.path.abspath(__file__))
novel_agent_dir = os.path.dirname(test_dir)
sys.path.insert(0, novel_agent_dir)

from tests.test_utils import MockLLMClient
from core.diagnostic_tool import DiagnosticTool, get_diagnostic_tool
import config


class TestDiagnosticTool(unittest.TestCase):
    """DiagnosticTool 测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.original_data_dir = config.DATA_DIR
        config.DATA_DIR = self.test_dir
        
    def tearDown(self):
        """测试后清理"""
        config.DATA_DIR = self.original_data_dir
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    @patch('core.diagnostic_tool.get_character_manager')
    @patch('core.diagnostic_tool.get_foreshadow_tracker')
    @patch('core.diagnostic_tool.get_genre_knowledge_base')
    @patch('core.diagnostic_tool.TruthFiles')
    def test_initialization(self, mock_truth_files, mock_genre, mock_foreshadow, mock_character):
        """测试初始化"""
        mock_tf_instance = MagicMock()
        mock_truth_files.return_value = mock_tf_instance
        mock_genre.return_value = MagicMock()
        mock_foreshadow.return_value = MagicMock()
        mock_character.return_value = MagicMock()
        
        dt = DiagnosticTool()
        self.assertIsNotNone(dt.truth_files)
        self.assertIsNotNone(dt.genre_knowledge_base)
        self.assertIsNotNone(dt.foreshadow_tracker)
        self.assertIsNotNone(dt.character_manager)
    
    @patch('core.diagnostic_tool.get_character_manager')
    @patch('core.diagnostic_tool.get_foreshadow_tracker')
    @patch('core.diagnostic_tool.get_genre_knowledge_base')
    @patch('core.diagnostic_tool.TruthFiles')
    def test_generate_report(self, mock_truth_files, mock_genre, mock_foreshadow, mock_character):
        """测试生成诊断报告"""
        mock_tf_instance = MagicMock()
        mock_tf_instance.get_file.return_value = {}
        mock_truth_files.return_value = mock_tf_instance
        
        mock_genre_instance = MagicMock()
        mock_genre_instance.list_genres.return_value = ["玄幻", "都市"]
        mock_genre.return_value = mock_genre_instance
        
        mock_foreshadow_instance = MagicMock()
        mock_foreshadow_instance.health_check.return_value = {"healthy": True, "active_count": 0}
        mock_foreshadow_instance.foreshadows = []
        mock_foreshadow.return_value = mock_foreshadow_instance
        
        mock_character_instance = MagicMock()
        mock_character_instance.characters = {}
        mock_character.return_value = mock_character_instance
        
        dt = DiagnosticTool()
        result = dt.generate_report()
        
        self.assertIsInstance(result, dict)
        self.assertIn("system_status", result)
        self.assertIn("health_check", result)
        self.assertIn("report", result)
        self.assertIn("generated_at", result)
    
    @patch('core.diagnostic_tool.get_character_manager')
    @patch('core.diagnostic_tool.get_foreshadow_tracker')
    @patch('core.diagnostic_tool.get_genre_knowledge_base')
    @patch('core.diagnostic_tool.TruthFiles')
    def test_health_check(self, mock_truth_files, mock_genre, mock_foreshadow, mock_character):
        """测试健康检查"""
        mock_tf_instance = MagicMock()
        mock_tf_instance.get_file.return_value = {}
        mock_truth_files.return_value = mock_tf_instance
        
        mock_genre_instance = MagicMock()
        mock_genre_instance.list_genres.return_value = ["玄幻", "都市"]
        mock_genre.return_value = mock_genre_instance
        
        mock_foreshadow_instance = MagicMock()
        mock_foreshadow_instance.health_check.return_value = {"healthy": True}
        mock_foreshadow.return_value = mock_foreshadow_instance
        
        mock_character_instance = MagicMock()
        mock_character_instance.characters = {}
        mock_character.return_value = mock_character_instance
        
        dt = DiagnosticTool()
        result = dt.health_check()
        
        self.assertIsInstance(result, dict)
        self.assertIn("healthy", result)
        self.assertIn("issues", result)
        self.assertIn("warnings", result)
    
    @patch('core.diagnostic_tool.get_character_manager')
    @patch('core.diagnostic_tool.get_foreshadow_tracker')
    @patch('core.diagnostic_tool.get_genre_knowledge_base')
    @patch('core.diagnostic_tool.TruthFiles')
    def test_export_report(self, mock_truth_files, mock_genre, mock_foreshadow, mock_character):
        """测试导出报告"""
        mock_tf_instance = MagicMock()
        mock_tf_instance.get_file.return_value = {}
        mock_truth_files.return_value = mock_tf_instance
        
        mock_genre_instance = MagicMock()
        mock_genre_instance.list_genres.return_value = ["玄幻"]
        mock_genre.return_value = mock_genre_instance
        
        mock_foreshadow_instance = MagicMock()
        mock_foreshadow_instance.health_check.return_value = {"healthy": True}
        mock_foreshadow_instance.foreshadows = []
        mock_foreshadow.return_value = mock_foreshadow_instance
        
        mock_character_instance = MagicMock()
        mock_character_instance.characters = {}
        mock_character.return_value = mock_character_instance
        
        dt = DiagnosticTool()
        
        output_file = os.path.join(self.test_dir, "diagnostic_report.md")
        result = dt.export_report(output_file)
        
        self.assertIsInstance(result, dict)
        self.assertIn("exported", result)
        
        # 验证文件是否创建
        self.assertTrue(os.path.exists(output_file))


if __name__ == '__main__':
    unittest.main()
