import pytest
import os
import tempfile
from commands.index import IndexManager, FileScanner

class TestIndexManager:
    def test_clean_files(self, temp_dir, temp_db):
        """测试清除文件索引"""
        # 创建测试文件
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        # 扫描文件
        scanner = FileScanner(temp_db)
        scanner.scan_directory(temp_dir)
        
        # 初始化IndexManager
        manager = IndexManager(temp_db)
        
        # 清除文件索引
        manager.clean_files()
        
        # 验证文件索引已清除
        import sqlite3
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM files')
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 0
    
    def test_rebuild_duplicate_groups(self, temp_dir, temp_db):
        """测试重建重复文件组"""
        # 创建重复文件
        file1 = os.path.join(temp_dir, 'test1.txt')
        file2 = os.path.join(temp_dir, 'test2.txt')
        with open(file1, 'w') as f:
            f.write('test content')
        with open(file2, 'w') as f:
            f.write('test content')  # 与file1内容相同
        
        # 扫描文件
        scanner = FileScanner(temp_db)
        scanner.scan_directory(temp_dir)
        
        # 初始化IndexManager
        manager = IndexManager(temp_db)
        
        # 重建重复文件组
        groups_created, files_assigned = manager.rebuild_duplicate_groups()
        
        # 验证重建结果
        assert groups_created >= 1
        assert files_assigned >= 2
    
    def test_clean_index(self, temp_dir, temp_db):
        """测试清理索引"""
        # 创建测试文件
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        # 扫描文件
        scanner = FileScanner(temp_db)
        scanner.scan_directory(temp_dir)
        
        # 初始化IndexManager
        manager = IndexManager(temp_db)
        
        # 清理索引
        manager.clean_index()
        
        # 验证索引清理结果
        import sqlite3
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM files')
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 1
    
    def test_clean_files_by_pattern(self, temp_dir, temp_db):
        """测试按模式清除文件索引"""
        # 创建测试文件
        file1 = os.path.join(temp_dir, 'test1.txt')
        file2 = os.path.join(temp_dir, 'test2.csv')
        with open(file1, 'w') as f:
            f.write('test content 1')
        with open(file2, 'w') as f:
            f.write('test content 2')
        
        # 扫描文件
        scanner = FileScanner(temp_db)
        scanner.scan_directory(temp_dir)
        
        # 初始化IndexManager
        manager = IndexManager(temp_db)
        
        # 按模式清除文件索引
        manager.clean_files_by_pattern('*.txt')
        
        # 验证清除结果
        import sqlite3
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM files')
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 1  # 只保留了test2.csv
