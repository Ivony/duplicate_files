import pytest
import os
import tempfile
import sys
from commands.index import app

class TestIndexCommand:
    def test_scan_command(self, temp_dir, capsys):
        """测试index scan命令"""
        # 创建测试文件
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        # 执行命令
        sys.argv = ['', 'scan', temp_dir]
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '开始扫描路径' in captured.out
        assert '扫描完成' in captured.out
    
    def test_rebuild_command(self, temp_dir, capsys):
        """测试index rebuild命令"""
        # 创建测试文件
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        # 执行命令
        sys.argv = ['', 'rebuild']
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '索引清理' in captured.out
        assert '重建重复文件组' in captured.out
    
    def test_clear_command(self, temp_dir, capsys):
        """测试index clear命令"""
        # 执行命令
        sys.argv = ['', 'clear', '--all', '--force']
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '已清除文件索引' in captured.out
