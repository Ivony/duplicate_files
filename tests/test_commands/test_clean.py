import pytest
import os
import tempfile
import sys
from commands.clean import app

class TestCleanCommand:
    def test_delete_command_no_groups(self, capsys):
        """测试clean delete命令（无重复文件组）"""
        sys.argv = ['', 'delete', '--yes']
        with pytest.raises(SystemExit):
            app()
        
        captured = capsys.readouterr()
        assert '没有找到' in captured.out or '清理' in captured.out
    
    def test_link_command_no_groups(self, capsys):
        """测试clean link命令（无重复文件组）"""
        sys.argv = ['', 'link', '--yes']
        with pytest.raises(SystemExit):
            app()
        
        captured = capsys.readouterr()
        assert '没有找到' in captured.out or '清理' in captured.out
    
    def test_delete_script_mode_no_groups(self, temp_dir, capsys):
        """测试clean delete --mode script命令（无重复文件组）"""
        script_path = os.path.join(temp_dir, 'cleanup.bat')
        sys.argv = ['', 'delete', '--yes', '--mode', 'script', '--script', script_path]
        with pytest.raises(SystemExit):
            app()
    
    def test_link_script_mode_no_groups(self, temp_dir, capsys):
        """测试clean link --mode script命令（无重复文件组）"""
        script_path = os.path.join(temp_dir, 'link.bat')
        sys.argv = ['', 'link', '--yes', '--mode', 'script', '--script', script_path]
        with pytest.raises(SystemExit):
            app()
    
    def test_invalid_strategy(self, capsys):
        """测试无效的排序策略"""
        sys.argv = ['', 'delete', '--strategy', 'invalid', '--yes']
        with pytest.raises(SystemExit):
            app()
        
        captured = capsys.readouterr()
        assert '无效' in captured.out or '错误' in captured.out
    
    def test_invalid_mode(self, capsys):
        """测试无效的执行模式"""
        sys.argv = ['', 'delete', '--mode', 'invalid', '--yes']
        with pytest.raises(SystemExit):
            app()
        
        captured = capsys.readouterr()
        assert '无效' in captured.out or '错误' in captured.out
