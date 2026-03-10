import sqlite3
import os
import hashlib
import time
from datetime import datetime

class HashCalculator:
    """
    哈希值计算器
    
    重要说明：
    本类中的所有哈希计算操作都是顺序执行的，绝对不要使用并行计算（多线程或多进程）。
    
    原因：
    1. 哈希计算是磁盘IO密集型操作，不是CPU密集型操作
    2. 并行计算会导致多个线程/进程同时读取磁盘，造成磁盘IO竞争
    3. 磁盘IO竞争会导致磁头频繁寻道，大幅降低读取性能
    4. 对于机械硬盘（HDD），并行读取会导致性能下降50%甚至更多
    5. 即使是SSD，并行读取也不会带来明显的性能提升，反而可能降低性能
    
    因此，请保持顺序计算，一个文件一个文件地处理，这样才能获得最佳性能。
    """
    def __init__(self, db_path='file_index.db'):
        self.db_path = db_path
        self.total_processed = 0
        self.total_calculated = 0
        self.total_skipped = 0
        self.total_size_processed = 0
        self.total_size_calculated = 0
        self.total_size_for_speed = 0  # 用于速度计算的文件大小（不包括跳过的文件）
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
        """
        计算单个文件的哈希值
        
        注意：此方法是顺序执行的，不要尝试使用多线程或多进程来并行计算多个文件的哈希值。
        哈希计算是磁盘IO密集型操作，并行计算会导致磁盘IO竞争，反而降低性能。
        """
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
        self.total_size_for_speed = 0  # 用于速度计算的文件大小（不包括跳过的文件）
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
        
        # 获取所有重复文件组
        cursor.execute('''
            SELECT dg.ID, dg.Extension, dg.Size, COUNT(df.Filepath) as file_count
            FROM duplicate_groups dg
            INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
            GROUP BY dg.ID
            ORDER BY dg.Size DESC
        ''')
        groups = cursor.fetchall()
        conn.close()
        
        total_groups = len(groups)
        total_files = sum(group[3] for group in groups)
        total_size = sum(group[2] * group[3] for group in groups)
        
        print(f"重复文件组数量: {total_groups}")
        print(f"待处理文件数量: {total_files} 个")
        print(f"待处理文件总大小: {self.format_size(total_size)}")
        print("=" * 80)
        
        if total_groups == 0:
            print("\n没有需要处理的文件")
            return
        
        # 按组处理
        for group_idx, (group_id, extension, size, file_count) in enumerate(groups, 1):
            print(f"\n{'=' * 80}")
            print(f"处理第 {group_idx}/{total_groups} 组 (Group_ID: {group_id})")
            print(f"扩展名: {extension}, 文件大小: {self.format_size(size)}, 文件数量: {file_count}")
            print(f"{'=' * 80}")
            
            # 处理这个组
            self.process_group(group_id, mode, total_files, total_size)
        
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
    
    def process_group(self, group_id, mode, total_files, total_size):
        """
        处理一个重复文件组
        
        注意：此方法是顺序处理组内的所有文件，不使用并行计算。
        原因是哈希计算是磁盘IO密集型操作，并行计算会导致性能下降。
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 获取该组的所有文件
        if mode == 'new':
            # 仅新增模式：只获取从未计算过哈希值的文件
            cursor.execute('''
                SELECT df.Filepath, f.Size, f.Modified
                FROM duplicate_files df
                INNER JOIN files f ON df.Filepath = f.Filename
                WHERE df.Group_ID = ? AND df.Filepath NOT IN (SELECT Filepath FROM file_hash)
            ''', (group_id,))
        else:
            # 默认模式和强制更新模式：获取所有文件
            cursor.execute('''
                SELECT df.Filepath, f.Size, f.Modified
                FROM duplicate_files df
                INNER JOIN files f ON df.Filepath = f.Filename
                WHERE df.Group_ID = ?
            ''', (group_id,))
        
        files = cursor.fetchall()
        
        if not files:
            conn.close()
            print("该组没有需要处理的文件")
            return
        
        # 获取已计算的哈希值
        file_paths = [file[0] for file in files]
        placeholders = ','.join(['?'] * len(file_paths))
        cursor.execute(f'SELECT Filepath, Size, Modified FROM file_hash WHERE Filepath IN ({placeholders})', file_paths)
        existing_hashes = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
        
        # 计算哈希值
        results = []
        for file_path, file_size, file_modified in files:
            # 显示即将处理的文件（不换行）
            print(f"正在处理: {self.format_size(file_size):>10s}  {file_path} ... ", end='', flush=True)
            
            # 检查是否需要跳过计算
            should_skip = False
            
            if mode == 'new':
                # 仅新增模式：如果file_hash表里有该文件的记录，就跳过
                if file_path in existing_hashes:
                    should_skip = True
                    print("跳过（已有哈希记录）")
                    self.total_skipped += 1
                    self.total_processed += 1
                    self.total_size_processed += file_size
                    # 注意：跳过的文件不计入速度计算
            
            elif mode == 'default':
                # 默认模式：如果file_hash表里有该文件的记录，并且文件大小和修改时间都匹配，才跳过
                if file_path in existing_hashes:
                    db_size, db_modified = existing_hashes[file_path]
                    
                    # 确保修改时间是数值类型
                    if isinstance(file_modified, str):
                        try:
                            dt = datetime.fromisoformat(file_modified)
                            file_modified = dt.timestamp()
                        except:
                            file_modified = float(file_modified)
                    
                    if isinstance(db_modified, str):
                        try:
                            dt = datetime.fromisoformat(db_modified)
                            db_modified = dt.timestamp()
                        except:
                            db_modified = float(db_modified)
                    
                    if file_size == db_size and abs(file_modified - db_modified) < 0.001:
                        should_skip = True
                        print("跳过（文件未变化）")
                        self.total_skipped += 1
                        self.total_processed += 1
                        self.total_size_processed += file_size
            
            # 如果不需要跳过，计算哈希值
            if not should_skip:
                result = self.calculate_file_hash(file_path)
                if result:
                    results.append(result)
                    self.total_processed += 1
                    self.total_size_processed += file_size
                    self.total_size_for_speed += file_size  # 计入速度计算
                    
                    # 显示完成并换行
                    print("完成")
                else:
                    print("失败")
                    continue
        
        # 更新数据库
        for result in results:
            file_path = result['filepath']
            actual_size = result['size']
            actual_modified = result['modified']
            hash_val = result['hash']
            created_at = result['created_at']
            
            cursor.execute('''
            INSERT OR REPLACE INTO file_hash (Filepath, Size, Hash, Modified, created_at)
            VALUES (?, ?, ?, ?, ?)
            ''', (file_path, actual_size, hash_val, actual_modified, created_at))
            self.total_calculated += 1
            self.total_size_calculated += actual_size
        
        conn.commit()
        
        # 显示该组处理完成后的进度
        current_time = time.time()
        elapsed = current_time - self.start_time
        speed_size = self.total_size_for_speed / elapsed if elapsed > 0 and self.total_size_for_speed > 0 else 0
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
        
        print(f"\n进度: {self.format_size(self.total_size_processed)}/{self.format_size(total_size)} ({progress_size:.1f}%) - 剩余时间: {time_str} - 速度: {self.format_size(speed_size)}/秒")
        
        # 分析该组的哈希值结果
        print(f"\n分析该组的哈希值结果...")
        
        # 获取该组所有文件的哈希值
        cursor.execute('''
            SELECT fh.Hash, df.Filepath
            FROM duplicate_files df
            INNER JOIN file_hash fh ON df.Filepath = fh.Filepath
            WHERE df.Group_ID = ?
        ''', (group_id,))
        
        hash_results = cursor.fetchall()
        conn.close()
        
        if hash_results:
            # 按哈希值分组
            hash_groups = {}
            for hash_val, filepath in hash_results:
                if hash_val not in hash_groups:
                    hash_groups[hash_val] = []
                hash_groups[hash_val].append(filepath)
            
            # 显示结果
            if len(hash_groups) == 1:
                hash_val = list(hash_groups.keys())[0]
                print(f"✓ 该组所有文件哈希值相同，确认为重复文件组")
                print(f"  哈希值: {hash_val}")
                print(f"  文件数量: {len(hash_groups[hash_val])}")
            elif len(hash_groups) == len(hash_results):
                print(f"✗ 该组所有文件哈希值都不同，不是重复文件组")
                print(f"  可以拆分为 {len(hash_groups)} 个独立的文件")
            else:
                print(f"⚡ 该组可以细分为 {len(hash_groups)} 个子组：")
                for idx, (hash_val, filepaths) in enumerate(hash_groups.items(), 1):
                    print(f"  子组 {idx}: {len(filepaths)} 个文件 (哈希值: {hash_val[:16]}...)")
        else:
            print("该组没有计算哈希值的文件")
    
    def format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

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