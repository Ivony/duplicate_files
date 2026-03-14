import pytest
import os
import tempfile
import sys
from commands.show import app

class TestShowCommand:
    def test_groups_command(self, capsys):
        """测试show groups命令"""
        # 执行命令
        sys.argv = ['', 'groups']
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '重复文件组' in captured.out
    
    def test_files_command(self, temp_dir, capsys):
        """测试show files命令"""
        # 创建测试文件
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        # 执行命令
        sys.argv = ['', 'files', temp_dir]
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '路径' in captured.out
    
    def test_hash_command(self, capsys):
        """测试show hash命令"""
        # 执行命令
        sys.argv = ['', 'hash', 'test_hash']
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '哈希值' in captured.out
    
    def test_stats_command(self, capsys):
        """测试show stats命令"""
        # 执行命令
        sys.argv = ['', 'stats']
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '数据汇总报告' in captured.out
