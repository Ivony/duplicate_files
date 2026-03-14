import pytest
import os
import tempfile
import sys
from commands.clean import app

class TestCleanCommand:
    def test_clean_command(self, capsys):
        """测试clean run命令"""
        # 执行命令（模拟运行）
        sys.argv = ['', 'run', '--dryrun', '--yes']
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '模式: 模拟执行' in captured.out
    
    def test_script_command(self, temp_dir, capsys):
        """测试clean script命令"""
        # 执行命令
        script_path = os.path.join(temp_dir, 'cleanup.bat')
        sys.argv = ['', 'script', '--output', script_path]
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert os.path.exists(script_path)
