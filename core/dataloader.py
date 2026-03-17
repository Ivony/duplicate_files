import os
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any

from core.database import get_db_path


class DataLoader:
    """数据加载器 - 从数据库加载重复文件数据"""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or get_db_path()
        self.path_limit = None
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path, timeout=60.0, isolation_level='IMMEDIATE')
    
    def get_statistics(self) -> Dict[str, Any]:
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
    
    def get_groups_list(self, count=20, hash_only=True, min_size=None, max_size=None, extension=None, sort_by='size', page=1, page_size=20, disk=None, hash_value=None) -> Dict[str, Any]:
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
            hash_value: 按哈希值过滤
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
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
            conditions.append("UPPER(SUBSTR(f.Filename, 1, 2)) = ?")
            params.append(disk.upper())
        
        if hash_value:
            conditions.append("dg.Hash LIKE ?")
            params.append(f"{hash_value}%")
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
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
        
        offset = (page - 1) * page_size
        params.extend([page_size, offset])
        cursor.execute(query, params)
        groups = cursor.fetchall()
        
        count_query = f'''
        SELECT COUNT(DISTINCT dg.ID)
        FROM duplicate_groups dg
        INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
        {where_clause}
        '''
        cursor.execute(count_query, params[:-2])
        total_count = cursor.fetchone()[0]
        
        result = []
        for group_id, size, ext, file_count, hash_val in groups:
            cursor.execute('''
            SELECT f.Filename
            FROM duplicate_files df
            INNER JOIN files f ON df.Filepath = f.Filename
            WHERE df.Group_ID = ?
            ORDER BY f.Filename
            LIMIT 3
            ''', (group_id,))
            files = [f[0] for f in cursor.fetchall()]
            
            truncated_files = []
            for filepath in files:
                if len(filepath) > 50:
                    filename = os.path.basename(filepath)
                    if len(filename) > 30:
                        name_part, ext_part = os.path.splitext(filename)
                        if ext_part:
                            truncated_name = name_part[:27] + "..." + ext_part
                        else:
                            truncated_name = filename[:30] + "..."
                        truncated_files.append(".../" + truncated_name)
                    else:
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
    
    def get_groups_count(self, hash_only=True, min_size=None, max_size=None, extension=None, disk=None, hash_value=None) -> int:
        """快速获取重复文件组总数
        
        Args:
            hash_only: 是否只返回已确认哈希值的组
            min_size: 最小文件大小（字节）
            max_size: 最大文件大小（字节）
            extension: 文件扩展名过滤
            disk: 按磁盘过滤
            hash_value: 按哈希值过滤
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
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
            conditions.append("UPPER(SUBSTR(f.Filename, 1, 2)) = ?")
            params.append(disk.upper())
        
        if hash_value:
            conditions.append("dg.Hash LIKE ?")
            params.append(f"{hash_value}%")
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        if self.path_limit:
            count_query = f'''
            SELECT COUNT(DISTINCT dg.ID)
            FROM duplicate_groups dg
            INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
            INNER JOIN files f ON df.Filepath = f.Filename
            {where_clause}
            '''
        else:
            count_query = f'''
            SELECT COUNT(DISTINCT dg.ID)
            FROM duplicate_groups dg
            INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
            {where_clause}
            '''
        
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        conn.close()
        
        return total_count
    
    def get_groups_batch(self, start_idx=0, count=20, hash_only=True, min_size=None, max_size=None, extension=None, sort_by='size', disk=None, hash_value=None) -> List[Dict[str, Any]]:
        """按需获取重复文件组数据块
        
        Args:
            start_idx: 起始索引
            count: 获取数量
            hash_only: 是否只返回已确认哈希值的组
            min_size: 最小文件大小（字节）
            max_size: 最大文件大小（字节）
            extension: 文件扩展名过滤
            sort_by: 排序方式
            disk: 按磁盘过滤
            hash_value: 按哈希值过滤
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
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
            conditions.append("UPPER(SUBSTR(f.Filename, 1, 2)) = ?")
            params.append(disk.upper())
        
        if hash_value:
            conditions.append("dg.Hash LIKE ?")
            params.append(f"{hash_value}%")
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
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
        
        params.extend([count, start_idx])
        cursor.execute(query, params)
        groups = cursor.fetchall()
        
        result = []
        for group_id, size, ext, file_count, hash_val in groups:
            cursor.execute('''
            SELECT f.Filename
            FROM duplicate_files df
            INNER JOIN files f ON df.Filepath = f.Filename
            WHERE df.Group_ID = ?
            ORDER BY f.Filename
            LIMIT 3
            ''', (group_id,))
            files = [f[0] for f in cursor.fetchall()]
            
            truncated_files = []
            for filepath in files:
                if len(filepath) > 50:
                    filename = os.path.basename(filepath)
                    if len(filename) > 30:
                        name_part, ext_part = os.path.splitext(filename)
                        if ext_part:
                            truncated_name = name_part[:27] + "..." + ext_part
                        else:
                            truncated_name = filename[:30] + "..."
                        truncated_files.append(".../" + truncated_name)
                    else:
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
        return result
    
    def get_group_details(self, group_id) -> Optional[Dict[str, Any]]:
        """获取指定组的详细信息
        
        Args:
            group_id: 组ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
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
    
    def filter_by_pattern(self, pattern, hash_only=True) -> List[Dict[str, Any]]:
        """使用通配符模式筛选重复文件组
        
        Args:
            pattern: 筛选表达式，支持通配符如 *.mp4, E:/Downloads/*.mp4
            hash_only: 是否只返回已确认哈希值的组（Hash字段不为空）
        """
        import fnmatch
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        hash_condition = "WHERE dg.Hash IS NOT NULL AND dg.Hash != ''" if hash_only else "WHERE 1=1"
        
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
        
        normalized_pattern = pattern.replace('\\', '/').lower()
        
        result = []
        for group_id, size, extension, file_count, hash_val in groups:
            cursor.execute('''
            SELECT f.Filename
            FROM duplicate_files df
            INNER JOIN files f ON df.Filepath = f.Filename
            WHERE df.Group_ID = ?
            ''', (group_id,))
            
            files = cursor.fetchall()
            file_paths = [f[0] for f in files]
            
            matched_files = []
            for filepath in file_paths:
                normalized_path = filepath.replace('\\', '/').lower()
                filename = os.path.basename(normalized_path)
                
                if fnmatch.fnmatch(filename, normalized_pattern):
                    matched_files.append(filepath)
                elif fnmatch.fnmatch(normalized_path, normalized_pattern):
                    matched_files.append(filepath)
                else:
                    path_parts = normalized_path.split('/')
                    
                    for part in path_parts:
                        if fnmatch.fnmatch(part, normalized_pattern):
                            matched_files.append(filepath)
                            break
                    
                    if normalized_pattern in normalized_path:
                        matched_files.append(filepath)
            
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
    
    def get_groups_by_path(self, path_prefix, hash_only=True) -> List[Dict[str, Any]]:
        """获取指定路径下的重复文件组
        
        Args:
            path_prefix: 路径前缀
            hash_only: 是否只返回已确认哈希值的组（Hash字段不为空）
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        normalized_prefix = path_prefix.replace('\\', '/').lower()
        
        hash_condition = "AND dg.Hash IS NOT NULL AND dg.Hash != ''" if hash_only else ""
        
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
            
            cursor.execute(f'''
            SELECT f.Filename
            FROM duplicate_files df
            INNER JOIN files f ON df.Filepath = f.Filename
            WHERE df.Group_ID = ? AND LOWER(REPLACE(f.Filename, '\\\\', '/')) LIKE ? {hash_condition}
            ORDER BY f.Filename
            ''', (group_id, f"{normalized_prefix}%"))
            
            files = [f[0] for f in cursor.fetchall()]
            
            if files:
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
    
    def get_duplicate_details(self, hash_value) -> List[Dict[str, Any]]:
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
            
            disk = os.path.splitdrive(filepath)[0] if os.path.splitdrive(filepath)[0] else '未知'
            
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

    def get_stats_by_extension(self) -> Dict[str, int]:
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
    
    def get_stats_by_size_range(self) -> Dict[str, int]:
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
    
    def get_stats_by_date(self) -> Dict[str, int]:
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
