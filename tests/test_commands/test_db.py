import pytest
import os
import tempfile
import sys
from commands.db import app

class TestDbCommand:
    def test_check_command(self, capsys):
        """测试db check命令"""
        # 执行命令
        sys.argv = ['', 'check']
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '数据库中的表' in captured.out
    
    def test_optimize_command(self, capsys):
        """测试db optimize命令"""
        # 执行命令
        sys.argv = ['', 'optimize']
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '数据库优化' in captured.out
    

    
    def test_init_command(self, capsys):
        """测试db init命令"""
        # 执行命令（添加--force参数避免交互式输入）
        sys.argv = ['', 'init', '--force']
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '重建数据库' in captured.out
