import typer
import sqlite3
import os
from typing import Optional
from datetime import datetime
from rich.console import Console
from rich.table import Table
from commands.db import get_db_path

class DataViewer:
    """数据查看器 - 提供查询和展示重复文件数据的功能"""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or get_db_path()
        self.path_limit = None
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path, timeout=60.0, isolation_level='IMMEDIATE')
    
    def get_statistics(self):
        """获取统计信息
        
        返回全部组的统计和已确认哈希组的统计
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM files')
        total_files = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM duplicate_groups')
        total_groups = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM duplicate_groups WHERE Hash IS NOT NULL AND Hash != ''")
        hashed_groups = cursor.fetchone()[0]
        
        unhashed_groups = total_groups - hashed_groups
        
        cursor.execute('SELECT COUNT(*) FROM duplicate_files')
        total_duplicate_files = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM duplicate_files df
            INNER JOIN duplicate_groups dg ON df.Group_ID = dg.ID
            WHERE dg.Hash IS NOT NULL AND dg.Hash != ''
        ''')
        confirmed_duplicate_files = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM file_hash WHERE Hash IS NOT NULL AND Hash != ""')
        hashed_files = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM duplicate_files WHERE Filepath NOT IN (SELECT Filepath FROM file_hash)')
        unhashed_files = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(Size) FROM files')
        total_size = cursor.fetchone()[0] or 0
        
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
        savable_size = cursor.fetchone()[0] or 0
        
        cursor.execute('''
        SELECT SUM(f.Size) FROM file_hash fh
        INNER JOIN files f ON fh.Filepath = f.Filename
        WHERE fh.Hash IS NOT NULL AND fh.Hash != ""
        ''')
        hashed_size = cursor.fetchone()[0] or 0
        
        cursor.execute('''
        SELECT SUM(f.Size) FROM duplicate_files df
        INNER JOIN files f ON df.Filepath = f.Filename
        ''')
        duplicate_files_total_size = cursor.fetchone()[0] or 0
        
        cursor.execute('''
        SELECT AVG(file_count) FROM (
            SELECT COUNT(*) as file_count
            FROM duplicate_files df
            GROUP BY df.Group_ID
        )
        ''')
        avg_duplication = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT AVG(Size) FROM duplicate_groups')
        avg_group_size = cursor.fetchone()[0] or 0
        
        cursor.execute('''
        SELECT 
            UPPER(SUBSTR(f.Filename, 1, 2)) as disk,
            COUNT(*) as file_count
        FROM files f
        GROUP BY disk
        ORDER BY file_count DESC
        ''')
        disk_distribution = {}
        for disk, file_count in cursor.fetchall():
            disk_distribution[disk] = {'file_count': file_count}
        
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
        
        import os
        db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        
        conn.close()
        
        return {
            'total_files': total_files,
            'total_groups': total_groups,
            'hashed_groups': hashed_groups,
            'unhashed_groups': unhashed_groups,
            'total_duplicate_files': total_duplicate_files,
            'confirmed_duplicate_files': confirmed_duplicate_files,
            'hashed_files': hashed_files,
            'unhashed_files': unhashed_files,
            'total_size': total_size,
            'savable_size': savable_size,
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
    
    def get_groups_list(self, count=20, hash_only=True, min_size=None, max_size=None, extension=None, sort_by='size', page=1, page_size=20, disk=None):
        """获取重复文件组列表
        
        Args:
            count: 返回的组数量
            hash_only: 是否只返回已确认哈希值的组
            min_size: 最小文件大小（字节）
            max_size: 最大文件大小（字节）
            extension: 文件扩展名过滤
            sort_by: 排序方式（size/count/path/ext/hash）
            page: 页码
            page_size: 每页大小
            disk: 按磁盘过滤
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
        
        if disk:
            # 按磁盘过滤（Windows: 盘符，如 C:, D: 等）
            conditions.append("UPPER(SUBSTR(f.Filename, 1, 2)) = ?")
            params.append(disk.upper())
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        # 构建ORDER BY
        if sort_by == 'size':
            order_by = "ORDER BY (COUNT(*) - 1) * dg.Size DESC"
        elif sort_by == 'count':
            order_by = "ORDER BY COUNT(*) DESC"
        elif sort_by == 'path':
            order_by = "ORDER BY MIN(f.Filename)"
        elif sort_by == 'ext':
            order_by = "ORDER BY dg.Extension, (COUNT(*) - 1) * dg.Size DESC"
        elif sort_by == 'hash':
            order_by = "ORDER BY dg.Hash"
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
            LIMIT ? OFFSET ?
            '''
        else:
            query = f'''
            SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count, dg.Hash
            FROM duplicate_groups dg
            INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
            {where_clause}
            GROUP BY dg.ID
            {order_by}
            LIMIT ? OFFSET ?
            '''
        
        # 计算偏移量
        offset = (page - 1) * page_size
        params.extend([page_size, offset])
        cursor.execute(query, params)
        groups = cursor.fetchall()
        
        # 获取总记录数
        count_query = f'''
        SELECT COUNT(DISTINCT dg.ID)
        FROM duplicate_groups dg
        INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
        {where_clause}
        '''
        cursor.execute(count_query, params[:-2])  # 移除 LIMIT 和 OFFSET 参数
        total_count = cursor.fetchone()[0]
        
        result = []
        for group_id, size, ext, file_count, hash_val in groups:
            # 获取组内前3个文件作为预览
            cursor.execute('''
            SELECT f.Filename
            FROM duplicate_files df
            INNER JOIN files f ON df.Filepath = f.Filename
            WHERE df.Group_ID = ?
            ORDER BY f.Filename
            LIMIT 3
            ''', (group_id,))
            files = [f[0] for f in cursor.fetchall()]
            
            # 智能截断文件路径
            truncated_files = []
            for filepath in files:
                if len(filepath) > 50:
                    # 保留文件名和扩展名
                    filename = os.path.basename(filepath)
                    if len(filename) > 30:
                        name_part, ext_part = os.path.splitext(filename)
                        if ext_part:
                            truncated_name = name_part[:27] + "..." + ext_part
                        else:
                            truncated_name = filename[:30] + "..."
                        truncated_files.append(".../" + truncated_name)
                    else:
                        # 保留完整文件名，截断路径
                        path_part = os.path.dirname(filepath)
                        if len(path_part) > 20:
                            truncated_path = "..." + path_part[-17:]
                            truncated_files.append(truncated_path + "/" + filename)
                        else:
                            truncated_files.append(filepath)
                else:
                    truncated_files.append(filepath)
            
            result.append({
                'group_id': group_id,
                'size': size,
                'extension': ext,
                'file_count': file_count,
                'savable_space': (file_count - 1) * size,
                'hash': hash_val,
                'files': truncated_files
            })
        
        conn.close()
        return {
            'groups': result,
            'total_count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size
        }
    
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

app = typer.Typer(
    name="show",
    help="[bold blue]📊 显示信息[/bold blue]",
    rich_markup_mode=True
)
analyzer = DataViewer()

@app.command()
def groups(
    top: int = 20,
    unconfirmed: bool = False,
    min_size: Optional[str] = None,
    max_size: Optional[str] = None,
    extension: Optional[str] = None,
    sort: str = "size",
    detail: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    disk: Optional[str] = None
):
    """[bold]显示重复文件组列表[/bold]
    
    [dim]显示已确认的重复文件组，按大小排序[/dim]
    
    [dim]排序选项: size (大小), count (数量), path (路径), ext (扩展名), hash (哈希值)[/dim]
    """
    console = Console()
    hash_only = not unconfirmed
    
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
    
    parsed_min_size = _parse_size(min_size) if min_size else None
    parsed_max_size = _parse_size(max_size) if max_size else None
    
    if detail is not None:
        _show_group_detail(detail)
        return
    
    # 获取组列表
    result = analyzer.get_groups_list(
        hash_only=hash_only,
        min_size=parsed_min_size,
        max_size=parsed_max_size,
        extension=extension,
        sort_by=sort,
        page=page,
        page_size=page_size,
        disk=disk
    )
    
    groups = result['groups']
    total_count = result['total_count']
    current_page = result['page']
    current_page_size = result['page_size']
    total_pages = result['total_pages']
    
    console.print()
    console.print("[bold blue]📁 重复文件组列表[/bold blue]")
    console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
    console.print()
    
    # 显示统计信息
    if total_count > 0:
        # 计算总可释放空间和平均文件数
        total_savable = sum(group['savable_space'] for group in groups)
        avg_file_count = sum(group['file_count'] for group in groups) / len(groups) if groups else 0
        
        console.print(f"  [bold]统计信息:[/bold] 共 [green]{total_count:,}[/green] 个组 | 总可释放空间: {format_size_colored(total_savable)} | 平均文件数: [bold]{avg_file_count:.1f}[/bold] 个/组")
        console.print(f"  [bold]分页信息:[/bold] 第 [green]{current_page}[/green] / {total_pages} 页 | 每页显示 [green]{current_page_size}[/green] 个组")
        console.print()
    
    if not groups:
        console.print("  [dim]没有找到符合条件的重复文件组[/dim]")
    else:
        # 创建表格
        table = Table(show_header=True, header_style="bold blue", border_style="dim")
        table.add_column("组ID", width=8, style="cyan")
        table.add_column("大小", width=12, style="bold")
        table.add_column("扩展名", width=10)
        table.add_column("文件数", width=8, justify="center")
        table.add_column("可释放空间", width=15)
        table.add_column("哈希状态", width=12)
        table.add_column("示例文件", width=50)
        
        for group in groups:
            # 格式化哈希状态
            if group['hash']:
                hash_status = "✅ 已确认"
            else:
                hash_status = "⏳ 未确认"
            
            # 格式化文件预览
            files_preview = "\n".join(group['files'][:3])
            if len(group['files']) > 3:
                files_preview += f"\n... 还有 {len(group['files']) - 3} 个文件"
            
            table.add_row(
                str(group['group_id']),
                format_size_colored(group['size']),
                group['extension'] or "(无)",
                str(group['file_count']),
                format_size_colored(group['savable_space']),
                hash_status,
                files_preview
            )
        
        console.print(table)
        console.print()
        
        # 显示分页导航
        if total_pages > 1:
            console.print("  [bold]分页导航:[/bold]")
            console.print(f"    使用 --page 1-{total_pages} 切换页码")
            console.print(f"    使用 --page-size N 设置每页显示数量")
            console.print()
    
    console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
    console.print()
    console.print("  [bold]提示:[/bold]")
    console.print("    --sort size/count/path/ext/hash 切换排序方式")
    console.print("    --min-size/--max-size 按大小过滤")
    console.print("    --extension 按扩展名过滤")
    console.print("    --disk 按磁盘过滤（如 C:, D: 等）")
    console.print("    --page/--page-size 分页控制")
    console.print("    --detail <组ID> 查看详细信息")
    console.print()

@app.command()
def files(
    pattern: str,
    all: bool = False,
    hash: bool = False,
    limit: int = 100
):
    """[bold]查询文件，支持路径或模式[/bold]
    
    [dim]搜索重复文件组或已索引的文件[/dim]
    """
    console = Console()
    show_all = all
    show_hash = hash
    
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
    
    has_wildcard = '*' in pattern or '?' in pattern
    
    is_full_path = False
    if not has_wildcard:
        if len(pattern) >= 2 and pattern[1] == ':' and (pattern[0].isalpha()):
            is_full_path = True
        elif pattern.startswith('\\') or pattern.startswith('/'):
            is_full_path = True
    
    if has_wildcard or not is_full_path:
        hash_only = not show_all
        groups = analyzer.filter_by_pattern(pattern, hash_only=hash_only)
        
        unhashed_count = 0
        if not show_all:
            all_groups = analyzer.filter_by_pattern(pattern, hash_only=False)
            unhashed_count = len(all_groups) - len(groups)
        
        console.print()
        console.print(f"[bold blue]🔍 文件搜索结果（模式: {pattern}）[/bold blue]")
        console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
        console.print()
        
        if not groups:
            console.print("  [dim]没有找到匹配的文件[/dim]")
            if unhashed_count > 0:
                console.print()
                console.print(f"  [yellow]提示: 有 {unhashed_count} 个组因未计算哈希值而被隐藏[/yellow]")
                console.print("  [dim]使用 --all 选项显示所有组（包括未计算哈希的）[/dim]")
        else:
            console.print(f"  找到 [bold green]{len(groups)}[/bold green] 个匹配的重复文件组")
            console.print()
            for i, group in enumerate(groups[:limit], 1):
                console.print(f"  [cyan]{i}. 组ID: {group['group_id']}[/cyan]")
                console.print(f"    文件大小      {format_size_colored(group['size'])}")
                console.print(f"    文件扩展名    [bold]{group['extension']}[/bold]")
                console.print(f"    文件数量      [bold]{group['file_count']}[/bold] 个")
                console.print("    匹配的文件:")
                for j, filepath in enumerate(group['matched_files'][:5], 1):
                    console.print(f"      [dim]{j}.[/dim] {filepath}")
                if len(group['matched_files']) > 5:
                    console.print(f"      [dim]... 还有 {len(group['matched_files']) - 5} 个匹配文件[/dim]")
                console.print()
            
            if len(groups) > limit:
                console.print(f"  [dim]... 还有 {len(groups) - limit} 个组未显示（使用 --limit {limit + 20} 显示更多）[/dim]")
                console.print()
            
            if unhashed_count > 0:
                console.print(f"  [yellow]提示: 还有 {unhashed_count} 个组因未计算哈希值而被隐藏[/yellow]")
                console.print("  [dim]使用 --all 选项显示所有组（包括未计算哈希的）[/dim]")
        
        console.print()
        console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
        console.print()
    else:
        if show_all:
            conn = analyzer.get_connection()
            cursor = conn.cursor()
            
            normalized_pattern = pattern.replace('\\', '/').lower()
            
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
            
            console.print()
            console.print(f"[bold blue]📂 路径 {pattern} 下已索引的文件[/bold blue]")
            console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
            console.print()
            
            if not files:
                console.print("  [dim]没有找到已索引的文件[/dim]")
            else:
                for i, (filename, size, modified, hash_val, created_at) in enumerate(files, 1):
                    hash_status = "[green]已计算[/green]" if hash_val else "[yellow]未计算[/yellow]"
                    console.print(f"  [dim]{i}.[/dim] {filename}")
                    console.print(f"    大小: {format_size_colored(size)}    修改时间: [dim]{modified}[/dim]    哈希状态: {hash_status}")
                    if show_hash and hash_val:
                        console.print(f"    哈希值: [dim]{hash_val[:16]}...[/dim]")
                        if created_at:
                            console.print(f"    计算时间: [dim]{created_at}[/dim]")
                    console.print()
            
            if len(files) >= limit:
                console.print(f"  [dim]... 还有更多文件（仅显示前{limit}个，使用 --limit {limit + 100} 显示更多）[/dim]")
            
            console.print()
            console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
            console.print()
        else:
            hash_only = not show_all
            groups = analyzer.get_groups_by_path(pattern, hash_only=hash_only)
            
            unhashed_count = 0
            if not show_all:
                all_groups = analyzer.get_groups_by_path(pattern, hash_only=False)
                unhashed_count = len(all_groups) - len(groups)
            
            console.print()
            console.print(f"[bold blue]📂 路径 {pattern} 下的重复文件[/bold blue]")
            console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
            console.print()
            
            if not groups:
                console.print("  [dim]没有找到重复文件[/dim]")
                if unhashed_count > 0:
                    console.print()
                    console.print(f"  [yellow]提示: 有 {unhashed_count} 个组因未计算哈希值而被隐藏[/yellow]")
                    console.print("  [dim]使用 --all 选项显示所有组（包括未计算哈希的）[/dim]")
            else:
                console.print(f"  找到 [bold green]{len(groups)}[/bold green] 个重复文件组")
                console.print()
                for i, group in enumerate(groups[:limit], 1):
                    console.print(f"  [cyan]{i}. 组ID: {group['group_id']}[/cyan]")
                    console.print(f"    文件大小      {format_size_colored(group['size'])}")
                    console.print(f"    文件扩展名    [bold]{group['extension']}[/bold]")
                    console.print(f"    文件数量      [bold]{group['file_count']}[/bold] 个")
                    console.print("    包含的文件:")
                    for j, filepath in enumerate(group['files'][:5], 1):
                        console.print(f"      [dim]{j}.[/dim] {filepath}")
                    if len(group['files']) > 5:
                        console.print(f"      [dim]... 还有 {len(group['files']) - 5} 个文件[/dim]")
                    console.print()
                
                if len(groups) > limit:
                    console.print(f"  [dim]... 还有 {len(groups) - limit} 个组未显示（使用 --limit {limit + 20} 显示更多）[/dim]")
                    console.print()
                
                if unhashed_count > 0:
                    console.print(f"  [yellow]提示: 还有 {unhashed_count} 个组因未计算哈希值而被隐藏[/yellow]")
                    console.print("  [dim]使用 --all 选项显示所有组（包括未计算哈希的）[/dim]")
            
            console.print()
            console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
            console.print()

@app.command()
def hash(hash_value: str):
    """[bold]显示指定哈希值的所有文件[/bold]
    
    [dim]根据哈希值查找所有重复文件[/dim]
    """
    console = Console()
    files = analyzer.get_duplicate_details(hash_value)
    
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
    
    console.print()
    console.print(f"[bold blue]🔑 哈希值 {hash_value[:16]}... 的重复文件[/bold blue]")
    console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
    console.print()
    
    if not files:
        console.print("  [dim]没有找到文件[/dim]")
    else:
        for i, file_info in enumerate(files, 1):
            console.print(f"  [cyan]{i}. 文件路径[/cyan]")
            console.print(f"    {file_info['filepath']}")
            console.print("  [dim]───────────────────────────────────────────────[/dim]")
            console.print(f"    磁盘        [bold]{file_info['disk']}[/bold]")
            console.print(f"    大小        {format_size_colored(file_info['size'])}")
            console.print(f"    修改时间    [dim]{file_info['modified']}[/dim]")
            console.print(f"    哈希值      [dim]{file_info['hash'][:16]}...[/dim]")
            console.print(f"    计算时间    [dim]{file_info['created_at']}[/dim]")
            console.print()
    
    console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
    console.print()

@app.command()
def stats(
    by_extension: bool = False,
    by_size_range: bool = False,
    by_date: bool = False
):
    """[bold]显示统计分析[/bold]
    
    [dim]显示文件、重复组和类型分析的统计信息[/dim]
    """
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
        stats = analyzer.get_statistics()
        
        console.print()
        
        console.print("[bold blue]📄 文件统计信息[/bold blue]")
        console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
        console.print()
        console.print(f"  扫描文件数          [bold]{stats['total_files']:,}[/bold]")
        console.print(f"  文件总大小          {format_size_colored(stats['total_size'])}")
        console.print(f"  已计算哈希文件      [bold green]{stats['hashed_files']:,}[/bold green]")
        console.print(f"  待计算哈希文件      [bold yellow]{stats['unhashed_files']:,}[/bold yellow]")
        console.print()
        
        console.print("  [dim]───────────────────────────────────────────────[/dim]")
        console.print("  💿 磁盘分布")
        if stats['disk_distribution']:
            for disk, info in stats['disk_distribution'].items():
                console.print(f"    {disk}    {info['file_count']:,} 个文件")
        else:
            console.print("    暂无数据")
        console.print()
        
        if stats['duplicate_files_total_size'] > 0:
            hash_progress = stats['hashed_size'] / stats['duplicate_files_total_size'] * 100
        else:
            hash_progress = 0
        
        console.print("  [dim]───────────────────────────────────────────────[/dim]")
        console.print("  ⏳ 哈希计算进度")
        console.print(f"  已计算 {format_size(stats['hashed_size'])} / {format_size(stats['duplicate_files_total_size'])}")
        console.print(f"  {print_progress_bar(hash_progress)} [bold]{hash_progress:.1f}%[/bold]")
        console.print()
        
        duplicate_rate = (stats['total_duplicate_files'] / stats['total_files'] * 100) if stats['total_files'] > 0 else 0
        deletable_files = stats['confirmed_duplicate_files'] - stats['hashed_groups']
        
        console.print("[bold blue]📁 重复组统计信息[/bold blue]")
        console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
        console.print()
        console.print(f"  重复组总数          [bold]{stats['total_groups']:,}[/bold]")
        console.print(f"  组内文件总数        [bold]{stats['total_duplicate_files']:,}[/bold]")
        console.print(f"  已确认组            [bold green]{stats['hashed_groups']:,}[/bold green]")
        console.print(f"  待确认组            [bold yellow]{stats['unhashed_groups']:,}[/bold yellow]")
        console.print()
        
        console.print("  [dim]───────────────────────────────────────────────[/dim]")
        console.print(f"  平均组大小          {format_size_colored(stats['avg_group_size'])}")
        console.print(f"  平均组文件数        [bold]{stats['avg_duplication']:.2f}[/bold] 个")
        avg_savable = stats['savable_size'] / stats['hashed_groups'] if stats['hashed_groups'] > 0 else 0
        console.print(f"  平均可释放空间      {format_size_colored(avg_savable)}")
        console.print(f"  重复率              [bold yellow]{duplicate_rate:.2f}%[/bold yellow]")
        console.print()
        
        if stats['total_groups'] > 0:
            group_progress = stats['hashed_groups'] / stats['total_groups'] * 100
        else:
            group_progress = 0
        
        console.print("  [dim]───────────────────────────────────────────────[/dim]")
        console.print("  ⏳ 组确认进度")
        console.print(f"  已确认 {stats['hashed_groups']:,} / {stats['total_groups']:,} 组")
        console.print(f"  {print_progress_bar(group_progress)} [bold]{group_progress:.1f}%[/bold]")
        console.print()
        
        console.print("  [dim]───────────────────────────────────────────────[/dim]")
        console.print("  💾 可释放空间（已确认组）")
        console.print(f"  可删除 [bold red]{deletable_files:,}[/bold red] 个文件，节省 [bold green]{format_size(stats['savable_size'])}[/bold green]")
        console.print()
        
        console.print("[bold blue]📊 类型和大小分析[/bold blue]")
        console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
        console.print()
        
        console.print("  📁 按扩展名 Top 5（已确认组）")
        if stats['top_extensions']:
            for ext_info in stats['top_extensions'][:5]:
                console.print(f"    {ext_info['extension']:<10} {ext_info['group_count']:>5} 组    可释放 {format_size_colored(ext_info['savable_space'])}")
        else:
            console.print("    暂无数据")
        console.print()
        
        console.print("  [dim]───────────────────────────────────────────────[/dim]")
        console.print("  📏 按大小分布（已确认组）")
        size_order = ['< 1MB', '1MB - 10MB', '10MB - 100MB', '100MB - 1GB', '> 1GB']
        if stats['size_distribution']:
            for range_name in size_order:
                if range_name in stats['size_distribution']:
                    info = stats['size_distribution'][range_name]
                    console.print(f"    {range_name:<12} 可释放 {format_size_colored(info['savable_space'])}")
        else:
            console.print("    暂无数据")
        console.print()
        
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
    console = Console()
    group = analyzer.get_group_details(group_id)

    if not group:
        console.print(f"[red]错误: 找不到组ID: {group_id}[/red]")
        return

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

    console.print()
    console.print(f"[bold blue]📁 组 #{group_id} 详细信息[/bold blue]")
    console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
    console.print()
    console.print(f"  文件大小      {format_size_colored(group['size'])}")
    console.print(f"  文件扩展名    [bold]{group['extension'] or '无'}[/bold]")
    console.print(f"  文件数量      [bold]{group['file_count']}[/bold] 个")
    console.print(f"  可释放空间    {format_size_colored(group['savable_space'])}")
    
    if group['hash']:
        console.print(f"  哈希值        [dim]{group['hash'][:16]}...[/dim]")
    else:
        console.print(f"  哈希值        [yellow]未确认[/yellow]")
    
    console.print()
    console.print("  [dim]───────────────────────────────────────────────[/dim]")
    console.print("  📄 包含的文件")
    console.print()
    
    for i, file_info in enumerate(group['files'], 1):
        console.print(f"    [dim]{i}.[/dim] {file_info['filepath']}")
    
    console.print()
    console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
    console.print()
