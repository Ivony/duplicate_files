import sqlite3
import os
import hashlib
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

class HashCalculator:
    def __init__(self, db_path='file_index.db'):
        self.db_path = db_path
        self.total_processed = 0
        self.total_calculated = 0
        self.total_skipped = 0
        self.start_time = 0
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path, timeout=60.0, isolation_level='IMMEDIATE')
    
    def get_file_info(self, file_path):
        """获取文件信息"""
        try:
            if not os.path.exists(file_path):
                return None
            
            stat = os.stat(file_path)
            return {
                'size': stat.st_size,
                'modified': stat.st_mtime
            }
        except Exception as e:
            print(f"获取文件信息失败 {file_path}: {e}")
            return None
    
    def calculate_file_hash(self, file_path):
        """计算单个文件的哈希值"""
        try:
            file_info = self.get_file_info(file_path)
            if file_info is None:
                return None
            
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            
            return {
                'filepath': file_path,
                'size': file_info['size'],
                'hash': hasher.hexdigest(),
                'modified': file_info['modified'],
                'created_at': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"计算哈希失败 {file_path}: {e}")
            return None
    
    def calculate_hash(self, mode='default'):
        """计算哈希值
        
        Args:
            mode: 计算模式
                'default' - 默认模式：检查并更新
                'new' - 仅新增模式：仅计算从未计算过hash值的文件
                'force' - 强制更新模式：对duplicate_files表中所有文件重新计算哈希值
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        self.total_processed = 0
        self.total_calculated = 0
        self.total_skipped = 0
        self.start_time = time.time()
        
        print(f"开始计算哈希值（模式: {mode})...")
        
        # 获取需要计算哈希的文件列表
        if mode == 'new':
            # 仅新增模式：只获取从未计算过哈希值的文件
            cursor.execute('''
            SELECT df.Filepath, f.Size, f.Modified
            FROM duplicate_files df
            INNER JOIN files f ON df.Filepath = f.Filename
            WHERE df.Filepath NOT IN (SELECT Filepath FROM file_hash)
            ''')
        elif mode == 'force':
            # 强制更新模式：获取所有文件
            cursor.execute('''
            SELECT df.Filepath, f.Size, f.Modified
            FROM duplicate_files df
            INNER JOIN files f ON df.Filepath = f.Filename
            ''')
        else:
            # 默认模式：获取所有文件，后续判断是否需要重新计算
            cursor.execute('''
            SELECT df.Filepath, f.Size, f.Modified
            FROM duplicate_files df
            INNER JOIN files f ON df.Filepath = f.Filename
            ''')
        
        files = cursor.fetchall()
        conn.close()
        
        total_files = len(files)
        print(f"找到 {total_files} 个文件需要处理")
        
        # 批量计算哈希值
        batch_size = 100
        for i in range(0, len(files), batch_size):
            batch = files[i:i+batch_size]
            self.process_batch(batch, mode, total_files)
        
        elapsed = time.time() - self.start_time
        speed = self.total_processed / elapsed if elapsed > 0 else 0
        
        print(f"\n哈希计算完成！")
        print(f"总处理: {self.total_processed} 个文件")
        print(f"计算哈希: {self.total_calculated} 个文件")
        print(f"跳过: {self.total_skipped} 个文件")
        print(f"耗时: {elapsed:.2f} 秒")
        print(f"平均速度: {speed:.1f} 文件/秒")
    
    def process_batch(self, batch, mode, total_files):
        """处理一批文件的哈希计算"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 获取已计算的哈希值
        file_paths = [file[0] for file in batch]
        placeholders = ','.join(['?'] * len(file_paths))
        cursor.execute(f'SELECT Filepath, Size, Modified FROM file_hash WHERE Filepath IN ({placeholders})', file_paths)
        existing_hashes = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
        
        # 计算哈希值
        results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_file = {
                executor.submit(self.calculate_file_hash, file_path): file_path
                for file_path, _, _ in batch
            }
            
            for future in as_completed(future_to_file):
                result = future.result()
                if result:
                    results.append(result)
                    self.total_processed += 1
                    
                    # 每10个文件或每批结束时显示进度
                    if self.total_processed % 10 == 0 or self.total_processed == total_files:
                        current_time = time.time()
                        elapsed = current_time - self.start_time
                        speed = self.total_processed / elapsed if elapsed > 0 else 0
                        progress = (self.total_processed / total_files * 100) if total_files > 0 else 0
                        print(f"进度: {self.total_processed}/{total_files} ({progress:.1f}%) - 速度: {speed:.1f} 文件/秒")
        
        # 更新数据库
        for result in results:
            file_path = result['filepath']
            actual_size = result['size']
            actual_modified = result['modified']
            hash_val = result['hash']
            created_at = result['created_at']
            
            should_calculate = True
            
            if mode == 'default':
                # 默认模式：检查是否需要重新计算
                if file_path in existing_hashes:
                    db_size, db_modified = existing_hashes[file_path]
                    if actual_size == db_size and abs(actual_modified - db_modified) < 0.001:
                        should_calculate = False
                        self.total_skipped += 1
                    else:
                        print(f"文件变化 {file_path}: 大小或修改时间不一致")
            
            if should_calculate:
                cursor.execute('''
                INSERT OR REPLACE INTO file_hash (Filepath, Size, Hash, Modified, created_at)
                VALUES (?, ?, ?, ?, ?)
                ''', (file_path, actual_size, hash_val, actual_modified, created_at))
                self.total_calculated += 1
        
        conn.commit()
        conn.close()

if __name__ == '__main__':
    import sys
    
    calculator = HashCalculator()
    
    if len(sys.argv) < 2:
        print("用法: python hash_calculator.py <command> [args]")
        print("\n可用命令:")
        print("  calculate              - 计算哈希值（默认模式）")
        print("  calculate --new       - 仅计算从未计算过hash值的文件")
        print("  calculate --force     - 强制更新模式：对所有文件重新计算哈希值")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'calculate':
        mode = 'default'
        if '--new' in sys.argv:
            mode = 'new'
        elif '--force' in sys.argv:
            mode = 'force'
        
        calculator.calculate_hash(mode)
    else:
        print(f"未知命令: {command}")
        sys.exit(1)