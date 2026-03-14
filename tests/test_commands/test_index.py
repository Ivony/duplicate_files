import pytest
import os
import tempfile
import sys
from commands.index import app

class TestIndexCommand:
    def test_scan_command(self, temp_dir, capsys):
        """测试index scan命令"""
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        sys.argv = ['', 'scan', temp_dir]
        with pytest.raises(SystemExit):
            app()
        
        captured = capsys.readouterr()
        assert '扫描文件' in captured.out
        assert '扫描完成' in captured.out
    
    def test_rebuild_command(self, temp_dir, capsys):
        """测试index rebuild命令"""
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        sys.argv = ['', 'rebuild']
        with pytest.raises(SystemExit):
            app()
        
        captured = capsys.readouterr()
        assert '重建重复文件组' in captured.out
    
    def test_clear_command(self, temp_dir, capsys):
        """测试index clear命令"""
        sys.argv = ['', 'clear', '--all', '--force']
        with pytest.raises(SystemExit):
            app()
        
        captured = capsys.readouterr()
        assert '已清除' in captured.out
