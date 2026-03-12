import sqlite3
import os
import sys

class DataViewer:
    """数据查看器 - 提供查询和展示重复文件数据的功能"""
    
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
    
    def show_summary(self, hash_only=False):
        """显示数据汇总"""
        stats = self.get_statistics(hash_only=hash_only)
        
        print(f"\n数据汇总报告")
        print(f"=" * 60)
        print(f"总文件数: {stats['total_files']:,}")
        print(f"重复文件组数: {stats['duplicate_groups']:,}")
        print(f"重复文件关联数: {stats['duplicate_files']:,}")
        print(f"已计算哈希的文件数: {stats['hashed_files']:,}")
        print(f"待计算哈希的文件数: {stats['unhashed_files']:,}")
        print(f"总文件大小: {stats['total_size']:,} 字节 ({stats['total_size']/1024/1024/1024:.2f} GB)")
        print(f"重复文件总大小: {stats['duplicate_size']:,} 字节 ({stats['duplicate_size']/1024/1024/1024:.2f} GB)")
        print(f"\n如果删除重复文件:")
        print(f"  可以删除 {stats['duplicate_files'] - stats['duplicate_groups']} 个文件")
        print(f"  可以节省磁盘空间: {stats['duplicate_size']:,} 字节 ({stats['duplicate_size']/1024/1024/1024:.2f} GB)")
        print(f"=" * 60)
    
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
    
    def show_groups(self, count=20, hash_only=True, min_size=None, max_size=None, extension=None, sort_by='size'):
        """显示重复文件组列表"""
        groups = self.get_groups_list(
            count=count,
            hash_only=hash_only,
            min_size=min_size,
            max_size=max_size,
            extension=extension,
            sort_by=sort_by
        )
        
        print(f"\n重复文件组列表")
        print(f"=" * 60)
        
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
        
        print(f"=" * 60)
    
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
    
    def show_group(self, group_id):
        """显示指定组的详细信息"""
        group = self.get_group_details(group_id)
        
        if not group:
            print(f"错误: 找不到组ID: {group_id}")
            return
        
        print(f"\n组 {group_id} 的详细信息")
        print(f"=" * 60)
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
        print(f"=" * 60)
    
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
    
    def show_files(self, pattern, show_all=False, show_hash=False, limit=100):
        """显示文件查询结果"""
        has_wildcard = '*' in pattern or '?' in pattern
        
        if has_wildcard:
            # 模式搜索：查找重复文件组
            groups = self.filter_by_pattern(pattern, hash_only=True)
            
            print(f"\n文件搜索结果（模式: {pattern}）")
            print(f"=" * 60)
            
            if not groups:
                print("  没有找到匹配的文件")
            else:
                print(f"  找到 {len(groups)} 个匹配的重复文件组")
                for i, group in enumerate(groups[:limit], 1):
                    print(f"\n{i}. 组ID: {group['group_id']}")
                    print(f"   文件大小: {group['size']:,} 字节")
                    print(f"   文件扩展名: {group['extension']}")
                    print(f"   文件数量: {group['file_count']} 个")
                    print(f"   匹配的文件:")
                    for j, filepath in enumerate(group['matched_files'][:5], 1):
                        print(f"     {j}. {filepath}")
                    if len(group['matched_files']) > 5:
                        print(f"     ... 还有 {len(group['matched_files']) - 5} 个匹配文件")
                
                if len(groups) > limit:
                    print(f"\n... 还有 {len(groups) - limit} 个组未显示（使用 --limit {limit + 20} 显示更多）")
            
            print(f"=" * 60)
        else:
            # 路径查询：显示已索引的文件
            if show_all:
                # 显示所有已索引文件
                conn = self.get_connection()
                cursor = conn.cursor()
                
                query = '''
                    SELECT f.Filename, f.Size, f.Modified, fh.Hash, fh.created_at
                    FROM files f
                    LEFT JOIN file_hash fh ON f.Filename = fh.Filepath
                    WHERE f.Filename LIKE ?
                    ORDER BY f.Filename
                    LIMIT ?
                '''
                cursor.execute(query, (f"{pattern}%", limit))
                files = cursor.fetchall()
                conn.close()
                
                print(f"\n路径 {pattern} 下已索引的文件:")
                if not files:
                    print("  没有找到已索引的文件")
                else:
                    for i, (filename, size, modified, hash_val, created_at) in enumerate(files, 1):
                        hash_status = "已计算" if hash_val else "未计算"
                        print(f"  {i}. {filename}")
                        print(f"     大小: {size:,} 字节, 修改时间: {modified}, 哈希状态: {hash_status}")
                        if show_hash and hash_val:
                            print(f"     哈希值: {hash_val}")
                            if created_at:
                                print(f"     计算时间: {created_at}")
                
                if len(files) >= limit:
                    print(f"\n... 还有更多文件（仅显示前{limit}个，使用 --limit {limit + 100} 显示更多）")
            else:
                # 显示路径下的重复文件组
                groups = self.get_groups_by_path(pattern)
                
                print(f"\n路径 {pattern} 下的重复文件")
                print(f"=" * 60)
                
                if not groups:
                    print("  没有找到重复文件")
                else:
                    print(f"  找到 {len(groups)} 个重复文件组")
                    for i, group in enumerate(groups[:limit], 1):
                        print(f"\n{i}. 组ID: {group['group_id']}")
                        print(f"   文件大小: {group['size']:,} 字节")
                        print(f"   文件扩展名: {group['extension']}")
                        print(f"   文件数量: {group['file_count']} 个")
                        print(f"   包含的文件:")
                        for j, filepath in enumerate(group['files'][:5], 1):
                            print(f"     {j}. {filepath}")
                        if len(group['files']) > 5:
                            print(f"     ... 还有 {len(group['files']) - 5} 个文件")
                    
                    if len(groups) > limit:
                        print(f"\n... 还有 {len(groups) - limit} 个组未显示（使用 --limit {limit + 20} 显示更多）")
                
                print(f"=" * 60)
    
    def get_groups_by_path(self, path_prefix):
        """获取指定路径下的重复文件组"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT DISTINCT dg.ID, dg.Size, dg.Extension, dg.Hash
        FROM duplicate_groups dg
        INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
        INNER JOIN files f ON df.Filepath = f.Filename
        WHERE f.Filename LIKE ? AND dg.Hash IS NOT NULL AND dg.Hash != ''
        ''', (f"{path_prefix}%",))
        
        groups = []
        for row in cursor.fetchall():
            group_id, size, extension, hash_val = row
            
            # 获取该组在该路径下的文件
            cursor.execute('''
            SELECT f.Filename
            FROM duplicate_files df
            INNER JOIN files f ON df.Filepath = f.Filename
            WHERE df.Group_ID = ? AND f.Filename LIKE ?
            ORDER BY f.Filename
            ''', (group_id, f"{path_prefix}%"))
            
            files = [f[0] for f in cursor.fetchall()]
            
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
    
    def show_stats(self, by_extension=False, by_size_range=False, by_date=False):
        """显示统计分析"""
        if by_extension:
            stats = self.get_stats_by_extension()
            print(f"\n按扩展名统计")
            print(f"=" * 60)
            for ext, count in stats.items():
                print(f"  {ext or '(无扩展名)'}: {count} 个组")
            print(f"=" * 60)
        elif by_size_range:
            stats = self.get_stats_by_size_range()
            print(f"\n按大小范围统计")
            print(f"=" * 60)
            for range_name, count in stats.items():
                print(f"  {range_name}: {count} 个组")
            print(f"=" * 60)
        elif by_date:
            stats = self.get_stats_by_date()
            print(f"\n按日期统计")
            print(f"=" * 60)
            for date, count in stats.items():
                print(f"  {date}: {count} 个文件")
            print(f"=" * 60)
        else:
            # 默认显示所有统计
            print(f"\n统计分析")
            print(f"=" * 60)
            print("请指定统计方式:")
            print("  --by-extension    按扩展名统计")
            print("  --by-size-range   按大小范围统计")
            print("  --by-date         按日期统计")
            print(f"=" * 60)


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python data_viewer.py <command> [args]")
        print("\n可用命令:")
        print("  summary                    - 显示数据汇总")
        print("  groups [options]           - 显示重复文件组列表")
        print("    --top <n>                - 显示前n个组（默认20）")
        print("    --unconfirmed            - 包括未确认哈希值的组")
        print("    --min-size <size>        - 最小文件大小")
        print("    --max-size <size>        - 最大文件大小")
        print("    --extension <ext>        - 按扩展名过滤")
        print("    --sort <size|count|path> - 排序方式")
        print("  group <id>                 - 显示指定组的详细信息")
        print("  files <pattern> [options]  - 查询文件")
        print("    --all                    - 显示所有已索引文件")
        print("    --hash                   - 显示哈希值")
        print("    --limit <n>              - 限制显示数量")
        print("  stats <type>               - 统计分析")
        print("    --by-extension           - 按扩展名统计")
        print("    --by-size-range          - 按大小范围统计")
        print("    --by-date                - 按日期统计")
        sys.exit(1)
    
    viewer = DataViewer()
    command = sys.argv[1]
    
    if command == 'summary':
        viewer.show_summary()
    
    elif command == 'groups':
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
                size_str = sys.argv[i + 1]
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
                size_str = sys.argv[i + 1]
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
        
        viewer.show_groups(count, hash_only, min_size, max_size, extension, sort_by)
    
    elif command == 'group':
        if len(sys.argv) < 3:
            print("错误: 请指定组ID")
            sys.exit(1)
        try:
            group_id = int(sys.argv[2])
            viewer.show_group(group_id)
        except ValueError:
            print(f"错误: 无效的组ID: {sys.argv[2]}")
            sys.exit(1)
    
    elif command == 'files':
        if len(sys.argv) < 3:
            print("错误: 请指定路径或模式")
            sys.exit(1)
        
        pattern = sys.argv[2]
        show_all = False
        show_hash = False
        limit = 100
        
        i = 3
        while i < len(sys.argv):
            arg = sys.argv[i]
            if arg == '--all':
                show_all = True
            elif arg == '--hash':
                show_hash = True
            elif arg == '--limit' and i + 1 < len(sys.argv):
                limit = int(sys.argv[i + 1])
                i += 1
            i += 1
        
        viewer.show_files(pattern, show_all, show_hash, limit)
    
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
        
        viewer.show_stats(by_extension, by_size_range, by_date)
    
    else:
        print(f"错误: 未知命令: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
