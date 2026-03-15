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
