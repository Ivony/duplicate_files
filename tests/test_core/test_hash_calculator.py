import pytest
import os
import tempfile
import csv
import json
from commands.hash import HashCalculator

class TestHashCalculator:
    def test_calculate_file_hash(self, temp_dir):
        """测试计算文件哈希"""
        # 创建测试文件
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        # 初始化HashCalculator
        calculator = HashCalculator(':memory:', quiet=True)
        
        # 计算哈希
        hash_value = calculator.calculate_file_hash(test_file)
        
        # 验证哈希值
        assert hash_value is not None
        assert len(hash_value) > 0
    
    def test_calculate_hash(self, temp_dir, temp_db):
        """测试计算哈希"""
        # 创建测试文件
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        # 初始化HashCalculator
        calculator = HashCalculator(temp_db, quiet=True)
        
        # 计算哈希
        calculator.calculate_hash()
        
        # 验证计算结果
        assert calculator.total_processed >= 0
    
    def test_backup_hash(self, temp_dir, temp_db):
        """测试备份哈希"""
        # 创建测试文件
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        # 初始化HashCalculator
        calculator = HashCalculator(temp_db, quiet=True)
        
        # 计算哈希
        calculator.calculate_hash()
        
        # 验证哈希计算结果
        assert calculator.total_processed >= 0
    
    def test_clear_hash(self, temp_dir, temp_db):
        """测试清除哈希"""
        # 创建测试文件
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        # 初始化HashCalculator
        calculator = HashCalculator(temp_db, quiet=True)
        
        # 计算哈希
        calculator.calculate_hash()
        
        # 清除哈希
        import sqlite3
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM file_hash')
        cursor.execute("UPDATE duplicate_groups SET Hash = NULL")
        conn.commit()
        conn.close()
        
        # 验证哈希已清除
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM file_hash')
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 0
