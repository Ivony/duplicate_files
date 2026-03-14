import pytest
import os
import tempfile
import csv
from commands.index import FileScanner

class TestFileScanner:
    def test_scan_file(self, temp_dir):
        """测试扫描单个文件"""
        # 创建测试文件
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        # 初始化FileScanner
        scanner = FileScanner(':memory:')
        
        # 扫描文件
        file_info = scanner.scan_file(test_file)
        
        # 验证扫描结果
        assert file_info is not None
        assert file_info['filename'] == os.path.normcase(test_file)
        assert file_info['extension'] == '.txt'
        assert file_info['size'] == 12
        assert 'created' in file_info
        assert 'modified' in file_info
        assert 'accessed' in file_info
    
    def test_is_path_excluded(self, temp_dir):
        """测试路径排除功能"""
        # 初始化FileScanner
        scanner = FileScanner(':memory:')
        
        # 测试默认情况下路径不被排除
        test_file = os.path.join(temp_dir, 'test.txt')
        assert not scanner.is_path_excluded(test_file)
    
    def test_scan_directory(self, temp_dir, temp_db):
        """测试扫描目录"""
        # 创建测试文件
        for i in range(3):
            test_file = os.path.join(temp_dir, f'test{i}.txt')
            with open(test_file, 'w') as f:
                f.write(f'test content {i}')
        
        # 初始化FileScanner
        scanner = FileScanner(temp_db)
        
        # 扫描目录
        scanner.scan_directory(temp_dir)
        
        # 验证扫描结果
        assert scanner.total_scanned == 3
        assert scanner.total_indexed == 3
    
    def test_scan_from_csv(self, temp_dir, temp_db):
        """测试从CSV导入"""
        # 创建测试文件
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        # 创建CSV文件
        csv_path = os.path.join(temp_dir, 'files.csv')
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['filename'])
            writer.writerow([test_file])
        
        # 初始化FileScanner
        scanner = FileScanner(temp_db)
        
        # 从CSV导入
        scanner.scan_from_csv(csv_path)
        
        # 验证导入结果
        assert scanner.total_scanned == 1
        assert scanner.total_indexed == 1
