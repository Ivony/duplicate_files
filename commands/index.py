import typer
import os
import sqlite3
import time
import csv
import hashlib
import mmap
import re
from typing import Optional
from datetime import datetime
from commands.config import ConfigManager
from commands.db_config import get_db_path

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

class FileScanner:
    def __init__(self, db_path=None):
        self.db_path = db_path or get_db_path()
        self.total_scanned = 0
        self.total_indexed = 0
        self.start_time = 0
        
        # 优化方案一：缓存 ConfigManager 和预编译正则表达式
        self.config_manager = ConfigManager()
        self.excluded_patterns = []
        self._compile_exclude_patterns()
    
    def _compile_exclude_patterns(self):
        """预编译所有排除模式的正则表达式"""
        patterns = self.config_manager.get_excluded_patterns()
        self.excluded_patterns = [re.compile(pattern) for pattern in patterns]
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path, timeout=30.0, isolation_level='DEFERRED')
    
    def is_path_excluded(self, file_path):
        """检查路径是否被排除（使用缓存的预编译正则表达式）"""
        for pattern in self.excluded_patterns:
            if pattern.match(file_path):
                return True
        return False
    
    def _get_canonical_path(self, path):
        """获取规范化路径（用于数据库主键/去重）

        在 Windows 上使用 os.path.normcase() 转为小写
        在其他系统上保持原样（区分大小写）

        Raises:
            ValueError: 如果路径不是绝对路径
        """
        if not os.path.isabs(path):
            raise ValueError(f"路径必须是绝对路径: {path}")
        return os.path.normcase(path)

    def scan_file(self, file_path):
        """扫描单个文件（优化方案四：延迟 datetime 转换，直接存储时间戳）"""
        try:
            stat = os.stat(file_path)
            _, ext = os.path.splitext(file_path)
            return {
                'filename': self._get_canonical_path(file_path),
                'extension': ext.lower() if ext else '',
                'size': stat.st_size,
                'created': stat.st_ctime,  # 直接存储时间戳
                'modified': stat.st_mtime,  # 直接存储时间戳
                'accessed': stat.st_atime   # 直接存储时间戳
            }
        except Exception as e:
            print(f"扫描文件失败 {file_path}: {e}")
            return None
    
    def _flush_buffer(self, cursor, conn, buffer):
        """将缓冲区数据写入数据库"""
        if not buffer:
            return
        
        placeholders = ','.join(['(?, ?, ?, ?, ?, ?)'] * len(buffer))
        values = []
        for file_info in buffer:
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
    
    def scan_directory(self, path):
        """扫描指定路径下的所有文件（优化方案二：流式处理）"""
        # 确保路径是绝对路径
        path = os.path.abspath(path)

        conn = self.get_connection()
        cursor = conn.cursor()

        self.total_scanned = 0
        self.total_indexed = 0
        self.start_time = time.time()

        print(f"开始扫描路径: {path}")
        
        # 优化方案二：使用固定大小的缓冲区进行流式处理
        buffer_size = 5000
        buffer = []
        
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                self.total_scanned += 1
                
                if self.is_path_excluded(file_path):
                    continue
                
                file_info = self.scan_file(file_path)
                if file_info:
                    buffer.append(file_info)
                    self.total_indexed += 1
                
                # 缓冲区满时写入数据库
                if len(buffer) >= buffer_size:
                    self._flush_buffer(cursor, conn, buffer)
                    buffer = []
                
                if self.total_scanned % 1000 == 0:
                    current_time = time.time()
                    elapsed = current_time - self.start_time
                    speed = self.total_scanned / elapsed if elapsed > 0 else 0
                    print(f"已扫描: {self.total_scanned} 文件, 已索引: {self.total_indexed} 文件 ({speed:.1f} 文件/秒)")
        
        # 写入剩余数据
        if buffer:
            self._flush_buffer(cursor, conn, buffer)
        
        elapsed = time.time() - self.start_time
        speed = self.total_scanned / elapsed if elapsed > 0 else 0
        
        print(f"\n扫描完成！")
        print(f"总扫描文件数: {self.total_scanned}")
        print(f"总索引文件数: {self.total_indexed}")
        print(f"耗时: {elapsed:.2f} 秒")
        print(f"平均速度: {speed:.1f} 文件/秒")
        
        conn.close()
    
    def scan_from_csv(self, csv_path, encoding='utf-8'):
        """从CSV文件导入文件列表（优化方案二：流式处理）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        self.total_scanned = 0
        self.total_indexed = 0
        self.start_time = time.time()
        
        print(f"开始从CSV文件导入: {csv_path} (编码: {encoding})")
        
        # 优化方案二：使用固定大小的缓冲区进行流式处理
        buffer_size = 5000
        buffer = []
        
        try:
            with open(csv_path, 'r', encoding=encoding) as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    self.total_scanned += 1
                    
                    filename = row.get('filename', '')
                    if not filename or not os.path.exists(filename):
                        continue

                    # 确保路径是绝对路径
                    filename = os.path.abspath(filename)

                    if self.is_path_excluded(filename):
                        continue

                    file_info = self.scan_file(filename)
                    if file_info:
                        buffer.append(file_info)
                        self.total_indexed += 1
                    
                    # 缓冲区满时写入数据库
                    if len(buffer) >= buffer_size:
                        self._flush_buffer(cursor, conn, buffer)
                        buffer = []
                    
                    if self.total_scanned % 1000 == 0:
                        current_time = time.time()
                        elapsed = current_time - self.start_time
                        speed = self.total_scanned / elapsed if elapsed > 0 else 0
                        print(f"已处理: {self.total_scanned} 文件, 已索引: {self.total_indexed} 文件 ({speed:.1f} 文件/秒)")
        
        except Exception as e:
            print(f"读取CSV文件失败: {e}")
            # 写入已处理的数据
            if buffer:
                self._flush_buffer(cursor, conn, buffer)
            conn.close()
            return
        
        # 写入剩余数据
        if buffer:
            self._flush_buffer(cursor, conn, buffer)
        
        elapsed = time.time() - self.start_time
        speed = self.total_scanned / elapsed if elapsed > 0 else 0
        
        print(f"\nCSV导入完成！")
        print(f"总处理文件数: {self.total_scanned}")
        print(f"总索引文件数: {self.total_indexed}")
        print(f"耗时: {elapsed:.2f} 秒")
        print(f"平均速度: {speed:.1f} 文件/秒")
        
        conn.close()

class IndexManager:
    def __init__(self, db_path=None):
        self.db_path = db_path or get_db_path()
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path, timeout=60.0, isolation_level='IMMEDIATE')
    
    def clean_files(self):
        """清除文件索引"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM files')
        count = cursor.fetchone()[0]
        
        cursor.execute('DELETE FROM files')
        cursor.execute('DELETE FROM duplicate_files')
        cursor.execute('DELETE FROM duplicate_groups')
        
        conn.commit()
        conn.close()
        
        print(f"已清除文件索引，删除了 {count} 个文件记录")
    
    def clean_files_by_pattern(self, pattern):
        """按模式或路径清除文件索引
        
        Args:
            pattern: 通配符模式或路径前缀
        """
        import fnmatch
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 规范化模式：统一使用正斜杠，转为小写
        normalized_pattern = pattern.replace('\\', '/').lower()
        
        # 判断是通配符模式还是路径前缀
        has_wildcard = '*' in pattern or '?' in pattern
        
        # 获取所有文件
        cursor.execute('SELECT Filename FROM files')
        all_files = [row[0] for row in cursor.fetchall()]
        
        # 筛选匹配的文件
        files_to_delete = []
        for filepath in all_files:
            normalized_path = filepath.replace('\\', '/').lower()
            
            if has_wildcard:
                # 通配符匹配：匹配文件名或完整路径
                filename = os.path.basename(normalized_path)
                if fnmatch.fnmatch(filename, normalized_pattern) or \
                   fnmatch.fnmatch(normalized_path, normalized_pattern):
                    files_to_delete.append(filepath)
            else:
                # 路径前缀匹配
                if normalized_path.startswith(normalized_pattern):
                    files_to_delete.append(filepath)
        
        if not files_to_delete:
            print(f"没有找到匹配 '{pattern}' 的文件")
            conn.close()
            return
        
        print(f"找到 {len(files_to_delete)} 个匹配的文件")
        
        # 删除匹配的文件记录
        placeholders = ','.join(['?'] * len(files_to_delete))
        
        # 从 duplicate_files 中删除
        cursor.execute(f'''
            DELETE FROM duplicate_files 
            WHERE Filepath IN ({placeholders})
        ''', files_to_delete)
        duplicate_files_deleted = cursor.rowcount
        
        # 从 files 中删除
        cursor.execute(f'''
            DELETE FROM files 
            WHERE Filename IN ({placeholders})
        ''', files_to_delete)
        files_deleted = cursor.rowcount
        
        # 清理空的重复文件组
        cursor.execute('''
            DELETE FROM duplicate_groups 
            WHERE ID NOT IN (SELECT DISTINCT Group_ID FROM duplicate_files)
        ''')
        groups_deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"已清除匹配的文件索引:")
        print(f"  删除文件记录: {files_deleted} 个")
        print(f"  删除重复文件关联: {duplicate_files_deleted} 个")
        print(f"  清理空组: {groups_deleted} 个")
    
    def clean_index(self):
        """检查并清理索引文件
        
        检查files表中的每个文件：
        - 如果文件已丢失，删除记录
        - 如果文件已变更，更新记录
        
        如果有删除或更新操作：
        - 删除file_hash表中对应的记录
        - 重新计算duplicate_groups和duplicate_files表
        """
        print("\n" + "=" * 80)
        print("索引清理")
        print("=" * 80)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 获取所有文件记录
        cursor.execute('SELECT Filename, Size, Modified FROM files')
        files = cursor.fetchall()
        
        total_files = len(files)
        deleted_count = 0
        updated_count = 0
        unchanged_count = 0
        
        print(f"检查 {total_files} 个文件记录...")
        print("-" * 80)
        
        files_to_delete = []
        files_to_update = []
        
        for i, (filepath, size, modified) in enumerate(files, 1):
            # 显示进度
            if i % 100 == 0 or i == total_files:
                progress = (i / total_files * 100) if total_files > 0 else 0
                print(f"进度: {i}/{total_files} ({progress:.1f}%)", end='\r')
            
            # 检查文件是否存在
            if not os.path.exists(filepath):
                files_to_delete.append(filepath)
                deleted_count += 1
                print(f"\n文件丢失: {filepath}")
            else:
                # 检查文件是否发生变化
                try:
                    actual_size = os.path.getsize(filepath)
                    actual_modified = os.path.getmtime(filepath)
                    
                    # 确保modified是float类型
                    if isinstance(modified, str):
                        # 尝试解析ISO格式的时间字符串
                        try:
                            dt = datetime.fromisoformat(modified)
                            modified = dt.timestamp()
                        except:
                            modified = float(modified)
                    
                    if actual_size != size or abs(actual_modified - modified) > 0.001:
                        files_to_update.append((filepath, actual_size, actual_modified))
                        updated_count += 1
                        print(f"\n文件变更: {filepath}")
                        print(f"  原大小: {self.format_size(size)}, 新大小: {self.format_size(actual_size)}")
                    else:
                        unchanged_count += 1
                except Exception as e:
                    # 如果无法访问文件，标记为删除
                    files_to_delete.append(filepath)
                    deleted_count += 1
                    print(f"\n无法访问文件: {filepath} - {e}")
        
        print(f"\n\n检查完成！")
        print(f"文件丢失: {deleted_count} 个")
        print(f"文件变更: {updated_count} 个")
        print(f"文件未变: {unchanged_count} 个")
        print("-" * 80)
        
        # 如果有删除或更新操作
        if files_to_delete or files_to_update:
            print("\n正在更新数据库...")
            
            # 删除丢失的文件记录
            if files_to_delete:
                placeholders = ','.join(['?'] * len(files_to_delete))
                
                # 删除file_hash记录
                cursor.execute(f'DELETE FROM file_hash WHERE Filepath IN ({placeholders})', files_to_delete)
                hash_deleted = cursor.rowcount
                
                # 删除files记录
                cursor.execute(f'DELETE FROM files WHERE Filename IN ({placeholders})', files_to_delete)
                
                print(f"删除了 {deleted_count} 个丢失的文件记录")
                print(f"删除了 {hash_deleted} 个对应的哈希记录")
            
            # 更新变更的文件记录
            if files_to_update:
                for filepath, new_size, new_modified in files_to_update:
                    # 更新files表
                    cursor.execute('''
                        UPDATE files 
                        SET Size = ?, Modified = ?
                        WHERE Filename = ?
                    ''', (new_size, new_modified, filepath))
                    
                    # 删除对应的哈希记录
                    cursor.execute('DELETE FROM file_hash WHERE Filepath = ?', (filepath,))
                
                print(f"更新了 {updated_count} 个变更的文件记录")
            
            # 重新计算重复文件组
            self._rebuild_duplicate_groups_internal(cursor)
            conn.commit()
        else:
            print("\n没有需要清理的记录")
        
        conn.close()
        
        print("=" * 80)
    
    def format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
    
    def rebuild_index(self, scan_paths=None):
        """重建索引
        
        Args:
            scan_paths: 要扫描的路径列表，如果为None则扫描所有磁盘
        """
        print("开始重建索引...")
        
        # 清除所有数据
        self.clean_files()
        
        # 如果没有指定扫描路径，扫描所有磁盘
        if scan_paths is None:
            scan_paths = []
            for letter in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
                path = f"{letter}:\\"
                if os.path.exists(path):
                    scan_paths.append(path)
            
            if not scan_paths:
                print("没有找到可用的磁盘")
                return
        
        # 扫描所有路径
        scanner = FileScanner(self.db_path)
        
        for path in scan_paths:
            if os.path.exists(path) and os.path.isdir(path):
                print(f"\n扫描路径: {path}")
                scanner.scan_directory(path)
            else:
                print(f"跳过不存在的路径: {path}")
        
        print("\n索引重建完成！")
    
    def rebuild_duplicate_groups(self):
        """重建重复文件组（公共方法）
        
        扫描files表，按照扩展名和大小创建重复文件组
        可以被其他脚本引用
        
        Returns:
            tuple: (groups_created, files_assigned) 创建的组数和分配的文件数
        """
        print("\n" + "=" * 60)
        print("重建重复文件组")
        print("=" * 60)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取files表中的文件数量
            cursor.execute('SELECT COUNT(*) FROM files')
            total_files = cursor.fetchone()[0]
            
            if total_files == 0:
                print("files表为空，无需重建")
                conn.close()
                return (0, 0)
            
            print(f"files表中有 {total_files} 个文件")
            
            # 清理旧的重复文件组数据
            cursor.execute('DELETE FROM duplicate_files')
            cursor.execute('DELETE FROM duplicate_groups')
            conn.commit()
            print("已清理旧的重复文件组数据")
            
            # 查找重复文件（扩展名和大小都相同）
            cursor.execute('''
                SELECT f.Filename, f.Extension, f.Size
                FROM files f
                INNER JOIN (
                    SELECT Extension, Size
                    FROM files
                    GROUP BY Extension, Size
                    HAVING COUNT(*) > 1
                ) dup ON f.Extension = dup.Extension AND f.Size = dup.Size
                ORDER BY f.Extension, f.Size, f.Filename
            ''')
            
            duplicate_files = cursor.fetchall()
            
            if not duplicate_files:
                print("没有找到重复文件（扩展名和大小都相同的文件）")
                conn.close()
                return (0, 0)
            
            # 按扩展名和大小分组
            groups = {}
            for filepath, ext, size in duplicate_files:
                key = (ext, size)
                if key not in groups:
                    groups[key] = []
                groups[key].append(filepath)
            
            # 插入重复文件组（Hash字段为空，等待index hash计算）
            groups_created = 0
            files_assigned = 0
            
            for (ext, size), filepaths in groups.items():
                cursor.execute('''
                    INSERT INTO duplicate_groups (Extension, Size, Hash)
                    VALUES (?, ?, NULL)
                ''', (ext, size))
                group_id = cursor.lastrowid
                groups_created += 1
                
                for filepath in filepaths:
                    cursor.execute('''
                        INSERT INTO duplicate_files (Group_ID, Filepath)
                        VALUES (?, ?)
                    ''', (group_id, filepath))
                    files_assigned += 1
            
            conn.commit()
            
            print(f"\n重复文件组重建完成！")
            print(f"创建了 {groups_created} 个重复文件组")
            print(f"共有 {files_assigned} 个文件被分配到组中")
            
            return (groups_created, files_assigned)
            
        except Exception as e:
            print(f"重建重复文件组时出错: {e}")
            conn.rollback()
            return (0, 0)
        finally:
            conn.close()
        
        print("=" * 60)
    
    def _rebuild_duplicate_groups_internal(self, cursor):
        """重建重复文件组（内部方法，供clean_index使用）
        
        Args:
            cursor: 数据库游标
        """
        print("\n重新计算重复文件组...")
        cursor.execute('DELETE FROM duplicate_files')
        cursor.execute('DELETE FROM duplicate_groups')
        
        # 查找重复文件（扩展名和大小都相同）
        cursor.execute('''
            SELECT f.Filename, f.Extension, f.Size
            FROM files f
            INNER JOIN (
                SELECT Extension, Size
                FROM files
                GROUP BY Extension, Size
                HAVING COUNT(*) > 1
            ) dup ON f.Extension = dup.Extension AND f.Size = dup.Size
            ORDER BY f.Extension, f.Size, f.Filename
        ''')
        
        duplicate_files = cursor.fetchall()
        
        if not duplicate_files:
            print("没有找到重复文件")
            return
        
        # 按扩展名和大小分组
        groups = {}
        for filepath, ext, size in duplicate_files:
            key = (ext, size)
            if key not in groups:
                groups[key] = []
            groups[key].append(filepath)
        
        # 插入重复文件组（Hash字段为空，等待index hash计算）
        for (ext, size), filepaths in groups.items():
            cursor.execute('''
                INSERT INTO duplicate_groups (Extension, Size, Hash)
                VALUES (?, ?, NULL)
            ''', (ext, size))
            group_id = cursor.lastrowid
            
            for filepath in filepaths:
                cursor.execute('''
                    INSERT INTO duplicate_files (Group_ID, Filepath)
                    VALUES (?, ?)
                ''', (group_id, filepath))
        
        print(f"创建了 {len(groups)} 个重复文件组")
        print(f"共有 {len(duplicate_files)} 个文件被分配到组中")

app = typer.Typer()

@app.command()
def scan(path: str):
    """扫描指定路径，将文件放入files表，扫描后会自动重建重复文件组"""
    if not os.path.exists(path) or not os.path.isdir(path):
        typer.echo(f"错误: 路径不存在或不是目录: {path}")
        return
    
    scanner = FileScanner()
    scanner.scan_directory(path)
    
    # 自动重建重复文件组
    _rebuild_duplicate_groups()

@app.command(name="import")
def import_csv(csv_path: str, encoding: str = "utf-8"):
    """从CSV文件导入文件列表，导入后会自动重建重复文件组"""
    if not os.path.exists(csv_path) or not os.path.isfile(csv_path):
        typer.echo(f"错误: CSV文件不存在: {csv_path}")
        return
    
    scanner = FileScanner()
    scanner.scan_from_csv(csv_path, encoding)
    
    # 自动重建重复文件组
    _rebuild_duplicate_groups()

@app.command()
def rebuild():
    """检查并清理索引文件，然后重建重复文件组"""
    manager = IndexManager()
    manager.clean_index()
    _rebuild_duplicate_groups()

@app.command()
def clear(
    pattern: Optional[str] = typer.Argument(None, help="清理模式（通配符或路径前缀）"),
    force: bool = typer.Option(False, "--force", "-f", help="强制清理，不询问"),
    all: bool = typer.Option(False, "--all", "-a", help="清除所有文件索引")
):
    """清除文件索引（保留哈希值，哈希值请使用 hash clear 清除）
    
    示例:
        index clear --all                    # 清除所有文件索引
        index clear "*.tmp"                  # 清除匹配通配符的文件
        index clear "e:/downloads"           # 清除指定路径下的文件
        index clear "e:/downloads/*.tmp"     # 清除指定路径下匹配通配符的文件
    """
    manager = IndexManager()
    
    if all:
        # 清除所有文件索引
        if not force:
            typer.echo("这将清除所有文件索引，但保留哈希值")
            typer.echo("哈希值可使用 hash clear 命令清除")
            typer.echo("使用 --force 选项跳过确认")
            return
        manager.clean_files()
    elif pattern:
        # 按模式或路径清除
        if not force:
            typer.echo(f"这将清除匹配 '{pattern}' 的文件索引，但保留哈希值")
            typer.echo("哈希值可使用 hash clear 命令清除")
            typer.echo("使用 --force 选项跳过确认")
            return
        manager.clean_files_by_pattern(pattern)
    else:
        typer.echo("错误: 请指定 --all 或提供匹配模式")
        typer.echo("示例:")
        typer.echo("  index clear --all              # 清除所有")
        typer.echo("  index clear '*.tmp'            # 按通配符清除")
        typer.echo("  index clear 'e:/downloads'     # 按路径清除")

# 辅助函数
def _rebuild_duplicate_groups():
    """重建重复文件组"""
    index_manager = IndexManager()
    index_manager.rebuild_duplicate_groups()


