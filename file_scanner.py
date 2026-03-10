import os
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

class FileScanner:
    def __init__(self, db_path):
        self.db_path = db_path
        self.total_scanned = 0
        self.total_indexed = 0
        self.start_time = 0
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建duplicate表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS duplicate (
            Filepath TEXT PRIMARY KEY,
            Size INTEGER,
            Modified REAL,
            Disk TEXT
        )
        ''')
        
        # 创建Hash表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Hash (
            Filepath TEXT PRIMARY KEY,
            Size INTEGER,
            Hash TEXT,
            Modified REAL
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def scan_file(self, file_path):
        try:
            stat = os.stat(file_path)
            disk = os.path.splitdrive(file_path)[0].upper()
            return {
                'filepath': file_path,
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'disk': disk
            }
        except Exception as e:
            # 忽略无法访问的文件
            return None
    
    def process_batch(self, files):
        conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level='DEFERRED')
        cursor = conn.cursor()
        
        batch_size = 1000
        for i in range(0, len(files), batch_size):
            batch = files[i:i+batch_size]
            if not batch:
                continue
            
            placeholders = ','.join(['(?, ?, ?, ?)'] * len(batch))
            values = []
            for file_info in batch:
                values.extend([file_info['filepath'], file_info['size'], file_info['modified'], file_info['disk']])
            
            cursor.execute(f'''
            INSERT OR REPLACE INTO duplicate (Filepath, Size, Modified, Disk)
            VALUES {placeholders}
            ''', values)
            conn.commit()
        
        conn.close()
    
    def scan_directory(self, path):
        self.init_database()
        self.total_scanned = 0
        self.total_indexed = 0
        self.start_time = time.time()
        
        print(f"开始扫描路径: {path}")
        
        files_to_process = []
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                self.total_scanned += 1
                
                file_info = self.scan_file(file_path)
                if file_info:
                    files_to_process.append(file_info)
                    self.total_indexed += 1
                
                if self.total_scanned % 1000 == 0:
                    current_time = time.time()
                    elapsed = current_time - self.start_time
                    speed = self.total_scanned / elapsed if elapsed > 0 else 0
                    print(f"已扫描: {self.total_scanned} 文件, 已索引: {self.total_indexed} 文件 ({speed:.1f} 文件/秒)")
        
        # 处理剩余文件
        if files_to_process:
            print(f"正在处理 {len(files_to_process)} 个文件...")
            self.process_batch(files_to_process)
        
        elapsed = time.time() - self.start_time
        speed = self.total_scanned / elapsed if elapsed > 0 else 0
        
        print(f"\n扫描完成！")
        print(f"总扫描文件数: {self.total_scanned}")
        print(f"总索引文件数: {self.total_indexed}")
        print(f"耗时: {elapsed:.2f} 秒")
        print(f"平均速度: {speed:.1f} 文件/秒")

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: python file_scanner.py <path>")
        sys.exit(1)
    
    scanner = FileScanner('file_index.db')
    scanner.scan_directory(sys.argv[1])