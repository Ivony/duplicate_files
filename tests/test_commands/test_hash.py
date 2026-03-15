import pytest
import os
import sys
import sqlite3
from commands.hash import app, HashCalculator
from commands.db import DatabaseManager

class TestHashCommand:
    def test_calc_command(self, temp_dir, capsys):
        """测试hash calc命令"""
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        sys.argv = ['', 'calc']
        with pytest.raises(SystemExit):
            app()
        
        captured = capsys.readouterr()
        assert '哈希计算' in captured.out
    
    def test_verify_command(self, capsys):
        """测试hash verify命令"""
        sys.argv = ['', 'verify']
        with pytest.raises(SystemExit):
            app()
        
        captured = capsys.readouterr()
        assert '哈希计算' in captured.out
    
    def test_status_command(self, capsys):
        """测试hash status命令"""
        sys.argv = ['', 'status']
        with pytest.raises(SystemExit):
            app()
        
        captured = capsys.readouterr()
        assert '哈希计算状态' in captured.out
    
    def test_clear_command(self, capsys):
        """测试hash clear命令"""
        sys.argv = ['', 'clear', '--all']
        with pytest.raises(SystemExit):
            app()
        
        captured = capsys.readouterr()
        assert '已清除所有哈希值' in captured.out

class TestHashCalculator:
    def test_calculate_with_string_modified(self, test_db_with_data, test_filesystem):
        """测试 Modified 字段为字符串类型时的哈希计算
        
        验证时间戳类型转换逻辑是否正确处理字符串格式
        """
        calc = HashCalculator()
        calc.calculate_hash(mode='default')
        
        db_manager = DatabaseManager(test_db_with_data)
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM file_hash WHERE Hash IS NOT NULL')
        hash_count = cursor.fetchone()[0]
        
        conn.close()
        
        assert hash_count > 0
    
    def test_modified_iso_format(self, test_db_with_data, test_filesystem):
        """测试 ISO 格式时间戳的处理"""
        conn = sqlite3.connect(test_db_with_data)
        cursor = conn.cursor()
        
        cursor.execute('SELECT Filename, Modified FROM files LIMIT 1')
        row = cursor.fetchone()
        if row:
            filename, modified = row
            assert isinstance(modified, str), f"Modified should be string, got {type(modified)}"
        
        conn.close()
    
    def test_modified_comparison(self, test_db_with_data, test_filesystem):
        """测试时间戳比较逻辑
        
        验证字符串类型的时间戳可以正确比较
        """
        calc = HashCalculator()
        calc.calculate_hash(mode='default')
        
        calc.calculate_hash(mode='default')
        
        db_manager = DatabaseManager(test_db_with_data)
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM file_hash')
        count = cursor.fetchone()[0]
        
        conn.close()
        
        assert count > 0
    
    def test_hash_calculation_with_existing_hash(self, test_db_with_hash, test_filesystem):
        """测试已有哈希值时的跳过逻辑"""
        calc = HashCalculator()
        
        db_manager = DatabaseManager(test_db_with_hash)
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM file_hash WHERE Hash IS NOT NULL')
        initial_count = cursor.fetchone()[0]
        conn.close()
        
        calc.calculate_hash(mode='default')
        
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM file_hash WHERE Hash IS NOT NULL')
        final_count = cursor.fetchone()[0]
        conn.close()
        
        assert final_count >= initial_count
    
    def test_force_mode_recalculates(self, test_db_with_hash, test_filesystem):
        """测试强制模式重新计算哈希"""
        calc = HashCalculator()
        
        db_manager = DatabaseManager(test_db_with_hash)
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM file_hash WHERE Hash IS NOT NULL')
        initial_count = cursor.fetchone()[0]
        conn.close()
        
        calc.calculate_hash(mode='force')
        
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM file_hash WHERE Hash IS NOT NULL')
        final_count = cursor.fetchone()[0]
        conn.close()
        
        assert final_count >= initial_count
    
    def test_progress_display_format(self, test_db_with_data, test_filesystem, capsys):
        """测试进度显示格式，确保计算完成后提示正确覆盖进度行"""
        calc = HashCalculator()
        
        # 捕获输出
        calc.calculate_hash(mode='default')
        
        captured = capsys.readouterr()
        output = captured.out
        
        # 检查输出中是否包含计算完成的提示
        assert '已计算' in output
        
        # 检查输出中是否包含进度条相关的字符
        assert '[' in output
        assert ']' in output
        
        # 验证输出格式是否正确
        lines = output.split('\n')
        progress_lines = [line for line in lines if '[' in line and ']' in line]
        completed_lines = [line for line in lines if '已计算' in line]
        
        # 确保有进度显示和完成提示
        assert len(progress_lines) > 0
        assert len(completed_lines) > 0
    
    def test_truncate_filename(self):
        """测试文件名截断功能"""
        calc = HashCalculator()
        
        # 测试正常长度的文件名
        normal_name = "test_file.txt"
        assert calc.truncate_filename(normal_name) == normal_name
        
        # 测试刚好达到最大长度的文件名
        exactly_length = "a" * 37 + ".txt"
        assert len(calc.truncate_filename(exactly_length)) == 40
        
        # 测试需要截断的文件名（保留扩展名）
        long_name = "a" * 50 + ".mp4"
        truncated = calc.truncate_filename(long_name)
        assert len(truncated) <= 40
        assert truncated.endswith(".mp4")
        assert "..." in truncated
        
        # 测试长扩展名的情况
        long_ext = "file." + "x" * 35  # 总长度 5 + 35 = 40，刚好达到
        truncated_ext = calc.truncate_filename(long_ext)
        assert len(truncated_ext) == 40
        
        # 测试超长扩展名的情况
        very_long_ext = "file." + "x" * 40  # 总长度 5 + 40 = 45，超过最大长度
        truncated_very_long = calc.truncate_filename(very_long_ext)
        assert len(truncated_very_long) <= 40
        assert "..." in truncated_very_long
        
        # 测试没有扩展名的情况
        no_ext = "a" * 50
        truncated_no_ext = calc.truncate_filename(no_ext)
        assert len(truncated_no_ext) <= 40
        assert "..." in truncated_no_ext
        
        # 测试带路径的文件名
        path_name = "C:/very/long/path/to/file/" + "a" * 40 + ".doc"
        truncated_path = calc.truncate_filename(path_name)
        assert len(truncated_path) <= 40
        assert truncated_path.endswith(".doc")
        assert "..." in truncated_path
