import os
import sqlite3
import time
import csv
from datetime import datetime
import config
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
        for pattern in config.excluded_paths:
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
        
        # 扫描完成后自动建立重复文件组
        self.build_duplicate_groups()
    
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
        
        # 导入完成后自动建立重复文件组
        self.build_duplicate_groups()
    
    def build_duplicate_groups(self):
        """建立重复文件组"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        print("\n开始建立重复文件组...")
        
        # 清空现有的重复文件组数据
        cursor.execute('DELETE FROM duplicate_files')
        cursor.execute('DELETE FROM duplicate_groups')
        conn.commit()
        
        # 创建临时表来存储文件信息
        cursor.execute('''
        CREATE TEMP TABLE IF NOT EXISTS temp_files AS
        SELECT Filename, Extension, Size
        FROM files
        WHERE Size > 0
        ''')
        
        # 插入到duplicate_groups表
        cursor.execute('''
        INSERT INTO duplicate_groups (Size, Extension)
        SELECT Size, Extension
        FROM temp_files
        GROUP BY Size, Extension
        HAVING COUNT(*) > 1
        ''')
        
        # 重新插入到duplicate_files表
        cursor.execute('''
        INSERT INTO duplicate_files (Filepath, Group_ID)
        SELECT 
            tf.Filename,
            dg.ID
        FROM temp_files tf
        INNER JOIN duplicate_groups dg ON tf.Size = dg.Size AND tf.Extension = dg.Extension
        ''')
        
        # 获取创建的组数量
        cursor.execute('SELECT COUNT(*) FROM duplicate_groups')
        group_count = cursor.fetchone()[0]
        
        # 获取有多少文件被分配到组
        cursor.execute('SELECT COUNT(*) FROM duplicate_files')
        file_count = cursor.fetchone()[0]
        
        # 清理临时表
        cursor.execute('DROP TABLE IF EXISTS temp_files')
        
        conn.commit()
        conn.close()
        
        print(f"\n重复文件组建立完成！")
        print(f"创建了 {group_count} 个重复文件组")
        print(f"共有 {file_count} 个文件被分配到组中")

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