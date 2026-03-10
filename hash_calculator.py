import sqlite3
import os
import hashlib
import time
from datetime import datetime

class HashCalculator:
    def __init__(self, db_path='file_index.db'):
        self.db_path = db_path
        self.total_processed = 0
        self.total_calculated = 0
        self.total_skipped = 0
        self.total_size_processed = 0
        self.total_size_calculated = 0
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
        self.total_size_processed = 0
        self.total_size_calculated = 0
        self.start_time = time.time()
        
        # 显示模式说明
        mode_desc = {
            'default': '默认模式 - 检查并更新变化的文件',
            'new': '仅新增模式 - 仅计算从未计算过hash值的文件',
            'force': '强制更新模式 - 对所有文件重新计算哈希值'
        }
        
        print("\n" + "=" * 80)
        print("哈希值计算")
        print("=" * 80)
        print(f"模式: {mode_desc.get(mode, mode)}")
        
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
        total_size = sum(file[1] for file in files)
        
        # 获取重复文件组信息
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM duplicate_groups')
        duplicate_groups = cursor.fetchone()[0]
        conn.close()
        
        print(f"重复文件组数量: {duplicate_groups}")
        print(f"待处理文件数量: {total_files} 个")
        print(f"待处理文件总大小: {self.format_size(total_size)}")
        print("=" * 80)
        
        if total_files == 0:
            print("\n没有需要处理的文件")
            return
        
        # 批量计算哈希值
        batch_size = 100
        for i in range(0, len(files), batch_size):
            batch = files[i:i+batch_size]
            self.process_batch(batch, mode, total_files, total_size)
        
        elapsed = time.time() - self.start_time
        
        # 显示完成信息
        print("\n" + "=" * 80)
        print("哈希计算完成！")
        print("=" * 80)
        print(f"总处理文件数: {self.total_processed} 个")
        print(f"总处理大小: {self.format_size(self.total_size_processed)}")
        print(f"计算哈希文件数: {self.total_calculated} 个")
        print(f"计算哈希大小: {self.format_size(self.total_size_calculated)}")
        print(f"跳过文件数: {self.total_skipped} 个")
        print(f"耗时: {elapsed:.2f} 秒")
        
        if elapsed > 0:
            speed_files = self.total_processed / elapsed
            speed_size = self.total_size_processed / elapsed
            print(f"平均速度: {speed_files:.1f} 文件/秒 ({self.format_size(speed_size)}/秒)")
        print("=" * 80)
    
    def format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
    
    def process_batch(self, batch, mode, total_files, total_size):
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
        for file_path, file_size, _ in batch:
            # 显示即将处理的文件（不换行）
            print(f"正在处理: {self.format_size(file_size):>10s}  {file_path} ... ", end='', flush=True)
            
            # 计算哈希值
            result = self.calculate_file_hash(file_path)
            if result:
                results.append(result)
                self.total_processed += 1
                self.total_size_processed += file_size
                
                # 显示完成并换行
                print("完成")
                
                # 每10个文件或每批结束时显示进度
                if self.total_processed % 10 == 0 or self.total_processed == total_files:
                    current_time = time.time()
                    elapsed = current_time - self.start_time
                    speed_files = self.total_processed / elapsed if elapsed > 0 else 0
                    speed_size = self.total_size_processed / elapsed if elapsed > 0 else 0
                    progress_size = (self.total_size_processed / total_size * 100) if total_size > 0 else 0
                    
                    # 计算剩余时间
                    remaining_size = total_size - self.total_size_processed
                    remaining_time = remaining_size / speed_size if speed_size > 0 else 0
                    
                    # 格式化剩余时间
                    if remaining_time < 60:
                        time_str = f"{remaining_time:.0f} 秒"
                    elif remaining_time < 3600:
                        time_str = f"{remaining_time/60:.1f} 分钟"
                    else:
                        time_str = f"{remaining_time/3600:.1f} 小时"
                    
                    print(f"\n进度: {self.format_size(self.total_size_processed)}/{self.format_size(total_size)} ({progress_size:.1f}%) - 剩余时间: {time_str} - 速度: {self.format_size(speed_size)}/秒 ({speed_files:.1f} 文件/秒)\n")
            else:
                print("失败")
        
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
                self.total_size_calculated += actual_size
        
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