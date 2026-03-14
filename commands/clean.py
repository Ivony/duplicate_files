import typer
import sqlite3
import os
from datetime import datetime
import hashlib
import time
import mmap

# 方案一：尝试导入 xxHash，如果失败则回退到 MD5
try:
    import xxhash
    HASH_ALGORITHM = 'xxhash'
    def get_hasher():
        return xxhash.xxh64()
    def get_hash_hexdigest(hasher):
        return hasher.hexdigest()
except ImportError:
    HASH_ALGORITHM = 'md5'
    def get_hasher():
        return hashlib.md5()
    def get_hash_hexdigest(hasher):
        return hasher.hexdigest()

class HashCalculator:
    """
    哈希值计算器（性能优化版）
    
    优化方案：
    1. 使用 xxHash 替代 MD5（速度提升 5-10 倍）
    2. 动态调整缓冲区大小
    3. 大文件使用内存映射（mmap）
    4. 预读取优化
    
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
        self.total_size_for_speed = 0
        self.start_time = 0
        self.quiet = False
    
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
    
    def _get_buffer_size(self, file_size):
        """方案二：根据文件大小动态调整缓冲区大小"""
        if file_size < 1024 * 1024:  # < 1MB
            return 64 * 1024  # 64KB
        elif file_size < 100 * 1024 * 1024:  # < 100MB
            return 1024 * 1024  # 1MB
        else:  # >= 100MB
            return 4 * 1024 * 1024  # 4MB
    
    def _calculate_hash_mmap(self, file_path, file_size):
        """方案五：使用内存映射计算大文件的哈希值"""
        hasher = get_hasher()
        with open(file_path, 'rb') as f:
            # 方案六：预读取优化
            try:
                os.posix_fadvise(f.fileno(), 0, file_size, os.POSIX_FADV_SEQUENTIAL)
            except (AttributeError, OSError):
                pass
            
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                # 分块处理，避免一次性处理过大的内存区域
                chunk_size = self._get_buffer_size(file_size)
                offset = 0
                while offset < file_size:
                    chunk = mm[offset:offset + chunk_size]
                    hasher.update(chunk)
                    offset += chunk_size
        
        return get_hash_hexdigest(hasher)
    
    def _calculate_hash_buffered(self, file_path, file_size):
        """使用缓冲区读取计算哈希值"""
        buffer_size = self._get_buffer_size(file_size)
        hasher = get_hasher()
        
        with open(file_path, 'rb') as f:
            # 方案六：预读取优化
            try:
                os.posix_fadvise(f.fileno(), 0, file_size, os.POSIX_FADV_SEQUENTIAL)
            except (AttributeError, OSError):
                pass
            
            while chunk := f.read(buffer_size):
                hasher.update(chunk)
        
        return get_hash_hexdigest(hasher)
    
    def calculate_file_hash(self, file_path):
        """
        计算单个文件的哈希值（优化版）
        
        优化方案：
        1. 使用 xxHash 替代 MD5
        2. 根据文件大小动态调整缓冲区
        3. 大文件使用内存映射
        4. 预读取优化
        
        注意：此方法是顺序执行的，不要尝试使用多线程或多进程来并行计算多个文件的哈希值。
        哈希计算是磁盘IO密集型操作，并行计算会导致磁盘IO竞争，反而降低性能。
        """
        try:
            file_info = self.get_file_info(file_path)
            if file_info is None:
                return None
            
            file_size = file_info['size']
            
            # 方案五：大文件使用内存映射（>100MB）
            # 注意：Windows 上 mmap 对小文件可能反而更慢
            if file_size > 100 * 1024 * 1024 and hasattr(mmap, 'ACCESS_READ'):
                try:
                    hash_value = self._calculate_hash_mmap(file_path, file_size)
                except Exception:
                    # mmap 失败时回退到缓冲区读取
                    hash_value = self._calculate_hash_buffered(file_path, file_size)
            else:
                hash_value = self._calculate_hash_buffered(file_path, file_size)
            
            return {
                'filepath': file_path,
                'size': file_size,
                'hash': hash_value,
                'modified': file_info['modified'],
                'created_at': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"计算哈希失败 {file_path}: {e}")
            return None
    
    def calculate_hash(self, mode='default', group_ids=None, filters=None, quiet=False):
        """计算哈希值
        
        Args:
            mode: 计算模式
                'default' - 默认模式：检查并更新
                'new' - 仅新增模式：仅计算从未计算过hash值的文件
                'force' - 强制更新模式：对duplicate_files表中所有文件重新计算哈希值
            group_ids: 指定的组ID列表，如果为None则根据filters选择组或选择所有组
            filters: 过滤器字典，如 {'extension': '.mp4', 'size': '>1000000', 'unconfirmed': True}
            quiet: 是否减少输出信息
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
        self.quiet = quiet
        
        # 显示模式说明
        mode_desc = {
            'default': '默认模式 - 检查并更新变化的文件',
            'new': '仅新增模式 - 仅计算从未计算过hash值的文件',
            'force': '强制更新模式 - 对所有文件重新计算哈希值',
            'verify': '验证模式 - 验证组的哈希值是否与所有文件一致'
        }
        
        if not self.quiet:
            print("\n" + "=" * 80)
            print("哈希值计算")
            print("=" * 80)
            print(f"模式: {mode_desc.get(mode, mode)}")
            print(f"哈希算法: {HASH_ALGORITHM.upper()}")
        
        # 获取要处理的重复文件组
        if group_ids:
            # 指定了组ID，只处理这些组
            placeholders = ','.join(['?'] * len(group_ids))
            cursor.execute(f'''
                SELECT dg.ID, dg.Extension, dg.Size, COUNT(df.Filepath) as file_count
                FROM duplicate_groups dg
                INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
                WHERE dg.ID IN ({placeholders})
                GROUP BY dg.ID
                ORDER BY dg.Size DESC
            ''', group_ids)
            if not self.quiet:
                print(f"指定组ID: {', '.join(map(str, group_ids))}")
        elif filters:
            # 根据过滤器选择组
            where_conditions = []
            params = []
            
            if 'extension' in filters:
                where_conditions.append('dg.Extension = ?')
                params.append(filters['extension'])
            
            if 'size' in filters:
                size_filter = filters['size']
                if size_filter.startswith('>') or size_filter.startswith('<'):
                    operator = size_filter[0]
                    size_value = int(size_filter[1:])
                    where_conditions.append(f'dg.Size {operator} ?')
                    params.append(size_value)
                else:
                    where_conditions.append('dg.Size = ?')
                    params.append(int(size_filter))
            
            if 'unconfirmed' in filters and filters['unconfirmed']:
                where_conditions.append('(dg.Hash IS NULL OR dg.Hash = "")')
            
            if where_conditions:
                where_clause = ' AND '.join(where_conditions)
                cursor.execute(f'''
                    SELECT dg.ID, dg.Extension, dg.Size, COUNT(df.Filepath) as file_count
                    FROM duplicate_groups dg
                    INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
                    WHERE {where_clause}
                    GROUP BY dg.ID
                    ORDER BY dg.Size DESC
                ''', params)
                
                filter_desc = []
                if 'extension' in filters:
                    filter_desc.append(f"扩展名: {filters['extension']}")
                if 'size' in filters:
                    filter_desc.append(f"大小: {filters['size']}")
                if 'unconfirmed' in filters and filters['unconfirmed']:
                    filter_desc.append("未确认哈希值")
                if not self.quiet:
                    print(f"过滤条件: {', '.join(filter_desc)}")
            else:
                # 没有过滤器，获取所有组
                cursor.execute('''
                    SELECT dg.ID, dg.Extension, dg.Size, COUNT(df.Filepath) as file_count
                    FROM duplicate_groups dg
                    INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
                    GROUP BY dg.ID
                    ORDER BY dg.Size DESC
                ''')
        else:
            # 没有指定组ID和过滤器，获取所有组
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
        
        if not self.quiet:
            print(f"重复文件组数量: {total_groups}")
            print(f"待处理文件数量: {total_files} 个")
            print(f"待处理文件总大小: {self.format_size(total_size)}")
            print("=" * 80)
        
        if total_groups == 0:
            if not self.quiet:
                print("\n没有需要处理的文件")
            return
        
        # 按组处理
        for group_idx, (group_id, extension, size, file_count) in enumerate(groups, 1):
            if not self.quiet:
                print(f"\n{'=' * 80}")
                print(f"处理第 {group_idx}/{total_groups} 组 (Group_ID: {group_id})")
                print(f"扩展名: {extension}, 文件大小: {self.format_size(size)}, 文件数量: {file_count}")
                print(f"{'=' * 80}")
            
            # 处理这个组
            self.process_group(group_id, mode, total_files, total_size)
        
        elapsed = time.time() - self.start_time
        
        # 显示完成信息
        if not self.quiet:
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
            if not self.quiet:
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
            if not self.quiet:
                print(f"正在处理: {self.format_size(file_size):>10s}  {file_path} ... ", end='', flush=True)
            
            # 检查是否需要跳过计算
            should_skip = False
            
            if mode == 'new':
                # 仅新增模式：如果file_hash表里有该文件的记录，就跳过
                if file_path in existing_hashes:
                    should_skip = True
                    if not self.quiet:
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
                        if not self.quiet:
                            print("跳过（文件未变化）")
                        self.total_skipped += 1
                        self.total_processed += 1
                        self.total_size_processed += file_size
            
            elif mode == 'verify':
                # 验证模式：只验证，不计算哈希值
                should_skip = True
                if not self.quiet:
                    print("验证中...")
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
                    if not self.quiet:
                        print("完成")
                else:
                    if not self.quiet:
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
        
        if not self.quiet:
            print(f"\n进度: {self.format_size(self.total_size_processed)}/{self.format_size(total_size)} ({progress_size:.1f}%) - 剩余时间: {time_str} - 速度: {self.format_size(speed_size)}/秒")
        
        # 分析该组的哈希值结果并更新数据库
        if not self.quiet:
            print(f"\n分析该组的哈希值结果...")
        
        # 获取该组的信息
        cursor.execute('SELECT Hash FROM duplicate_groups WHERE ID = ?', (group_id,))
        group_hash = cursor.fetchone()
        group_hash_val = group_hash[0] if group_hash else None
        
        # 获取该组所有文件的哈希值和文件信息
        cursor.execute('''
            SELECT fh.Hash, fh.Size, fh.Modified, df.Filepath, f.Size as current_size, f.Modified as current_modified
            FROM duplicate_files df
            INNER JOIN file_hash fh ON df.Filepath = fh.Filepath
            INNER JOIN files f ON df.Filepath = f.Filename
            WHERE df.Group_ID = ?
        ''', (group_id,))
        
        hash_results = cursor.fetchall()
        
        if hash_results:
            # 验证模式的处理
            if mode == 'verify':
                is_valid = True
                validation_issues = []
                
                # 检查组哈希值是否存在
                if not group_hash_val:
                    validation_issues.append("组哈希值未设置")
                    is_valid = False
                
                # 检查每个文件
                for file_hash, db_size, db_modified, filepath, current_size, current_modified in hash_results:
                    # 检查文件哈希值是否与组哈希值一致
                    if group_hash_val and file_hash != group_hash_val:
                        validation_issues.append(f"文件哈希值不匹配: {filepath}")
                        is_valid = False
                    
                    # 确保修改时间是数值类型
                    if isinstance(db_modified, str):
                        try:
                            dt = datetime.fromisoformat(db_modified)
                            db_modified = dt.timestamp()
                        except:
                            db_modified = float(db_modified)
                    
                    if isinstance(current_modified, str):
                        try:
                            dt = datetime.fromisoformat(current_modified)
                            current_modified = dt.timestamp()
                        except:
                            current_modified = float(current_modified)
                    
                    # 检查文件大小是否变化
                    if current_size != db_size:
                        validation_issues.append(f"文件大小变化: {filepath}")
                        is_valid = False
                    
                    # 检查文件修改时间是否变化
                    if abs(current_modified - db_modified) >= 0.001:
                        validation_issues.append(f"文件修改时间变化: {filepath}")
                        is_valid = False
                
                if is_valid:
                    if not self.quiet:
                        print(f"✓ 该组验证通过，哈希值一致且文件未变化")
                        print(f"  组哈希值: {group_hash_val}")
                else:
                    # 验证失败，清除组哈希值
                    cursor.execute('UPDATE duplicate_groups SET Hash = NULL WHERE ID = ?', (group_id,))
                    conn.commit()
                    if not self.quiet:
                        print(f"✗ 该组验证失败，已清除哈希值")
                        for issue in validation_issues:
                            print(f"  - {issue}")
            else:
                # 按哈希值分组
                hash_groups = {}
                for row in hash_results:
                    hash_val = row[0]
                    filepath = row[3]
                    if hash_val not in hash_groups:
                        hash_groups[hash_val] = []
                    hash_groups[hash_val].append(filepath)
                
                # 处理结果
                if len(hash_groups) == 1:
                    # 所有文件哈希值相同，更新组的Hash字段
                    hash_val = list(hash_groups.keys())[0]
                    cursor.execute('''
                        UPDATE duplicate_groups SET Hash = ? WHERE ID = ?
                    ''', (hash_val, group_id))
                    conn.commit()
                    if not self.quiet:
                        print(f"✓ 该组所有文件哈希值相同，确认为重复文件组")
                        print(f"  哈希值: {hash_val}")
                        print(f"  文件数量: {len(hash_groups[hash_val])}")
                elif len(hash_groups) == len(hash_results):
                    # 所有文件哈希值都不同，删除该组
                    cursor.execute('DELETE FROM duplicate_files WHERE Group_ID = ?', (group_id,))
                    cursor.execute('DELETE FROM duplicate_groups WHERE ID = ?', (group_id,))
                    conn.commit()
                    if not self.quiet:
                        print(f"✗ 该组所有文件哈希值都不同，不是重复文件组")
                        print(f"  已删除该组（{len(hash_results)} 个文件）")
                else:
                    # 部分文件哈希值相同，拆分为子组
                    if not self.quiet:
                        print(f"⚡ 该组拆分为 {len(hash_groups)} 个子组：")
                    
                    # 获取原组的信息
                    cursor.execute('SELECT Size, Extension FROM duplicate_groups WHERE ID = ?', (group_id,))
                    row = cursor.fetchone()
                    size, extension = row if row else (0, '')
                    
                    # 先删除duplicate_files中的关联记录
                    cursor.execute('DELETE FROM duplicate_files WHERE Group_ID = ?', (group_id,))
                    # 再删除原组
                    cursor.execute('DELETE FROM duplicate_groups WHERE ID = ?', (group_id,))
                    
                    # 为每个子组创建新的组
                    for idx, (hash_val, filepaths) in enumerate(hash_groups.items(), 1):
                        if len(filepaths) > 1:
                            # 只有多个文件才创建组
                            cursor.execute('''
                                INSERT INTO duplicate_groups (Size, Extension, Hash)
                                VALUES (?, ?, ?)
                            ''', (size, extension, hash_val))
                            new_group_id = cursor.lastrowid
                            
                            # 添加文件关联
                            for filepath in filepaths:
                                cursor.execute('''
                                    INSERT INTO duplicate_files (Group_ID, Filepath)
                                    VALUES (?, ?)
                                ''', (new_group_id, filepath))
                            
                            if not self.quiet:
                                print(f"  子组 {idx}: {len(filepaths)} 个文件 (哈希值: {hash_val[:16]}...)")
                        else:
                            if not self.quiet:
                                print(f"  子组 {idx}: 1 个文件 (独立文件，不创建组)")
                    
                    conn.commit()
        else:
            if not self.quiet:
                print("该组没有计算哈希值的文件")
        
        conn.close()
    
    def format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

class FileCleaner:
    def __init__(self, db_path='file_index.db'):
        self.db_path = db_path
        self.dryrun = False
        self.script_mode = False
        self.script_path = None
        self.script_file = None
        self.script_type = None  # 'cmd', 'bash', 'powershell'
        self.auto_confirm = False
        self.sort_strategy = 'newest'  # 默认策略
        self.group_ids = None
        self.min_size = None
        self.max_size = None
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path, timeout=60.0, isolation_level='IMMEDIATE')
    
    def delete_file(self, filepath):
        """删除文件，支持模拟模式和脚本模式"""
        if self.dryrun:
            print(f"    [模拟] 删除文件: {filepath}")
            return True
        
        if self.script_mode:
            # 脚本模式：将删除命令写入脚本文件
            self._write_delete_command(filepath)
            return True
        
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"    已删除: {filepath}")
                return True
            else:
                print(f"    警告: 文件不存在 {filepath}")
                return False
        except Exception as e:
            print(f"    错误: 删除文件失败 {filepath}: {e}")
            return False
    
    def init_script_file(self, script_path=None):
        """初始化脚本文件"""
        # 确定脚本路径
        if script_path:
            self.script_path = script_path
        else:
            # 默认路径
            self.script_path = self._get_default_script_path()
        
        # 检查文件是否存在
        if os.path.exists(self.script_path):
            print(f"\n脚本文件已存在: {self.script_path}")
            choice = input("是否覆盖? (y/n): ").strip().lower()
            if choice != 'y':
                print("取消脚本生成")
                return False
        
        # 确定脚本类型
        self.script_type = self._detect_script_type(self.script_path)
        
        # 创建脚本文件并写入头部
        self.script_file = open(self.script_path, 'w', encoding='utf-8')
        self._write_script_header()
        
        print(f"脚本文件: {self.script_path}")
        print(f"脚本类型: {self.script_type}")
        return True
    
    def _get_default_script_path(self):
        """获取默认脚本路径"""
        # 根据操作系统选择默认脚本类型
        if os.name == 'nt':  # Windows
            return 'clean_duplicate.cmd'
        else:
            return 'clean_duplicate.sh'
    
    def _detect_script_type(self, script_path):
        """根据文件扩展名检测脚本类型"""
        ext = os.path.splitext(script_path)[1].lower()
        if ext in ['.cmd', '.bat']:
            return 'cmd'
        elif ext in ['.sh', '.bash']:
            return 'bash'
        elif ext in ['.ps1']:
            return 'powershell'
        else:
            # 根据操作系统默认
            return 'cmd' if os.name == 'nt' else 'bash'
    
    def _write_script_header(self):
        """写入脚本头部"""
        if self.script_type == 'cmd':
            self.script_file.write('@echo off\n')
            self.script_file.write('REM 自动生成的重复文件清理脚本\n')
            self.script_file.write(f'REM 生成时间: {datetime.now().isoformat()}\n')
            self.script_file.write('REM 请仔细审查后再执行此脚本\n\n')
        elif self.script_type == 'bash':
            self.script_file.write('#!/bin/bash\n')
            self.script_file.write('# 自动生成的重复文件清理脚本\n')
            self.script_file.write(f'# 生成时间: {datetime.now().isoformat()}\n')
            self.script_file.write('# 请仔细审查后再执行此脚本\n\n')
        elif self.script_type == 'powershell':
            self.script_file.write('# 自动生成的重复文件清理脚本\n')
            self.script_file.write(f'# 生成时间: {datetime.now().isoformat()}\n')
            self.script_file.write('# 请仔细审查后再执行此脚本\n\n')
    
    def _write_delete_command(self, filepath):
        """写入删除命令到脚本"""
        # 转义特殊字符
        escaped_path = filepath.replace('"', '\\"')
        
        if self.script_type == 'cmd':
            # CMD: 使用 if exist 检查文件是否存在
            self.script_file.write(f'if exist "{escaped_path}" (\n')
            self.script_file.write(f'    echo 删除: {escaped_path}\n')
            self.script_file.write(f'    del /f "{escaped_path}"\n')
            self.script_file.write(f') else (\n')
            self.script_file.write(f'    echo 文件不存在: {escaped_path}\n')
            self.script_file.write(f')\n\n')
        elif self.script_type == 'bash':
            # Bash: 使用 [ -f ] 检查文件是否存在
            escaped_path = filepath.replace('"', '\\"').replace('$', '\\$')
            self.script_file.write(f'if [ -f "{escaped_path}" ]; then\n')
            self.script_file.write(f'    echo "删除: {escaped_path}"\n')
            self.script_file.write(f'    rm -f "{escaped_path}"\n')
            self.script_file.write(f'else\n')
            self.script_file.write(f'    echo "文件不存在: {escaped_path}"\n')
            self.script_file.write(f'fi\n\n')
        elif self.script_type == 'powershell':
            # PowerShell: 使用 Test-Path 检查文件是否存在
            self.script_file.write(f'if (Test-Path "{escaped_path}") {{\n')
            self.script_file.write(f'    Write-Host "删除: {escaped_path}"\n')
            self.script_file.write(f'    Remove-Item -Force "{escaped_path}"\n')
            self.script_file.write(f'}} else {{\n')
            self.script_file.write(f'    Write-Host "文件不存在: {escaped_path}"\n')
            self.script_file.write(f'}}\n\n')
    
    def close_script_file(self):
        """关闭脚本文件"""
        if self.script_file:
            self.script_file.close()
            self.script_file = None
            print(f"\n脚本已生成: {self.script_path}")
            print(f"请仔细审查脚本内容后再执行")
    
    def verify_group(self, group_id):
        """验证文件组的哈希值一致性"""
        print(f"  正在校验组 {group_id}...")
        calculator = HashCalculator(self.db_path)
        # 调用哈希计算器的验证模式，减少输出
        calculator.calculate_hash('verify', [group_id], quiet=True)
        
        # 检查验证后组是否还有哈希值
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT Hash FROM duplicate_groups WHERE ID = ?', (group_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result and result[0] is not None
    
    def get_sort_key(self, strategy):
        """获取排序键函数"""
        def get_file_info(filepath):
            """获取文件信息"""
            filename = os.path.basename(filepath)
            dir_depth = len(filepath.split(os.sep))
            return {
                'filepath': filepath,
                'filename': filename,
                'dir_depth': dir_depth
            }
        
        sort_functions = {
            'newest': lambda f: (f['modified'], f['filename'], f['filepath']),
            'oldest': lambda f: (f['modified'], f['filename'], f['filepath']),
            'longest_name': lambda f: (len(f['filename']), f['filename'], f['filepath']),
            'shortest_name': lambda f: (len(f['filename']), f['filename'], f['filepath']),
            'longest_path': lambda f: (len(f['filepath']), f['filename'], f['filepath']),
            'shortest_path': lambda f: (len(f['filepath']), f['filename'], f['filepath']),
            'name_asc': lambda f: (f['filename'], f['filepath']),
            'name_desc': lambda f: (f['filename'], f['filepath']),
            'path_asc': lambda f: (f['filepath'], f['filename']),
            'path_desc': lambda f: (f['filepath'], f['filename']),
            'deepest': lambda f: (len(f['filepath'].split(os.sep)), f['filename'], f['filepath']),
            'shallowest': lambda f: (len(f['filepath'].split(os.sep)), f['filename'], f['filepath'])
        }
        
        return sort_functions.get(strategy, sort_functions['newest'])
    
    def get_sort_reverse(self, strategy):
        """获取排序方向"""
        reverse_map = {
            'newest': True,
            'oldest': False,
            'longest_name': True,
            'shortest_name': False,
            'longest_path': True,
            'shortest_path': False,
            'name_asc': False,
            'name_desc': True,
            'path_asc': False,
            'path_desc': True,
            'deepest': True,
            'shallowest': False
        }
        
        return reverse_map.get(strategy, True)
    
    def clean(self):
        """执行清理操作"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        print("开始清理操作...")
        print(f"排序策略: {self.get_strategy_name()}")
        if self.dryrun:
            print("模式: 模拟执行 (不实际删除文件)")
        elif self.script_mode:
            print("模式: 脚本生成 (生成删除脚本)")
            # 初始化脚本文件
            if not self.init_script_file(self.script_path):
                conn.close()
                return
        
        # 构建查询语句
        query = '''
        SELECT dg.ID, dg.Size, dg.Extension, dg.Hash, COUNT(*) as file_count
        FROM duplicate_groups dg
        INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
        WHERE dg.Hash IS NOT NULL
        '''
        
        params = []
        
        if self.group_ids:
            placeholders = ','.join(['?'] * len(self.group_ids))
            query += f" AND dg.ID IN ({placeholders})"
            params.extend(self.group_ids)
        
        if self.min_size:
            query += " AND dg.Size >= ?"
            params.append(self.min_size)
        
        if self.max_size:
            query += " AND dg.Size <= ?"
            params.append(self.max_size)
        
        query += '''
        GROUP BY dg.ID
        HAVING COUNT(*) > 1
        ORDER BY (COUNT(*) - 1) * dg.Size DESC
        '''
        
        cursor.execute(query, params)
        groups = cursor.fetchall()
        
        if not groups:
            print("没有找到符合条件的重复文件组")
            conn.close()
            return
        
        total_files = 0
        total_size = 0
        failed_files = []
        
        print(f"\n找到 {len(groups)} 个符合条件的重复文件组")
        print("=" * 80)
        
        for group_id, size, extension, hash_val, file_count in groups:
            # 验证文件组
            if not self.verify_group(group_id):
                print(f"  跳过文件组 {group_id}: 验证失败，哈希值不一致")
                continue
            
            # 获取该组的文件列表
            cursor.execute('''
            SELECT f.Filename, f.Modified
            FROM duplicate_files df
            INNER JOIN files f ON df.Filepath = f.Filename
            WHERE df.Group_ID = ?
            ''', (group_id,))
            
            files = cursor.fetchall()
            
            # 准备文件信息
            file_infos = []
            for filepath, modified in files:
                # 确保修改时间是数值类型
                if isinstance(modified, str):
                    try:
                        dt = datetime.fromisoformat(modified)
                        modified = dt.timestamp()
                    except:
                        modified = float(modified)
                
                file_infos.append({
                    'filepath': filepath,
                    'filename': os.path.basename(filepath),
                    'modified': modified
                })
            
            # 应用排序策略
            sort_key = self.get_sort_key(self.sort_strategy)
            reverse = self.get_sort_reverse(self.sort_strategy)
            file_infos.sort(key=sort_key, reverse=reverse)
            
            # 显示文件组信息
            print(f"\n文件组 {group_id}:")
            print(f"  哈希值: {hash_val}")
            print(f"  文件大小: {size:,} 字节")
            print(f"  文件扩展名: {extension}")
            print(f"  文件数量: {file_count} 个")
            print(f"  排序策略: {self.get_strategy_name()}")
            print(f"  可释放空间: {(file_count - 1) * size:,} 字节")
            print("  文件列表:")
            
            for i, file_info in enumerate(file_infos, 1):
                print(f"    {i}. {file_info['filepath']}")
                print(f"       修改时间: {datetime.fromtimestamp(file_info['modified'])}")
            
            # 询问用户确认
            keep_index = 0
            if not self.auto_confirm:
                while True:
                    choice = input("  请选择要保留的文件序号 (默认 1, 输入 q 退出): ").strip().lower()
                    if not choice:
                        break
                    if choice == 'q':
                        print("  退出清理模式")
                        conn.close()
                        return
                    try:
                        keep_index = int(choice) - 1
                        if 0 <= keep_index < len(file_infos):
                            break
                        else:
                            print("  无效的选择，请重新输入")
                    except ValueError:
                        print("  无效的输入，请输入数字或 q 退出")
            
            # 确定要保留和删除的文件
            keep_file = file_infos[keep_index]
            delete_files = [f for i, f in enumerate(file_infos) if i != keep_index]
            
            print(f"  保留文件: {keep_file['filepath']}")
            print(f"  删除文件数: {len(delete_files)} 个")
            
            # 执行删除操作
            for file_info in delete_files:
                if self.delete_file(file_info['filepath']):
                    total_files += 1
                    total_size += size
                else:
                    failed_files.append(file_info['filepath'])
        
        conn.close()
        
        # 关闭脚本文件
        if self.script_mode:
            self.close_script_file()
        
        print("\n" + "=" * 80)
        print(f"清理完成！")
        print(f"总计:")
        print(f"  已删除文件数: {total_files:,} 个")
        print(f"  已释放空间: {total_size:,} 字节 ({total_size/1024/1024/1024:.2f} GB)")
        
        if failed_files:
            print(f"  删除失败文件数: {len(failed_files)} 个")
        
        if self.dryrun:
            print("\n注意：这是模拟操作，没有实际删除任何文件")
        elif self.script_mode:
            print(f"\n注意：已生成删除脚本，请审查后再执行: {self.script_path}")
        
        print("=" * 80)
    
    def get_strategy_name(self):
        """获取排序策略的中文名称"""
        strategy_names = {
            'newest': '保留最新文件',
            'oldest': '保留最旧文件',
            'longest_name': '保留文件名最长的文件',
            'shortest_name': '保留文件名最短的文件',
            'longest_path': '保留路径最长的文件',
            'shortest_path': '保留路径最短的文件',
            'name_asc': '按文件名升序保留第一个',
            'name_desc': '按文件名降序保留第一个',
            'path_asc': '按路径升序保留第一个',
            'path_desc': '按路径降序保留第一个',
            'deepest': '保留目录最深的文件',
            'shallowest': '保留目录最浅的文件'
        }
        
        return strategy_names.get(self.sort_strategy, '保留最新文件')

app = typer.Typer()

# 支持的排序策略列表
SORT_STRATEGIES = [
    'newest', 'oldest',
    'longest-name', 'shortest-name',
    'longest-path', 'shortest-path',
    'name-asc', 'name-desc',
    'path-asc', 'path-desc',
    'deepest', 'shallowest'
]

def parse_size(size_str: str) -> int:
    """解析大小字符串，支持 K/M/G 后缀"""
    size_str = size_str.upper()
    if size_str.endswith('K'):
        return int(size_str[:-1]) * 1024
    elif size_str.endswith('M'):
        return int(size_str[:-1]) * 1024 * 1024
    elif size_str.endswith('G'):
        return int(size_str[:-1]) * 1024 * 1024 * 1024
    else:
        return int(size_str)

def setup_cleaner(
    cleaner: FileCleaner,
    strategy: str,
    group: str,
    min_size: str,
    max_size: str
) -> bool:
    """配置清理器参数，返回是否成功"""
    # 设置排序策略
    if strategy:
        internal_strategy = strategy.replace('-', '_')
        cleaner.sort_strategy = internal_strategy
    
    # 解析组ID
    if group:
        try:
            cleaner.group_ids = [int(gid) for gid in group.split(',')]
        except ValueError:
            typer.echo(f"错误: 无效的组ID: {group}")
            return False
    
    # 解析大小参数
    if min_size:
        try:
            cleaner.min_size = parse_size(min_size)
        except ValueError:
            typer.echo(f"错误: 无效的大小值: {min_size}")
            return False
    
    if max_size:
        try:
            cleaner.max_size = parse_size(max_size)
        except ValueError:
            typer.echo(f"错误: 无效的大小值: {max_size}")
            return False
    
    return True

@app.command(name="run")
def run(
    dryrun: bool = False,
    yes: bool = False,
    group: str = None,
    min_size: str = None,
    max_size: str = None,
    strategy: str = typer.Option('newest', help=f"排序策略: {', '.join(SORT_STRATEGIES)}")
):
    """执行清理操作"""
    # 验证策略
    if strategy not in SORT_STRATEGIES:
        typer.echo(f"错误: 无效的排序策略 '{strategy}'")
        typer.echo(f"支持的策略: {', '.join(SORT_STRATEGIES)}")
        return
    
    cleaner = FileCleaner('file_index.db')
    cleaner.dryrun = dryrun
    cleaner.auto_confirm = yes
    
    if not setup_cleaner(cleaner, strategy, group, min_size, max_size):
        return
    
    # 执行清理操作
    cleaner.clean()

@app.command(name="script")
def script(
    output: str = typer.Option(..., "--output", "-o", help="输出脚本文件路径"),
    strategy: str = typer.Option('newest', help=f"排序策略: {', '.join(SORT_STRATEGIES)}"),
    group: str = None,
    min_size: str = None,
    max_size: str = None
):
    """生成清理脚本"""
    # 验证策略
    if strategy not in SORT_STRATEGIES:
        typer.echo(f"错误: 无效的排序策略 '{strategy}'")
        typer.echo(f"支持的策略: {', '.join(SORT_STRATEGIES)}")
        return
    
    cleaner = FileCleaner('file_index.db')
    cleaner.script_mode = True
    cleaner.script_path = output
    
    if not setup_cleaner(cleaner, strategy, group, min_size, max_size):
        return
    
    # 执行清理操作（生成脚本）
    cleaner.clean()
