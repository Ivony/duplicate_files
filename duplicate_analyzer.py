import sqlite3
import os

class DuplicateAnalyzer:
    def __init__(self, db_path='file_index.db'):
        self.db_path = db_path
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
        
        # 构建基础查询条件
        hash_condition = "WHERE dg.Hash IS NOT NULL AND dg.Hash != ''" if hash_only else ""
        
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
        
        # 计算总大小
        cursor.execute('SELECT SUM(Size) FROM files')
        total_size = cursor.fetchone()[0] or 0
        
        # 计算重复文件总大小
        if hash_only:
            cursor.execute('''
            SELECT SUM(duplicate_size)
            FROM (
                SELECT (COUNT(*) - 1) * f.Size as duplicate_size
                FROM duplicate_files df
                INNER JOIN files f ON df.Filepath = f.Filename
                INNER JOIN duplicate_groups dg ON df.Group_ID = dg.ID
                WHERE dg.Hash IS NOT NULL AND dg.Hash != ''
                GROUP BY df.Group_ID
            )
            ''')
        else:
            cursor.execute('''
            SELECT SUM(duplicate_size)
            FROM (
                SELECT (COUNT(*) - 1) * f.Size as duplicate_size
                FROM duplicate_files df
                INNER JOIN files f ON df.Filepath = f.Filename
                GROUP BY df.Group_ID
            )
            ''')
        duplicate_size = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_files': total_files,
            'duplicate_groups': duplicate_groups,
            'duplicate_files': duplicate_files,
            'hashed_files': hashed_files,
            'unhashed_files': unhashed_files,
            'total_size': total_size,
            'duplicate_size': duplicate_size
        }
    
    def get_top_groups(self, count=20, hash_only=True):
        """获取最大的重复文件组
        
        Args:
            count: 返回的组数量
            hash_only: 是否只返回已确认哈希值的组（Hash字段不为空）
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if hash_only:
            # 只返回已确认哈希值的组
            if self.path_limit:
                cursor.execute('''
                SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count, dg.Hash
                FROM duplicate_groups dg
                INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
                INNER JOIN files f ON df.Filepath = f.Filename
                WHERE f.Filename LIKE ? AND dg.Hash IS NOT NULL AND dg.Hash != ''
                GROUP BY dg.ID
                ORDER BY (COUNT(*) - 1) * dg.Size DESC
                LIMIT ?
                ''', (f"{self.path_limit}%", count))
            else:
                cursor.execute('''
                SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count, dg.Hash
                FROM duplicate_groups dg
                INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
                WHERE dg.Hash IS NOT NULL AND dg.Hash != ''
                GROUP BY dg.ID
                ORDER BY (COUNT(*) - 1) * dg.Size DESC
                LIMIT ?
                ''', (count,))
        else:
            # 返回所有组（包括未确认哈希值的）
            if self.path_limit:
                cursor.execute('''
                SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count, dg.Hash
                FROM duplicate_groups dg
                INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
                INNER JOIN files f ON df.Filepath = f.Filename
                WHERE f.Filename LIKE ?
                GROUP BY dg.ID
                ORDER BY (COUNT(*) - 1) * dg.Size DESC
                LIMIT ?
                ''', (f"{self.path_limit}%", count))
            else:
                cursor.execute('''
                SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count, dg.Hash
                FROM duplicate_groups dg
                INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
                GROUP BY dg.ID
                ORDER BY (COUNT(*) - 1) * dg.Size DESC
                LIMIT ?
                ''', (count,))
        
        groups = cursor.fetchall()
        
        top_groups = []
        for group_id, size, extension, file_count, hash_val in groups:
            # 获取该组的文件列表
            if self.path_limit:
                cursor.execute('''
                SELECT f.Filename, f.Modified, fh.Hash
                FROM duplicate_files df
                INNER JOIN files f ON df.Filepath = f.Filename
                LEFT JOIN file_hash fh ON df.Filepath = fh.Filepath
                WHERE df.Group_ID = ? AND f.Filename LIKE ?
                ORDER BY f.Modified DESC
                LIMIT 10
                ''', (group_id, f"{self.path_limit}%"))
            else:
                cursor.execute('''
                SELECT f.Filename, f.Modified, fh.Hash
                FROM duplicate_files df
                INNER JOIN files f ON df.Filepath = f.Filename
                LEFT JOIN file_hash fh ON df.Filepath = fh.Filepath
                WHERE df.Group_ID = ?
                ORDER BY f.Modified DESC
                LIMIT 10
                ''', (group_id,))
            
            files = cursor.fetchall()
            disk_files = [(os.path.splitdrive(filepath)[0].upper(), filepath) for filepath, _, _ in files]
            
            top_groups.append({
                'group_id': group_id,
                'size': size,
                'extension': extension,
                'file_count': file_count,
                'group_size': size * file_count,
                'savable_space': (file_count - 1) * size,
                'files': disk_files,
                'total_files': len(files),
                'hash': hash_val
            })
        
        conn.close()
        return top_groups
    
    def get_duplicate_details(self, hash_value):
        """获取特定哈希值的重复文件详情"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT f.Filename, f.Size, f.Modified, fh.Hash, fh.created_at
        FROM files f
        LEFT JOIN file_hash fh ON f.Filename = fh.Filepath
        WHERE fh.Hash = ?
        ORDER BY f.Modified DESC
        ''', (hash_value,))
        
        files = cursor.fetchall()
        conn.close()
        
        if not files:
            print(f"没有找到哈希值为 {hash_value} 的文件")
            return []
        
        result = []
        for filename, size, modified, hash_val, created_at in files:
            disk = os.path.splitdrive(filename)[0].upper()
            result.append({
                'filepath': filename,
                'disk': disk,
                'size': size,
                'modified': modified,
                'hash': hash_val,
                'created_at': created_at
            })
        
        return result
    
    def filter_duplicates(self, filter_type, value, hash_only=True):
        """过滤重复文件
        
        Args:
            filter_type: 过滤类型（extension/size/path）
            value: 过滤值
            hash_only: 是否只返回已确认哈希值的组（Hash字段不为空）
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 构建基础查询条件
        hash_condition = "AND dg.Hash IS NOT NULL AND dg.Hash != ''" if hash_only else ""
        
        if filter_type == 'extension':
            cursor.execute(f'''
            SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count, dg.Hash
            FROM duplicate_groups dg
            WHERE dg.Extension = ? {hash_condition}
            ORDER BY (COUNT(*) - 1) * dg.Size DESC
            ''', (value,))
        elif filter_type == 'size':
            # 支持比较操作符，如 >1000000, <1000000, =1000000
            if value.startswith('>') or value.startswith('<'):
                operator = value[0]
                size_value = int(value[1:])
                cursor.execute(f'''
                SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count, dg.Hash
                FROM duplicate_groups dg
                WHERE dg.Size {operator} ? {hash_condition}
                ORDER BY (COUNT(*) - 1) * dg.Size DESC
                ''', (size_value,))
            else:
                cursor.execute(f'''
                SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count, dg.Hash
                FROM duplicate_groups dg
                WHERE dg.Size = ? {hash_condition}
                ORDER BY (COUNT(*) - 1) * dg.Size DESC
                ''', (int(value),))
        elif filter_type == 'path':
            cursor.execute(f'''
            SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count, dg.Hash
            FROM duplicate_groups dg
            INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
            INNER JOIN files f ON df.Filepath = f.Filename
            WHERE f.Filename LIKE ? {hash_condition}
            GROUP BY dg.ID
            ORDER BY (COUNT(*) - 1) * dg.Size DESC
            ''', (f"{value}%",))
        else:
            conn.close()
            print(f"未知的过滤类型: {filter_type}")
            return []
        
        groups = cursor.fetchall()
        conn.close()
        
        result = []
        for group_id, size, extension, file_count, hash_val in groups:
            result.append({
                'group_id': group_id,
                'size': size,
                'extension': extension,
                'file_count': file_count,
                'group_size': size * file_count,
                'savable_space': (file_count - 1) * size,
                'hash': hash_val
            })
        
        return result
    
    def filter_by_pattern(self, pattern, hash_only=True):
        """使用通配符模式筛选重复文件组
        
        Args:
            pattern: 筛选表达式，支持通配符如 *.mp4, E:\\Downloads\\*.mp4
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
        
        # 规范化模式：统一使用正斜杠进行匹配，并转为小写
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
                # 规范化文件路径（转为小写）
                normalized_path = filepath.replace('\\', '/').lower()
                filename = os.path.basename(normalized_path)
                
                # 检查文件名是否匹配（如果是纯文件名模式如 *.mp4）
                # 或者完整路径是否匹配（如果是路径模式如 E:/Downloads/*.mp4）
                if fnmatch.fnmatch(filename, normalized_pattern) or fnmatch.fnmatch(normalized_path, normalized_pattern):
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

    def get_stats_by_extension(self):
        """按扩展名统计"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT Extension, COUNT(*) as count
        FROM duplicate_groups
        WHERE Hash IS NOT NULL AND Hash != ''
        GROUP BY Extension
        ORDER BY count DESC
        ''')
        
        result = {}
        for ext, count in cursor.fetchall():
            result[ext or '(无扩展名)'] = count
        
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
        """按日期统计（基于文件修改时间）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT 
            DATE(f.Modified) as date,
            COUNT(DISTINCT dg.ID) as count
        FROM duplicate_groups dg
        INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
        INNER JOIN files f ON df.Filepath = f.Filename
        WHERE dg.Hash IS NOT NULL AND dg.Hash != ''
        GROUP BY DATE(f.Modified)
        ORDER BY date DESC
        LIMIT 30
        ''')
        
        result = {}
        for date, count in cursor.fetchall():
            result[date] = count
        
        conn.close()
        return result

    def get_groups_by_path(self, path):
        """获取指定路径下的重复文件组
        
        Args:
            path: 路径前缀
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count, dg.Hash
        FROM duplicate_groups dg
        INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
        INNER JOIN files f ON df.Filepath = f.Filename
        WHERE f.Filename LIKE ? AND dg.Hash IS NOT NULL AND dg.Hash != ''
        GROUP BY dg.ID
        ORDER BY (COUNT(*) - 1) * dg.Size DESC
        ''', (f"{path}%",))
        
        groups = cursor.fetchall()
        
        result = []
        for group_id, size, extension, file_count, hash_val in groups:
            # 获取该组在指定路径下的文件
            cursor.execute('''
            SELECT f.Filename
            FROM duplicate_files df
            INNER JOIN files f ON df.Filepath = f.Filename
            WHERE df.Group_ID = ? AND f.Filename LIKE ?
            ORDER BY f.Filename
            ''', (group_id, f"{path}%"))
            
            files = [row[0] for row in cursor.fetchall()]
            
            result.append({
                'group_id': group_id,
                'size': size,
                'extension': extension,
                'file_count': file_count,
                'savable_space': (file_count - 1) * size,
                'hash': hash_val,
                'files': files
            })
        
        conn.close()
        return result

if __name__ == '__main__':
    import sys
    
    analyzer = DuplicateAnalyzer()
    
    if len(sys.argv) < 2:
        print("用法: python duplicate_analyzer.py <command> [args]")
        print("\n可用命令:")
        print("  summary               - 显示数据汇总")
        print("  groups [options]      - 显示重复文件组列表")
        print("                          --top N              显示最大的N个组")
        print("                          --min-size <size>    最小文件大小")
        print("                          --max-size <size>    最大文件大小")
        print("                          --extension <ext>    文件扩展名")
        print("                          --unconfirmed        包括未确认哈希值的组")
        print("                          --sort size|count|path 排序方式")
        print("  group <id>            - 显示指定组的详细信息")
        print("  files <pattern>       - 按模式搜索文件")
        print("  hash <hash>           - 显示指定哈希值的所有文件")
        print("  stats [options]       - 显示统计分析")
        print("                          --by-extension       按扩展名统计")
        print("                          --by-size-range      按大小范围统计")
        print("                          --by-date            按日期统计")
        print("  path <path>           - 显示指定路径下的重复文件")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'summary':
        stats = analyzer.get_statistics(hash_only=False)
        print("\n数据汇总报告")
        print("=" * 60)
        print(f"总文件数: {stats['total_files']}")
        print(f"重复文件组数: {stats['duplicate_groups']}")
        print(f"重复文件关联数: {stats['duplicate_files']}")
        print(f"已计算哈希的文件数: {stats['hashed_files']}")
        print(f"待计算哈希的文件数: {stats['unhashed_files']}")
        print(f"总文件大小: {stats['total_size']:,} 字节 ({stats['total_size']/1024/1024/1024:.2f} GB)")
        print(f"重复文件总大小: {stats['duplicate_size']:,} 字节 ({stats['duplicate_size']/1024/1024/1024:.2f} GB)")
        print(f"\n如果删除重复文件:")
        print(f"  可以删除 {stats['duplicate_files'] - stats['duplicate_groups']} 个文件")
        print(f"  可以节省磁盘空间: {stats['duplicate_size']:,} 字节 ({stats['duplicate_size']/1024/1024/1024:.2f} GB)")
        print("=" * 60)
    
    elif command == 'groups':
        # 解析参数
        count = 20
        hash_only = True
        min_size = None
        max_size = None
        extension = None
        sort_by = 'size'
        
        i = 2
        while i < len(sys.argv):
            arg = sys.argv[i]
            if arg == '--top' and i + 1 < len(sys.argv):
                count = int(sys.argv[i + 1])
                i += 1
            elif arg == '--unconfirmed':
                hash_only = False
            elif arg == '--min-size' and i + 1 < len(sys.argv):
                size_str = sys.argv[i + 1].upper()
                if size_str.endswith('K'):
                    min_size = int(size_str[:-1]) * 1024
                elif size_str.endswith('M'):
                    min_size = int(size_str[:-1]) * 1024 * 1024
                elif size_str.endswith('G'):
                    min_size = int(size_str[:-1]) * 1024 * 1024 * 1024
                else:
                    min_size = int(size_str)
                i += 1
            elif arg == '--max-size' and i + 1 < len(sys.argv):
                size_str = sys.argv[i + 1].upper()
                if size_str.endswith('K'):
                    max_size = int(size_str[:-1]) * 1024
                elif size_str.endswith('M'):
                    max_size = int(size_str[:-1]) * 1024 * 1024
                elif size_str.endswith('G'):
                    max_size = int(size_str[:-1]) * 1024 * 1024 * 1024
                else:
                    max_size = int(size_str)
                i += 1
            elif arg == '--extension' and i + 1 < len(sys.argv):
                extension = sys.argv[i + 1]
                i += 1
            elif arg == '--sort' and i + 1 < len(sys.argv):
                sort_by = sys.argv[i + 1]
                i += 1
            i += 1
        
        groups = analyzer.get_groups_list(
            count=count,
            hash_only=hash_only,
            min_size=min_size,
            max_size=max_size,
            extension=extension,
            sort_by=sort_by
        )
        
        print("\n重复文件组列表")
        print("=" * 60)
        if not groups:
            print("  没有找到符合条件的重复文件组")
        else:
            for group in groups:
                print(f"\n组ID: {group['group_id']}")
                print(f"  文件大小: {group['size']:,} 字节 ({group['size']/1024/1024:.2f} MB)")
                print(f"  文件扩展名: {group['extension']}")
                print(f"  文件数量: {group['file_count']} 个")
                print(f"  可释放空间: {group['savable_space']:,} 字节 ({group['savable_space']/1024/1024/1024:.2f} GB)")
                if group['hash']:
                    print(f"  哈希值: {group['hash']}")
                else:
                    print(f"  哈希值: 未确认")
        print("=" * 60)
    
    elif command == 'group':
        if len(sys.argv) < 3:
            print("错误: 请指定组ID")
            sys.exit(1)
        
        try:
            group_id = int(sys.argv[2])
        except ValueError:
            print(f"错误: 无效的组ID: {sys.argv[2]}")
            sys.exit(1)
        
        group = analyzer.get_group_details(group_id)
        
        if not group:
            print(f"错误: 找不到组ID: {group_id}")
            sys.exit(1)
        
        print(f"\n组 {group_id} 的详细信息")
        print("=" * 60)
        print(f"文件大小: {group['size']:,} 字节 ({group['size']/1024/1024:.2f} MB)")
        print(f"文件扩展名: {group['extension']}")
        print(f"文件数量: {group['file_count']} 个")
        print(f"总大小: {group['group_size']:,} 字节 ({group['group_size']/1024/1024/1024:.2f} GB)")
        print(f"可释放空间: {group['savable_space']:,} 字节 ({group['savable_space']/1024/1024/1024:.2f} GB)")
        if group['hash']:
            print(f"哈希值: {group['hash']}")
        else:
            print(f"哈希值: 未确认")
        print(f"\n包含的文件:")
        for i, file_info in enumerate(group['files'], 1):
            print(f"  {i}. {file_info['filepath']}")
            print(f"     磁盘: {file_info['disk']}")
            print(f"     修改时间: {file_info['modified']}")
        print("=" * 60)
    
    elif command == 'files':
        if len(sys.argv) < 3:
            print("错误: 请指定搜索模式")
            sys.exit(1)
        
        pattern = sys.argv[2]
        groups = analyzer.filter_by_pattern(pattern, hash_only=True)
        
        print(f"\n文件搜索结果（模式: {pattern}）")
        print("=" * 60)
        if not groups:
            print("  没有找到匹配的文件")
        else:
            print(f"  找到 {len(groups)} 个匹配的重复文件组")
            for i, group in enumerate(groups, 1):
                print(f"\n{i}. 组ID: {group['group_id']}")
                print(f"   文件大小: {group['size']:,} 字节")
                print(f"   文件扩展名: {group['extension']}")
                print(f"   文件数量: {group['file_count']} 个")
                print(f"   匹配的文件:")
                for j, filepath in enumerate(group['matched_files'][:5], 1):
                    print(f"     {j}. {filepath}")
                if len(group['matched_files']) > 5:
                    print(f"     ... 还有 {len(group['matched_files']) - 5} 个匹配文件")
        print("=" * 60)
    
    elif command == 'hash':
        if len(sys.argv) < 3:
            print("错误: 请指定哈希值")
            sys.exit(1)
        
        hash_value = sys.argv[2]
        files = analyzer.get_duplicate_details(hash_value)
        
        print(f"\n哈希值为 {hash_value} 的重复文件:")
        print("=" * 60)
        if not files:
            print("  没有找到文件")
        else:
            for i, file_info in enumerate(files, 1):
                print(f"\n{i}. 文件路径: {file_info['filepath']}")
                print(f"   磁盘: {file_info['disk']}")
                print(f"   大小: {file_info['size']:,} 字节")
                print(f"   修改时间: {file_info['modified']}")
                print(f"   哈希值: {file_info['hash']}")
                print(f"   计算时间: {file_info['created_at']}")
        print("=" * 60)
    
    elif command == 'stats':
        by_extension = False
        by_size_range = False
        by_date = False
        
        for arg in sys.argv[2:]:
            if arg == '--by-extension':
                by_extension = True
            elif arg == '--by-size-range':
                by_size_range = True
            elif arg == '--by-date':
                by_date = True
        
        if by_extension:
            stats = analyzer.get_stats_by_extension()
            print("\n按扩展名统计")
            print("=" * 60)
            for ext, count in stats.items():
                print(f"  {ext}: {count} 个组")
            print("=" * 60)
        elif by_size_range:
            stats = analyzer.get_stats_by_size_range()
            print("\n按大小范围统计")
            print("=" * 60)
            for range_name, count in stats.items():
                print(f"  {range_name}: {count} 个组")
            print("=" * 60)
        elif by_date:
            stats = analyzer.get_stats_by_date()
            print("\n按日期统计")
            print("=" * 60)
            for date, count in stats.items():
                print(f"  {date}: {count} 个组")
            print("=" * 60)
        else:
            print("\n统计分析")
            print("=" * 60)
            print("请指定统计方式:")
            print("  --by-extension    按扩展名统计")
            print("  --by-size-range   按大小范围统计")
            print("  --by-date         按日期统计")
            print("=" * 60)
    
    elif command == 'path':
        if len(sys.argv) < 3:
            print("错误: 请指定路径")
            sys.exit(1)
        
        path = sys.argv[2]
        groups = analyzer.get_groups_by_path(path)
        
        print(f"\n路径 {path} 下的重复文件")
        print("=" * 60)
        if not groups:
            print("  没有找到重复文件")
        else:
            print(f"  找到 {len(groups)} 个重复文件组")
            for i, group in enumerate(groups, 1):
                print(f"\n{i}. 组ID: {group['group_id']}")
                print(f"   文件大小: {group['size']:,} 字节")
                print(f"   文件扩展名: {group['extension']}")
                print(f"   文件数量: {group['file_count']} 个")
                print(f"   包含的文件:")
                for j, filepath in enumerate(group['files'][:5], 1):
                    print(f"     {j}. {filepath}")
                if len(group['files']) > 5:
                    print(f"     ... 还有 {len(group['files']) - 5} 个文件")
        print("=" * 60)
    
    else:
        print(f"未知命令: {command}")
        sys.exit(1)