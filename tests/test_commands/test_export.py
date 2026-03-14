import pytest
import os
import tempfile
import sys
from commands.export import app

class TestExportCommand:
    def test_csv_command(self, temp_dir, capsys):
        """测试export csv命令"""
        # 执行命令
        output_path = os.path.join(temp_dir, 'export.csv')
        sys.argv = ['', 'csv', output_path]
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '导出为CSV格式' in captured.out
        assert os.path.exists(output_path)
    
    def test_json_command(self, temp_dir, capsys):
        """测试export json命令"""
        # 执行命令
        output_path = os.path.join(temp_dir, 'export.json')
        sys.argv = ['', 'json', output_path]
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '导出为JSON格式' in captured.out
        assert os.path.exists(output_path)
    
    def test_report_command(self, temp_dir, capsys):
        """测试export report命令"""
        # 执行命令
        output_path = os.path.join(temp_dir, 'report.txt')
        sys.argv = ['', 'report', output_path]
        with pytest.raises(SystemExit):
            app()
        
        # 验证输出
        captured = capsys.readouterr()
        assert '生成详细报告' in captured.out
        assert os.path.exists(output_path)
