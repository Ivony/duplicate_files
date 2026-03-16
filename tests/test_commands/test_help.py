"""测试help命令功能"""

import pytest
import sys
from main import app


class TestHelpCommand:
    """测试help命令"""
    
    def test_clean_help(self, capsys):
        """测试clean --help命令"""
        sys.argv = ['duplicate', 'clean', '--help']
        with pytest.raises(SystemExit) as exc_info:
            app()
        
        captured = capsys.readouterr()
        assert '清理重复文件' in captured.out
        assert 'delete' in captured.out
        assert 'link' in captured.out
    
    def test_show_help(self, capsys):
        """测试show --help命令"""
        sys.argv = ['duplicate', 'show', '--help']
        with pytest.raises(SystemExit) as exc_info:
            app()
        
        captured = capsys.readouterr()
        assert '显示信息' in captured.out
        assert 'groups' in captured.out
    
    def test_hash_help(self, capsys):
        """测试hash --help命令"""
        sys.argv = ['duplicate', 'hash', '--help']
        with pytest.raises(SystemExit) as exc_info:
            app()
        
        captured = capsys.readouterr()
        assert '哈希计算' in captured.out or 'hash' in captured.out.lower()
    
    def test_index_help(self, capsys):
        """测试index --help命令"""
        sys.argv = ['duplicate', 'index', '--help']
        with pytest.raises(SystemExit) as exc_info:
            app()
        
        captured = capsys.readouterr()
        assert '索引管理' in captured.out or 'index' in captured.out.lower()
    
    def test_main_help(self, capsys):
        """测试主命令--help"""
        sys.argv = ['duplicate', '--help']
        with pytest.raises(SystemExit) as exc_info:
            app()
        
        captured = capsys.readouterr()
        assert '重复文件查找工具' in captured.out
        assert 'clean' in captured.out
        assert 'show' in captured.out
        assert 'hash' in captured.out
        assert 'index' in captured.out


class TestProgName:
    """测试程序名显示"""
    
    def test_interactive_mode_prog_name(self, capsys):
        """测试交互式模式下显示duplicate>"""
        with pytest.raises(SystemExit):
            app(['clean', '--help'], prog_name='duplicate>')
        
        captured = capsys.readouterr()
        assert 'duplicate>' in captured.out
        assert 'clean' in captured.out
    
    def test_command_line_mode_prog_name(self, capsys):
        """测试命令行模式下显示脚本名"""
        sys.argv = ['main.py', 'clean', '--help']
        with pytest.raises(SystemExit):
            app()
        
        captured = capsys.readouterr()
        assert 'Usage:' in captured.out
        assert 'clean' in captured.out
    
    def test_interactive_help_command(self, capsys):
        """测试交互式模式下help <command>格式"""
        with pytest.raises(SystemExit):
            app(['show', '--help'], prog_name='duplicate>')
        
        captured = capsys.readouterr()
        assert 'duplicate>' in captured.out
        assert 'show' in captured.out
        assert 'groups' in captured.out
