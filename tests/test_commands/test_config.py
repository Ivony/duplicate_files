import pytest
import os
import tempfile
import sys
from commands.config import app

class TestConfigCommand:
    def test_limit_command(self, temp_dir, capsys):
        """测试config limit命令"""
        # 执行命令
        sys.argv = ['', 'limit', temp_dir]
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '已设置检索范围限制' in captured.out
    
    def test_limit_clear_command(self, capsys):
        """测试config limit clear命令"""
        # 执行命令
        sys.argv = ['', 'limit', 'clear']
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '已解除检索范围限制' in captured.out
    
    def test_exclude_add_command(self, capsys):
        """测试config exclude add命令"""
        # 执行命令
        sys.argv = ['', 'exclude', 'add', '*.tmp']
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '已添加排除模式' in captured.out
    
    def test_exclude_list_command(self, capsys):
        """测试config exclude list命令"""
        # 执行命令
        sys.argv = ['', 'exclude', 'list']
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '当前排除模式' in captured.out
    
    def test_exclude_remove_command(self, capsys):
        """测试config exclude remove命令"""
        # 执行命令
        sys.argv = ['', 'exclude', 'remove', '*.tmp']
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '已移除排除模式' in captured.out
