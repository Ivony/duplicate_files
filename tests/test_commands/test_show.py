import pytest
import os
import tempfile
import sys
from commands.show import app

class TestShowCommand:
    def test_groups_command(self, capsys):
        """测试show groups命令"""
        sys.argv = ['', 'groups']
        with pytest.raises(SystemExit):
            app()
        
        captured = capsys.readouterr()
        assert '重复文件组' in captured.out
    
    def test_groups_hash_filter(self, capsys):
        """测试show groups --hash参数"""
        sys.argv = ['', 'groups', '--hash', 'abc123']
        with pytest.raises(SystemExit):
            app()
        
        captured = capsys.readouterr()
        assert '哈希值' in captured.out or '重复文件组' in captured.out
    
    def test_files_command(self, temp_dir, capsys):
        """测试show files命令"""
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        sys.argv = ['', 'files', temp_dir]
        with pytest.raises(SystemExit):
            app()
        
        captured = capsys.readouterr()
        assert '路径' in captured.out
    
    def test_stats_command(self, capsys):
        """测试show stats命令"""
        sys.argv = ['', 'stats']
        with pytest.raises(SystemExit):
            app()
        
        captured = capsys.readouterr()
        assert '文件统计信息' in captured.out
