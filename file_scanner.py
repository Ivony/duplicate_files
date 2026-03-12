import os
import sqlite3
import time
import csv
from datetime import datetime
from config_manager import ConfigManager
import re

class FileScanner:
    def __init__(self, db_path='file_index.db'):
        self.db_path = db_path
        self.total_scanned = 0
        self.total_indexed = 0
        self.start_time = 0
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path, timeout=30.0, isolation_level='DEFERRED')
    
    def is_path_excluded(self, file_path):
        """检查路径是否被排除"""
        config_manager = ConfigManager()
        for pattern in config_manager.get_excluded_patterns():
            if re.match(pattern, file_path):
                return True
        return False
    
    def scan_file(self, file_path):
        """扫描单个文件"""
        try:
            stat = os.stat(file_path)
            _, ext = os.path.splitext(file_path)
            return {
                'filename': file_path,
                'extension': ext.lower() if ext else '',
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'accessed': datetime.fromtimestamp(stat.st_atime).isoformat()
            }
        except Exception as e:
            print(f"扫描文件失败 {file_path}: {e}")
            return None
    
    def scan_directory(self, path):
        """扫描指定路径下的所有文件"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        self.total_scanned = 0
        self.total_indexed = 0
        self.start_time = time.time()
        
        print(f"开始扫描路径: {path}")
        
        files_to_process = []
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                self.total_scanned += 1
                
                if self.is_path_excluded(file_path):
                    continue
                
                file_info = self.scan_file(file_path)
                if file_info:
                    files_to_process.append(file_info)
                    self.total_indexed += 1
                
                if self.total_scanned % 1000 == 0:
                    current_time = time.time()
                    elapsed = current_time - self.start_time
                    speed = self.total_scanned / elapsed if elapsed > 0 else 0
                    print(f"已扫描: {self.total_scanned} 文件, 已索引: {self.total_indexed} 文件 ({speed:.1f} 文件/秒)")
        
        # 批量插入到files表
        if files_to_process:
            print(f"正在处理 {len(files_to_process)} 个文件...")
            batch_size = 1000
            for i in range(0, len(files_to_process), batch_size):
                batch = files_to_process[i:i+batch_size]
                placeholders = ','.join(['(?, ?, ?, ?, ?, ?)'] * len(batch))
                values = []
                for file_info in batch:
                    values.extend([
                        file_info['filename'],
                        file_info['extension'],
                        file_info['size'],
                        file_info['created'],
                        file_info['modified'],
                        file_info['accessed']
                    ])
                
                cursor.execute(f'''
                INSERT OR REPLACE INTO files (Filename, Extension, Size, Created, Modified, Accessed)
                VALUES {placeholders}
                ''', values)
                conn.commit()
        
        elapsed = time.time() - self.start_time
        speed = self.total_scanned / elapsed if elapsed > 0 else 0
        
        print(f"\n扫描完成！")
        print(f"总扫描文件数: {self.total_scanned}")
        print(f"总索引文件数: {self.total_indexed}")
        print(f"耗时: {elapsed:.2f} 秒")
        print(f"平均速度: {speed:.1f} 文件/秒")
        
        conn.close()
    
    def scan_from_csv(self, csv_path, encoding='utf-8'):
        """从CSV文件导入文件列表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        self.total_scanned = 0
        self.total_indexed = 0
        self.start_time = time.time()
        
        print(f"开始从CSV文件导入: {csv_path} (编码: {encoding})")
        
        files_to_process = []
        try:
            with open(csv_path, 'r', encoding=encoding) as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    self.total_scanned += 1
                    
                    # 假设CSV文件包含filename字段
                    filename = row.get('filename', '')
                    if not filename or not os.path.exists(filename):
                        continue
                    
                    if self.is_path_excluded(filename):
                        continue
                    
                    file_info = self.scan_file(filename)
                    if file_info:
                        files_to_process.append(file_info)
                        self.total_indexed += 1
                    
                    if self.total_scanned % 1000 == 0:
                        current_time = time.time()
                        elapsed = current_time - self.start_time
                        speed = self.total_scanned / elapsed if elapsed > 0 else 0
                        print(f"已处理: {self.total_scanned} 文件, 已索引: {self.total_indexed} 文件 ({speed:.1f} 文件/秒)")
        
        except Exception as e:
            print(f"读取CSV文件失败: {e}")
            conn.close()
            return
        
        # 批量插入到files表
        if files_to_process:
            print(f"正在处理 {len(files_to_process)} 个文件...")
            batch_size = 1000
            for i in range(0, len(files_to_process), batch_size):
                batch = files_to_process[i:i+batch_size]
                placeholders = ','.join(['(?, ?, ?, ?, ?)'] * len(batch))
                values = []
                for file_info in batch:
                    values.extend([
                        file_info['filename'],
                        file_info['extension'],
                        file_info['size'],
                        file_info['created'],
                        file_info['modified'],
                        file_info['accessed']
                    ])
                
                cursor.execute(f'''
                INSERT OR REPLACE INTO files (Filename, Extension, Size, Created, Modified, Accessed)
                VALUES {placeholders}
                ''', values)
                conn.commit()
        
        elapsed = time.time() - self.start_time
        speed = self.total_scanned / elapsed if elapsed > 0 else 0
        
        print(f"\nCSV导入完成！")
        print(f"总处理文件数: {self.total_scanned}")
        print(f"总索引文件数: {self.total_indexed}")
        print(f"耗时: {elapsed:.2f} 秒")
        print(f"平均速度: {speed:.1f} 文件/秒")
        
        conn.close()

if __name__ == '__main__':
    import sys
    
    scanner = FileScanner()
    
    if len(sys.argv) < 2:
        print("用法: python file_scanner.py <command> [args]")
        print("\n可用命令:")
        print("  scan <path>           - 扫描指定路径下的所有文件")
        print("  import <csv>           - 从CSV文件导入文件列表")
        print("                          --encoding <编码>  指定CSV文件的字符编码（默认utf-8）")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'scan':
        if len(sys.argv) < 3:
            print("错误: 请指定要扫描的路径")
            sys.exit(1)
        path = sys.argv[2]
        if not os.path.exists(path) or not os.path.isdir(path):
            print(f"错误: 路径不存在或不是目录: {path}")
            sys.exit(1)
        scanner.scan_directory(path)
    elif command == 'import':
        if len(sys.argv) < 3:
            print("错误: 请指定CSV文件路径")
            sys.exit(1)
        csv_path = sys.argv[2]
        if not os.path.exists(csv_path) or not os.path.isfile(csv_path):
            print(f"错误: CSV文件不存在: {csv_path}")
            sys.exit(1)
        
        encoding = 'utf-8'
        for i, arg in enumerate(sys.argv):
            if arg == '--encoding' and i + 1 < len(sys.argv):
                encoding = sys.argv[i + 1]
        
        scanner.scan_from_csv(csv_path, encoding)
    else:
        print(f"未知命令: {command}")
        sys.exit(1)