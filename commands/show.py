import typer
import sqlite3
import os
from typing import Optional
from datetime import datetime
from rich.console import Console
from commands.db import get_db_path

class DataViewer:
    """数据查看器 - 提供查询和展示重复文件数据的功能"""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or get_db_path()
        self.path_limit = None
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path, timeout=60.0, isolation_level='IMMEDIATE')
    
    def get_statistics(self, hash_only=True):
        """获取统计信息
        
        Args:
            hash_only: 是否只统计已确认哈希值的组（Hash字段不为空）
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 获取files表中的文件数量
        cursor.execute('SELECT COUNT(*) FROM files')
        total_files = cursor.fetchone()[0]
        
        # 获取duplicate_groups表中的组数量
        if hash_only:
            cursor.execute("SELECT COUNT(*) FROM duplicate_groups WHERE Hash IS NOT NULL AND Hash != ''")
        else:
            cursor.execute('SELECT COUNT(*) FROM duplicate_groups')
        duplicate_groups = cursor.fetchone()[0]
        
        # 获取duplicate_files表中的文件数量（只统计已确认哈希值的组中的文件）
        if hash_only:
            cursor.execute('''
                SELECT COUNT(*) FROM duplicate_files df
                INNER JOIN duplicate_groups dg ON df.Group_ID = dg.ID
                WHERE dg.Hash IS NOT NULL AND dg.Hash != ''
            ''')
        else:
            cursor.execute('SELECT COUNT(*) FROM duplicate_files')
        duplicate_files = cursor.fetchone()[0]
        
        # 获取file_hash表中的文件数量
        cursor.execute('SELECT COUNT(*) FROM file_hash WHERE Hash IS NOT NULL AND Hash != ""')
        hashed_files = cursor.fetchone()[0]
        
        # 获取待计算哈希值的文件数量
        cursor.execute('SELECT COUNT(*) FROM duplicate_files WHERE Filepath NOT IN (SELECT Filepath FROM file_hash)')
        unhashed_files = cursor.fetchone()[0]
        
        # 获取已计算哈希值的组数量
        cursor.execute("SELECT COUNT(*) FROM duplicate_groups WHERE Hash IS NOT NULL AND Hash != ''")
        hashed_groups = cursor.fetchone()[0]
        
        # 获取未计算哈希值的组数量
        cursor.execute("SELECT COUNT(*) FROM duplicate_groups WHERE Hash IS NULL OR Hash = ''")
        unhashed_groups = cursor.fetchone()[0]
        
        # 计算总大小
        cursor.execute('SELECT SUM(Size) FROM files')
        total_size = cursor.fetchone()[0] or 0
        
        # 计算重复文件总大小（默认按已计算哈希的组）
        cursor.execute('''
        SELECT SUM(duplicate_size)
        FROM (
            SELECT (COUNT(*) - 1) * MIN(f.Size) as duplicate_size
            FROM duplicate_files df
            INNER JOIN files f ON df.Filepath = f.Filename
            INNER JOIN duplicate_groups dg ON df.Group_ID = dg.ID
            WHERE dg.Hash IS NOT NULL AND dg.Hash != ''
            GROUP BY df.Group_ID
        )
        ''')
        duplicate_size = cursor.fetchone()[0] or 0
        
        # 计算已计算哈希的文件总大小
        cursor.execute('''
        SELECT SUM(f.Size) FROM file_hash fh
        INNER JOIN files f ON fh.Filepath = f.Filename
        WHERE fh.Hash IS NOT NULL AND fh.Hash != ''
        ''')
        hashed_size = cursor.fetchone()[0] or 0
        
        # 计算duplicate_files中所有文件的总大小（用于计算哈希进度）
        cursor.execute('''
        SELECT SUM(f.Size) FROM duplicate_files df
        INNER JOIN files f ON df.Filepath = f.Filename
        ''')
        duplicate_files_total_size = cursor.fetchone()[0] or 0
        
        # 计算平均重复度（每个重复组平均有多少个文件）
        if hash_only:
            cursor.execute('''
            SELECT AVG(file_count) FROM (
                SELECT COUNT(*) as file_count
                FROM duplicate_files df
                INNER JOIN duplicate_groups dg ON df.Group_ID = dg.ID
                WHERE dg.Hash IS NOT NULL AND dg.Hash != ''
                GROUP BY df.Group_ID
            )
            ''')
        else:
            cursor.execute('''
            SELECT AVG(file_count) FROM (
                SELECT COUNT(*) as file_count
                FROM duplicate_files df
                GROUP BY df.Group_ID
            )
            ''')
        avg_duplication = cursor.fetchone()[0] or 0
        
        # 计算平均重复组大小
        if hash_only:
            cursor.execute('''
            SELECT AVG(dg.Size) FROM duplicate_groups dg
            WHERE dg.Hash IS NOT NULL AND dg.Hash != ''
            ''')
        else:
            cursor.execute('SELECT AVG(Size) FROM duplicate_groups')
        avg_group_size = cursor.fetchone()[0] or 0
        
        # 磁盘分布统计
        cursor.execute('''
        SELECT 
            UPPER(SUBSTR(f.Filename, 1, 2)) as disk,
            COUNT(DISTINCT df.Group_ID) as group_count,
            COUNT(*) as file_count
        FROM duplicate_files df
        INNER JOIN files f ON df.Filepath = f.Filename
        INNER JOIN duplicate_groups dg ON df.Group_ID = dg.ID
        WHERE dg.Hash IS NOT NULL AND dg.Hash != ''
        GROUP BY disk
        ORDER BY group_count DESC
        ''')
        disk_distribution = {}
        for disk, group_count, file_count in cursor.fetchall():
            disk_distribution[disk] = {'group_count': group_count, 'file_count': file_count}
        
        # 跨磁盘重复统计（一个组中的文件分布在多个磁盘上）
        cursor.execute('''
        SELECT COUNT(*) FROM (
            SELECT df.Group_ID
            FROM duplicate_files df
            INNER JOIN duplicate_groups dg ON df.Group_ID = dg.ID
            INNER JOIN files f ON df.Filepath = f.Filename
            WHERE dg.Hash IS NOT NULL AND dg.Hash != ''
            GROUP BY df.Group_ID
            HAVING COUNT(DISTINCT UPPER(SUBSTR(f.Filename, 1, 2))) > 1
        )
        ''')
        cross_disk_groups = cursor.fetchone()[0]
        
        # 文件类型 Top 10（按可释放空间排序）
        cursor.execute('''
        SELECT 
            dg.Extension,
            COUNT(*) as group_count,
            SUM((cnt - 1) * dg.Size) as savable_space
        FROM duplicate_groups dg
        INNER JOIN (
            SELECT Group_ID, COUNT(*) as cnt
            FROM duplicate_files
            GROUP BY Group_ID
        ) df ON dg.ID = df.Group_ID
        WHERE dg.Hash IS NOT NULL AND dg.Hash != ''
        GROUP BY dg.Extension
        ORDER BY savable_space DESC
        LIMIT 10
        ''')
        top_extensions = []
        for ext, group_count, savable in cursor.fetchall():
            top_extensions.append({
                'extension': ext or '(无扩展名)',
                'group_count': group_count,
                'savable_space': savable
            })
        
        # 大小分布统计
        cursor.execute('''
        SELECT 
            CASE
                WHEN Size < 1048576 THEN '< 1MB'
                WHEN Size < 10485760 THEN '1MB - 10MB'
                WHEN Size < 104857600 THEN '10MB - 100MB'
                WHEN Size < 1073741824 THEN '100MB - 1GB'
                ELSE '> 1GB'
            END as size_range,
            COUNT(*) as group_count,
            SUM((cnt - 1) * dg.Size) as savable_space
        FROM duplicate_groups dg
        INNER JOIN (
            SELECT Group_ID, COUNT(*) as cnt
            FROM duplicate_files
            GROUP BY Group_ID
        ) df ON dg.ID = df.Group_ID
        WHERE dg.Hash IS NOT NULL AND dg.Hash != ''
        GROUP BY size_range
        ORDER BY MIN(dg.Size)
        ''')
        size_distribution = {}
        for range_name, group_count, savable in cursor.fetchall():
            size_distribution[range_name] = {'group_count': group_count, 'savable_space': savable}
        
        # 数据库大小
        import os
        db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        
        conn.close()
        
        return {
            'total_files': total_files,
            'duplicate_groups': duplicate_groups,
            'duplicate_files': duplicate_files,
            'hashed_files': hashed_files,
            'unhashed_files': unhashed_files,
            'hashed_groups': hashed_groups,
            'unhashed_groups': unhashed_groups,
            'total_size': total_size,
            'duplicate_size': duplicate_size,
            'hashed_size': hashed_size,
            'duplicate_files_total_size': duplicate_files_total_size,
            'avg_duplication': avg_duplication,
            'avg_group_size': avg_group_size,
            'disk_distribution': disk_distribution,
            'cross_disk_groups': cross_disk_groups,
            'top_extensions': top_extensions,
            'size_distribution': size_distribution,
            'db_size': db_size
        }
    
    def get_groups_list(self, count=20, hash_only=True, min_size=None, max_size=None, extension=None, sort_by='size'):
        """获取重复文件组列表
        
        Args:
            count: 返回的组数量
            hash_only: 是否只返回已确认哈希值的组
            min_size: 最小文件大小（字节）
            max_size: 最大文件大小（字节）
            extension: 文件扩展名过滤
            sort_by: 排序方式（size/count/path）
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 构建WHERE条件
        conditions = []
        params = []
        
        if hash_only:
            conditions.append("dg.Hash IS NOT NULL AND dg.Hash != ''")
        
        if min_size is not None:
            conditions.append("dg.Size >= ?")
            params.append(min_size)
        
        if max_size is not None:
            conditions.append("dg.Size <= ?")
            params.append(max_size)
        
        if extension is not None:
            conditions.append("dg.Extension = ?")
            params.append(extension)
        
        if self.path_limit:
            conditions.append("f.Filename LIKE ?")
            params.append(f"{self.path_limit}%")
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        # 构建ORDER BY
        if sort_by == 'size':
            order_by = "ORDER BY (COUNT(*) - 1) * dg.Size DESC"
        elif sort_by == 'count':
            order_by = "ORDER BY COUNT(*) DESC"
        elif sort_by == 'path':
            order_by = "ORDER BY MIN(f.Filename)"
        else:
            order_by = "ORDER BY (COUNT(*) - 1) * dg.Size DESC"
        
        # 构建查询
        if self.path_limit:
            query = f'''
            SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count, dg.Hash
            FROM duplicate_groups dg
            INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
            INNER JOIN files f ON df.Filepath = f.Filename
            {where_clause}
            GROUP BY dg.ID
            {order_by}
            LIMIT ?
            '''
        else:
            query = f'''
            SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count, dg.Hash
            FROM duplicate_groups dg
            INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
            {where_clause}
            GROUP BY dg.ID
            {order_by}
            LIMIT ?
            '''
        
        params.append(count)
        cursor.execute(query, params)
        groups = cursor.fetchall()
        
        result = []
        for group_id, size, ext, file_count, hash_val in groups:
            result.append({
                'group_id': group_id,
                'size': size,
                'extension': ext,
                'file_count': file_count,
                'savable_space': (file_count - 1) * size,
                'hash': hash_val
            })
        
        conn.close()
        return result
    
    def get_group_details(self, group_id):
        """获取指定组的详细信息
        
        Args:
            group_id: 组ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 获取组基本信息
        cursor.execute('''
        SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count, dg.Hash
        FROM duplicate_groups dg
        INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
        WHERE dg.ID = ?
        GROUP BY dg.ID
        ''', (group_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        
        group_id, size, extension, file_count, hash_val = row
        
        # 获取组内所有文件
        cursor.execute('''
        SELECT f.Filename, f.Modified, f.Size
        FROM duplicate_files df
        INNER JOIN files f ON df.Filepath = f.Filename
        WHERE df.Group_ID = ?
        ORDER BY f.Filename
        ''', (group_id,))
        
        files = []
        for filepath, modified, file_size in cursor.fetchall():
            disk = os.path.splitdrive(filepath)[0].upper()
            files.append({
                'filepath': filepath,
                'disk': disk,
                'modified': modified,
                'size': file_size
            })
        
        conn.close()
        
        return {
            'group_id': group_id,
            'size': size,
            'extension': extension,
            'file_count': file_count,
            'group_size': size * file_count,
            'savable_space': (file_count - 1) * size,
            'hash': hash_val,
            'files': files
        }
    
    def filter_by_pattern(self, pattern, hash_only=True):
        """使用通配符模式筛选重复文件组
        
        Args:
            pattern: 筛选表达式，支持通配符如 *.mp4, E:/Downloads/*.mp4
            hash_only: 是否只返回已确认哈希值的组（Hash字段不为空）
        """
        import fnmatch
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 构建基础查询条件
        hash_condition = "WHERE dg.Hash IS NOT NULL AND dg.Hash != ''" if hash_only else "WHERE 1=1"
        
        # 获取所有符合条件的组（需要关联duplicate_files表来统计文件数量）
        cursor.execute(f'''
        SELECT dg.ID, dg.Size, dg.Extension, COUNT(df.Filepath) as file_count, dg.Hash
        FROM duplicate_groups dg
        INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
        {hash_condition}
        GROUP BY dg.ID
        HAVING COUNT(df.Filepath) > 1
        ORDER BY (COUNT(df.Filepath) - 1) * dg.Size DESC
        ''')
        
        groups = cursor.fetchall()
        
        # 规范化模式：统一使用正斜杠进行匹配，转为小写
        normalized_pattern = pattern.replace('\\', '/').lower()
        
        result = []
        for group_id, size, extension, file_count, hash_val in groups:
            # 获取该组的所有文件路径
            cursor.execute('''
            SELECT f.Filename
            FROM duplicate_files df
            INNER JOIN files f ON df.Filepath = f.Filename
            WHERE df.Group_ID = ?
            ''', (group_id,))
            
            files = cursor.fetchall()
            file_paths = [f[0] for f in files]
            
            # 检查是否有文件匹配模式
            matched_files = []
            for filepath in file_paths:
                # 规范化文件路径，转为小写
                normalized_path = filepath.replace('\\', '/').lower()
                filename = os.path.basename(normalized_path)
                
                # 检查文件名是否匹配（如果是纯文件名模式如 *.mp4）
                # 或者完整路径是否匹配（如果是路径模式如 E:/Downloads/*.mp4）
                if fnmatch.fnmatch(filename, normalized_pattern):
                    matched_files.append(filepath)
                elif fnmatch.fnmatch(normalized_path, normalized_pattern):
                    matched_files.append(filepath)
                # 额外的路径匹配逻辑，处理路径模式
                else:
                    # 尝试匹配路径的任意部分
                    path_parts = normalized_path.split('/')
                    
                    # 检查是否有路径部分匹配
                    for part in path_parts:
                        if fnmatch.fnmatch(part, normalized_pattern):
                            matched_files.append(filepath)
                            break
                    
                    # 检查路径是否包含模式字符串
                    if normalized_pattern in normalized_path:
                        matched_files.append(filepath)
            
            # 如果该组有文件匹配，则添加到结果
            if matched_files:
                result.append({
                    'group_id': group_id,
                    'size': size,
                    'extension': extension,
                    'file_count': file_count,
                    'group_size': size * file_count,
                    'savable_space': (file_count - 1) * size,
                    'hash': hash_val,
                    'matched_files': matched_files
                })
        
        conn.close()
        return result
    
    def get_groups_by_path(self, path_prefix, hash_only=True):
        """获取指定路径下的重复文件组
        
        Args:
            path_prefix: 路径前缀
            hash_only: 是否只返回已确认哈希值的组（Hash字段不为空）
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 规范化路径前缀：统一使用正斜杠，转为小写
        normalized_prefix = path_prefix.replace('\\', '/').lower()
        
        # 构建哈希条件
        hash_condition = "AND dg.Hash IS NOT NULL AND dg.Hash != ''" if hash_only else ""
        
        # 使用大小写不敏感的匹配
        cursor.execute(f'''
        SELECT DISTINCT dg.ID, dg.Size, dg.Extension, dg.Hash
        FROM duplicate_groups dg
        INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
        INNER JOIN files f ON df.Filepath = f.Filename
        WHERE LOWER(REPLACE(f.Filename, '\\\\', '/')) LIKE ? {hash_condition}
        ''', (f"{normalized_prefix}%",))
        
        groups = []
        for row in cursor.fetchall():
            group_id, size, extension, hash_val = row
            
            # 获取该组在该路径下的文件
            cursor.execute(f'''
            SELECT f.Filename
            FROM duplicate_files df
            INNER JOIN files f ON df.Filepath = f.Filename
            WHERE df.Group_ID = ? AND LOWER(REPLACE(f.Filename, '\\\\', '/')) LIKE ? {hash_condition}
            ORDER BY f.Filename
            ''', (group_id, f"{normalized_prefix}%"))
            
            files = [f[0] for f in cursor.fetchall()]
            
            if files:  # 只添加有文件的组
                groups.append({
                    'group_id': group_id,
                    'size': size,
                    'extension': extension,
                    'file_count': len(files),
                    'files': files,
                    'hash': hash_val
                })
        
        conn.close()
        return groups
    
    def get_duplicate_details(self, hash_value):
        """获取指定哈希值的所有文件详情"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT 
            df.Filepath,
            dg.Size,
            dg.Extension,
            dg.Hash,
            fh.created_at
        FROM duplicate_files df
        INNER JOIN duplicate_groups dg ON df.Group_ID = dg.ID
        LEFT JOIN file_hash fh ON df.Filepath = fh.Filepath
        WHERE dg.Hash = ?
        ORDER BY df.Filepath
        ''', (hash_value,))
        
        files = []
        for row in cursor.fetchall():
            filepath, size, extension, hash_val, created_at = row
            
            # 获取磁盘信息
            disk = os.path.splitdrive(filepath)[0] if os.path.splitdrive(filepath)[0] else '未知'
            
            # 获取文件修改时间
            try:
                modified = datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
            except:
                modified = '未知'
            
            files.append({
                'filepath': filepath,
                'disk': disk,
                'size': size,
                'extension': extension,
                'hash': hash_val,
                'modified': modified,
                'created_at': created_at or '未知'
            })
        
        conn.close()
        return files

    def get_stats_by_extension(self):
        """按扩展名统计"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT 
            Extension,
            COUNT(*) as count
        FROM duplicate_groups
        WHERE Hash IS NOT NULL AND Hash != ''
        GROUP BY Extension
        ORDER BY count DESC
        ''')
        
        result = {}
        for ext, count in cursor.fetchall():
            result[ext] = count
        
        conn.close()
        return result
    
    def get_stats_by_size_range(self):
        """按大小范围统计"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT 
            CASE
                WHEN Size < 1048576 THEN '< 1MB'
                WHEN Size < 10485760 THEN '1MB - 10MB'
                WHEN Size < 104857600 THEN '10MB - 100MB'
                WHEN Size < 1073741824 THEN '100MB - 1GB'
                ELSE '> 1GB'
            END as size_range,
            COUNT(*) as count
        FROM duplicate_groups
        WHERE Hash IS NOT NULL AND Hash != ''
        GROUP BY size_range
        ORDER BY MIN(Size)
        ''')
        
        result = {}
        for range_name, count in cursor.fetchall():
            result[range_name] = count
        
        conn.close()
        return result
    
    def get_stats_by_date(self):
        """按日期统计"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as count
        FROM file_hash
        WHERE created_at IS NOT NULL
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        LIMIT 30
        ''')
        
        result = {}
        for date, count in cursor.fetchall():
            result[date] = count
        
        conn.close()
        return result

app = typer.Typer()
analyzer = DataViewer()

@app.command()
def groups(
    top: int = 20,
    unconfirmed: bool = False,
    min_size: Optional[str] = None,
    max_size: Optional[str] = None,
    extension: Optional[str] = None,
    sort: str = "size",
    detail: Optional[int] = None
):
    """显示重复文件组列表"""
    hash_only = not unconfirmed
    
    # 解析大小参数
    parsed_min_size = _parse_size(min_size) if min_size else None
    parsed_max_size = _parse_size(max_size) if max_size else None
    
    # 如果指定了 detail，显示组详情
    if detail is not None:
        _show_group_detail(detail)
        return
    
    # 获取组列表
    groups = analyzer.get_groups_list(
        count=top,
        hash_only=hash_only,
        min_size=parsed_min_size,
        max_size=parsed_max_size,
        extension=extension,
        sort_by=sort
    )
    
    typer.echo("\n重复文件组列表")
    typer.echo("=" * 60)
    
    if not groups:
        typer.echo("  没有找到符合条件的重复文件组")
    else:
        for group in groups:
            typer.echo(f"\n组ID: {group['group_id']}")
            typer.echo(f"  文件大小: {group['size']:,} 字节 ({group['size']/1024/1024:.2f} MB)")
            typer.echo(f"  文件扩展名: {group['extension']}")
            typer.echo(f"  文件数量: {group['file_count']} 个")
            typer.echo(f"  可释放空间: {group['savable_space']:,} 字节 ({group['savable_space']/1024/1024/1024:.2f} GB)")
            if group['hash']:
                typer.echo(f"  哈希值: {group['hash']}")
            else:
                typer.echo(f"  哈希值: 未确认")
    
    typer.echo("=" * 60)

@app.command()
def files(
    pattern: str,
    all: bool = False,
    hash: bool = False,
    limit: int = 100
):
    """查询文件，支持路径或模式"""
    show_all = all
    show_hash = hash
    
    # 判断是路径还是模式（包含通配符或不是完整路径）
    has_wildcard = '*' in pattern or '?' in pattern
    
    # 检查是否是完整路径（Windows路径格式）
    is_full_path = False
    if not has_wildcard:
        # 检查是否是Windows路径格式（如 C:\ 或 D:\）
        if len(pattern) >= 2 and pattern[1] == ':' and (pattern[0].isalpha()):
            is_full_path = True
        # 检查是否是绝对路径（以 \ 或 / 开头）
        elif pattern.startswith('\\') or pattern.startswith('/'):
            is_full_path = True
    
    if has_wildcard or not is_full_path:
        # 模式搜索：查找重复文件组
        # 根据 --all 选项决定是否只显示已计算哈希的组
        hash_only = not show_all
        groups = analyzer.filter_by_pattern(pattern, hash_only=hash_only)
        
        # 如果不是显示所有组，则获取所有组（包括未计算哈希的）用于提示
        unhashed_count = 0
        if not show_all:
            all_groups = analyzer.filter_by_pattern(pattern, hash_only=False)
            unhashed_count = len(all_groups) - len(groups)
        
        typer.echo(f"\n文件搜索结果（模式: {pattern}）")
        typer.echo("=" * 60)
        
        if not groups:
            typer.echo("  没有找到匹配的文件")
            if unhashed_count > 0:
                typer.echo(f"\n  提示: 有 {unhashed_count} 个组因未计算哈希值而被隐藏")
                typer.echo("  使用 --all 选项显示所有组（包括未计算哈希的）")
        else:
            typer.echo(f"  找到 {len(groups)} 个匹配的重复文件组")
            for i, group in enumerate(groups[:limit], 1):
                typer.echo(f"\n{i}. 组ID: {group['group_id']}")
                typer.echo(f"   文件大小: {group['size']:,} 字节")
                typer.echo(f"   文件扩展名: {group['extension']}")
                typer.echo(f"   文件数量: {group['file_count']} 个")
                typer.echo(f"   匹配的文件:")
                for j, filepath in enumerate(group['matched_files'][:5], 1):
                    typer.echo(f"     {j}. {filepath}")
                if len(group['matched_files']) > 5:
                    typer.echo(f"     ... 还有 {len(group['matched_files']) - 5} 个匹配文件")
            
            if len(groups) > limit:
                typer.echo(f"\n... 还有 {len(groups) - limit} 个组未显示（使用 --limit {limit + 20} 显示更多）")
            
            if unhashed_count > 0:
                typer.echo(f"\n  提示: 还有 {unhashed_count} 个组因未计算哈希值而被隐藏")
                typer.echo("  使用 --all 选项显示所有组（包括未计算哈希的）")
        
        typer.echo("=" * 60)
    else:
        # 路径查询：显示已索引的文件
        if show_all:
            # 显示所有已索引文件
            conn = analyzer.get_connection()
            cursor = conn.cursor()
            
            # 规范化路径：统一使用正斜杠，转为小写
            normalized_pattern = pattern.replace('\\', '/').lower()
            
            # 使用大小写不敏感的匹配
            query = '''
                SELECT f.Filename, f.Size, f.Modified, fh.Hash, fh.created_at
                FROM files f
                LEFT JOIN file_hash fh ON f.Filename = fh.Filepath
                WHERE LOWER(REPLACE(f.Filename, '\\\\', '/')) LIKE ?
                ORDER BY f.Filename
                LIMIT ?
            '''
            cursor.execute(query, (f"{normalized_pattern}%", limit))
            files = cursor.fetchall()
            conn.close()
            
            typer.echo(f"\n路径 {pattern} 下已索引的文件:")
            if not files:
                typer.echo("  没有找到已索引的文件")
            else:
                for i, (filename, size, modified, hash_val, created_at) in enumerate(files, 1):
                    hash_status = "已计算" if hash_val else "未计算"
                    typer.echo(f"  {i}. {filename}")
                    typer.echo(f"     大小: {size:,} 字节, 修改时间: {modified}, 哈希状态: {hash_status}")
                    if show_hash and hash_val:
                        typer.echo(f"     哈希值: {hash_val}")
                        if created_at:
                            typer.echo(f"     计算时间: {created_at}")
            
            if len(files) >= limit:
                typer.echo(f"\n... 还有更多文件（仅显示前{limit}个，使用 --limit {limit + 100} 显示更多）")
        else:
            # 显示路径下的重复文件组
            # 根据 --all 选项决定是否只显示已计算哈希的组
            hash_only = not show_all
            groups = analyzer.get_groups_by_path(pattern, hash_only=hash_only)
            
            # 如果不是显示所有组，则获取所有组（包括未计算哈希的）用于提示
            unhashed_count = 0
            if not show_all:
                all_groups = analyzer.get_groups_by_path(pattern, hash_only=False)
                unhashed_count = len(all_groups) - len(groups)
            
            typer.echo(f"\n路径 {pattern} 下的重复文件")
            typer.echo("=" * 60)
            
            if not groups:
                typer.echo("  没有找到重复文件")
                if unhashed_count > 0:
                    typer.echo(f"\n  提示: 有 {unhashed_count} 个组因未计算哈希值而被隐藏")
                    typer.echo("  使用 --all 选项显示所有组（包括未计算哈希的）")
            else:
                typer.echo(f"  找到 {len(groups)} 个重复文件组")
                for i, group in enumerate(groups[:limit], 1):
                    typer.echo(f"\n{i}. 组ID: {group['group_id']}")
                    typer.echo(f"   文件大小: {group['size']:,} 字节")
                    typer.echo(f"   文件扩展名: {group['extension']}")
                    typer.echo(f"   文件数量: {group['file_count']} 个")
                    typer.echo(f"   包含的文件:")
                    for j, filepath in enumerate(group['files'][:5], 1):
                        typer.echo(f"     {j}. {filepath}")
                    if len(group['files']) > 5:
                        typer.echo(f"     ... 还有 {len(group['files']) - 5} 个文件")
                
                if len(groups) > limit:
                    typer.echo(f"\n... 还有 {len(groups) - limit} 个组未显示（使用 --limit {limit + 20} 显示更多）")
                
                if unhashed_count > 0:
                    typer.echo(f"\n  提示: 还有 {unhashed_count} 个组因未计算哈希值而被隐藏")
                    typer.echo("  使用 --all 选项显示所有组（包括未计算哈希的）")
        
        typer.echo("=" * 60)

@app.command()
def hash(hash_value: str):
    """显示指定哈希值的所有文件"""
    files = analyzer.get_duplicate_details(hash_value)
    
    typer.echo(f"\n哈希值为 {hash_value} 的重复文件:")
    typer.echo("=" * 60)
    if not files:
        typer.echo("  没有找到文件")
    else:
        for i, file_info in enumerate(files, 1):
            typer.echo(f"\n{i}. 文件路径: {file_info['filepath']}")
            typer.echo(f"   磁盘: {file_info['disk']}")
            typer.echo(f"   大小: {file_info['size']:,} 字节")
            typer.echo(f"   修改时间: {file_info['modified']}")
            typer.echo(f"   哈希值: {file_info['hash']}")
            typer.echo(f"   计算时间: {file_info['created_at']}")
    typer.echo("=" * 60)

@app.command()
def stats(
    by_extension: bool = False,
    by_size_range: bool = False,
    by_date: bool = False
):
    """显示统计分析"""
    console = Console()
    
    def format_size(size):
        if size >= 1073741824:
            return f"{size/1073741824:.2f} GB"
        elif size >= 1048576:
            return f"{size/1048576:.2f} MB"
        elif size >= 1024:
            return f"{size/1024:.2f} KB"
        else:
            return f"{size} B"
    
    def format_size_colored(size):
        if size >= 1073741824:
            return f"[bold red]{size/1073741824:.2f} GB[/bold red]"
        elif size >= 1048576:
            return f"[bold yellow]{size/1048576:.2f} MB[/bold yellow]"
        elif size >= 1024:
            return f"[bold green]{size/1024:.2f} KB[/bold green]"
        else:
            return f"[bold]{size} B[/bold]"
    
    def print_progress_bar(progress, width=30):
        filled = int(progress / 100 * width)
        return f"[green]{'█' * filled}[/green][dim]{'░' * (width - filled)}[/dim]"
    
    if by_extension:
        stats = analyzer.get_stats_by_extension()
        console.print()
        console.print("[bold blue]📊 按扩展名统计[/bold blue]")
        console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
        console.print()
        for ext, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            console.print(f"  {ext or '(无扩展名)':<15} [bold green]{count:,}[/bold green] 个组")
        console.print()
    elif by_size_range:
        stats = analyzer.get_stats_by_size_range()
        console.print()
        console.print("[bold blue]📊 按大小范围统计[/bold blue]")
        console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
        console.print()
        size_order = ['< 1MB', '1MB - 10MB', '10MB - 100MB', '100MB - 1GB', '> 1GB']
        for range_name in size_order:
            if range_name in stats:
                console.print(f"  {range_name:<15} [bold green]{stats[range_name]:,}[/bold green] 个组")
        console.print()
    elif by_date:
        stats = analyzer.get_stats_by_date()
        console.print()
        console.print("[bold blue]📊 按日期统计[/bold blue]")
        console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
        console.print()
        for date, count in stats.items():
            console.print(f"  {date:<15} [bold green]{count:,}[/bold green] 个组")
        console.print()
    else:
        stats = analyzer.get_statistics(hash_only=True)
        
        console.print()
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 文件统计信息
        # ═══════════════════════════════════════════════════════════════════════════
        
        console.print("[bold blue]📄 文件统计信息[/bold blue]")
        console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
        console.print()
        console.print(f"  扫描文件数          [bold]{stats['total_files']:,}[/bold]")
        console.print(f"  文件总大小          {format_size_colored(stats['total_size'])}")
        console.print(f"  已计算哈希文件      [bold green]{stats['hashed_files']:,}[/bold green]")
        console.print(f"  待计算哈希文件      [bold yellow]{stats['unhashed_files']:,}[/bold yellow]")
        console.print()
        
        # 磁盘分布
        console.print("  [dim]───────────────────────────────────────────────[/dim]")
        console.print("  💿 磁盘分布")
        if stats['disk_distribution']:
            for disk, info in stats['disk_distribution'].items():
                console.print(f"    {disk}    {info['file_count']:,} 个文件")
        else:
            console.print("    暂无数据")
        console.print()
        
        # 哈希计算进度
        if stats['duplicate_files_total_size'] > 0:
            hash_progress = stats['hashed_size'] / stats['duplicate_files_total_size'] * 100
        else:
            hash_progress = 0
        
        console.print("  [dim]───────────────────────────────────────────────[/dim]")
        console.print("  ⏳ 哈希计算进度")
        console.print(f"  已计算 {format_size(stats['hashed_size'])} / {format_size(stats['duplicate_files_total_size'])}")
        console.print(f"  {print_progress_bar(hash_progress)} [bold]{hash_progress:.1f}%[/bold]")
        console.print()
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 重复组统计信息
        # ═══════════════════════════════════════════════════════════════════════════
        
        total_groups = stats['hashed_groups'] + stats['unhashed_groups']
        duplicate_rate = (stats['duplicate_files'] / stats['total_files'] * 100) if stats['total_files'] > 0 else 0
        deletable_files = stats['duplicate_files'] - stats['hashed_groups']
        
        console.print("[bold blue]📁 重复组统计信息[/bold blue]")
        console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
        console.print()
        console.print(f"  重复组总数          [bold]{total_groups:,}[/bold]")
        console.print(f"  组内文件总数        [bold]{stats['duplicate_files']:,}[/bold]")
        console.print(f"  已确认组            [bold green]{stats['hashed_groups']:,}[/bold green]")
        console.print(f"  待确认组            [bold yellow]{stats['unhashed_groups']:,}[/bold yellow]")
        console.print()
        
        # 组详情
        console.print("  [dim]───────────────────────────────────────────────[/dim]")
        console.print(f"  平均组大小          {format_size_colored(stats['avg_group_size'])}")
        console.print(f"  平均组文件数        [bold]{stats['avg_duplication']:.2f}[/bold] 个")
        avg_savable = stats['duplicate_size'] / stats['hashed_groups'] if stats['hashed_groups'] > 0 else 0
        console.print(f"  平均可释放空间      {format_size_colored(avg_savable)}")
        console.print(f"  重复率              [bold yellow]{duplicate_rate:.2f}%[/bold yellow]")
        console.print()
        
        # 组确认进度
        if total_groups > 0:
            group_progress = stats['hashed_groups'] / total_groups * 100
        else:
            group_progress = 0
        
        console.print("  [dim]───────────────────────────────────────────────[/dim]")
        console.print("  ⏳ 组确认进度")
        console.print(f"  已确认 {stats['hashed_groups']:,} / {total_groups:,} 组")
        console.print(f"  {print_progress_bar(group_progress)} [bold]{group_progress:.1f}%[/bold]")
        console.print()
        
        # 可释放空间
        console.print("  [dim]───────────────────────────────────────────────[/dim]")
        console.print("  💾 可释放空间")
        console.print(f"  可删除 [bold red]{deletable_files:,}[/bold red] 个文件，节省 [bold green]{format_size(stats['duplicate_size'])}[/bold green]")
        console.print()
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 类型和大小分析
        # ═══════════════════════════════════════════════════════════════════════════
        
        console.print("[bold blue]📊 类型和大小分析[/bold blue]")
        console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
        console.print()
        
        # 按扩展名 Top 5
        console.print("  📁 按扩展名 Top 5")
        if stats['top_extensions']:
            for ext_info in stats['top_extensions'][:5]:
                console.print(f"    {ext_info['extension']:<10} {ext_info['group_count']:>5} 组    可释放 {format_size_colored(ext_info['savable_space'])}")
        else:
            console.print("    暂无数据")
        console.print()
        
        # 按大小分布
        console.print("  [dim]───────────────────────────────────────────────[/dim]")
        console.print("  📏 按大小分布")
        size_order = ['< 1MB', '1MB - 10MB', '10MB - 100MB', '100MB - 1GB', '> 1GB']
        if stats['size_distribution']:
            for range_name in size_order:
                if range_name in stats['size_distribution']:
                    info = stats['size_distribution'][range_name]
                    console.print(f"    {range_name:<12} 可释放 {format_size_colored(info['savable_space'])}")
        else:
            console.print("    暂无数据")
        console.print()
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 其他信息
        # ═══════════════════════════════════════════════════════════════════════════
        
        console.print("[bold blue]📋 其他信息[/bold blue]")
        console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
        console.print()
        console.print(f"  数据库大小: {format_size_colored(stats['db_size'])}      跨磁盘重复组: [bold]{stats['cross_disk_groups']:,}[/bold] 个")
        console.print()

# 辅助函数
def _parse_size(size_str: str) -> int:
    """解析大小字符串（支持K/M/G单位）"""
    size_str = size_str.upper()
    if size_str.endswith('K'):
        return int(size_str[:-1]) * 1024
    elif size_str.endswith('M'):
        return int(size_str[:-1]) * 1024 * 1024
    elif size_str.endswith('G'):
        return int(size_str[:-1]) * 1024 * 1024 * 1024
    else:
        return int(size_str)

def _show_group_detail(group_id: int):
    """显示指定组的详细信息"""
    group = analyzer.get_group_details(group_id)

    if not group:
        typer.echo(f"错误: 找不到组ID: {group_id}")
        return

    # 格式化文件大小
    size = group['size']
    if size >= 1024 * 1024 * 1024:
        size_str = f"{size / 1024 / 1024 / 1024:.2f} GB"
    elif size >= 1024 * 1024:
        size_str = f"{size / 1024 / 1024:.2f} MB"
    elif size >= 1024:
        size_str = f"{size / 1024:.2f} KB"
    else:
        size_str = f"{size} B"

    # 格式化可释放空间
    savable = group['savable_space']
    if savable >= 1024 * 1024 * 1024:
        savable_str = f"{savable / 1024 / 1024 / 1024:.2f} GB"
    elif savable >= 1024 * 1024:
        savable_str = f"{savable / 1024 / 1024:.2f} MB"
    elif savable >= 1024:
        savable_str = f"{savable / 1024:.2f} KB"
    else:
        savable_str = f"{savable} B"

    # 哈希值显示（截短）
    hash_str = group['hash'] if group['hash'] else "未确认"
    if hash_str != "未确认" and len(hash_str) > 16:
        hash_str = hash_str[:16] + "..."

    typer.echo(f"\n组 #{group_id} | 大小: {size_str} | 扩展名: {group['extension'] or '无'} | 文件数: {group['file_count']} | 可释放: {savable_str} | 哈希: {hash_str}")
    typer.echo(f"{'=' * 100}")

    # 列出重复文件的绝对路径
    for i, file_info in enumerate(group['files'], 1):
        typer.echo(f"  {i}. {file_info['filepath']}")

    typer.echo(f"{'=' * 100}")
