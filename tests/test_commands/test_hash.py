import pytest
import os
import tempfile
import sys
from commands.hash import app

class TestHashCommand:
    def test_calc_command(self, temp_dir, capsys):
        """测试hash calc命令"""
        # 创建测试文件
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        # 执行命令
        sys.argv = ['', 'calc']
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '哈希计算' in captured.out
    
    def test_verify_command(self, capsys):
        """测试hash verify命令"""
        # 执行命令
        sys.argv = ['', 'verify']
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '哈希计算' in captured.out
    
    def test_status_command(self, capsys):
        """测试hash status命令"""
        # 执行命令
        sys.argv = ['', 'status']
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '哈希计算状态' in captured.out
    
    def test_clear_command(self, capsys):
        """测试hash clear命令"""
        # 执行命令
        sys.argv = ['', 'clear', '--all']
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '已清除所有哈希值' in captured.out
