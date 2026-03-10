import sqlite3
import os

class DuplicateAnalyzer:
    def __init__(self, db_path='file_index.db'):
        self.db_path = db_path
        self.path_limit = None
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path, timeout=60.0, isolation_level='IMMEDIATE')
    
    def get_statistics(self):
        """获取统计信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 获取files表中的文件数量
        cursor.execute('SELECT COUNT(*) FROM files')
        total_files = cursor.fetchone()[0]
        
        # 获取duplicate_groups表中的组数量
        cursor.execute('SELECT COUNT(*) FROM duplicate_groups')
        duplicate_groups = cursor.fetchone()[0]
        
        # 获取duplicate_files表中的文件数量
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
    
    def get_top_groups(self, count=20):
        """获取最大的重复文件组"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if self.path_limit:
            cursor.execute('''
            SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count
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
            SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count
            FROM duplicate_groups dg
            INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
            GROUP BY dg.ID
            ORDER BY (COUNT(*) - 1) * dg.Size DESC
            LIMIT ?
            ''', (count,))
        
        groups = cursor.fetchall()
        
        top_groups = []
        for group_id, size, extension, file_count in groups:
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
                'total_files': len(files)
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
    
    def filter_duplicates(self, filter_type, value):
        """过滤重复文件
        
        Args:
            filter_type: 过滤类型（extension/size/path）
            value: 过滤值
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if filter_type == 'extension':
            cursor.execute('''
            SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count
            FROM duplicate_groups dg
            WHERE dg.Extension = ?
            ORDER BY (COUNT(*) - 1) * dg.Size DESC
            ''', (value,))
        elif filter_type == 'size':
            # 支持比较操作符，如 >1000000, <1000000, =1000000
            if value.startswith('>') or value.startswith('<'):
                operator = value[0]
                size_value = int(value[1:])
                cursor.execute(f'''
                SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count
                FROM duplicate_groups dg
                WHERE dg.Size {operator} ?
                ORDER BY (COUNT(*) - 1) * dg.Size DESC
                ''', (size_value,))
            else:
                cursor.execute('''
                SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count
                FROM duplicate_groups dg
                WHERE dg.Size = ?
                ORDER BY (COUNT(*) - 1) * dg.Size DESC
                ''', (int(value),))
        elif filter_type == 'path':
            cursor.execute('''
            SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count
            FROM duplicate_groups dg
            INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
            INNER JOIN files f ON df.Filepath = f.Filename
            WHERE f.Filename LIKE ?
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
        for group_id, size, extension, file_count in groups:
            result.append({
                'group_id': group_id,
                'size': size,
                'extension': extension,
                'file_count': file_count,
                'group_size': size * file_count,
                'savable_space': (file_count - 1) * size
            })
        
        return result

if __name__ == '__main__':
    import sys
    
    analyzer = DuplicateAnalyzer()
    
    if len(sys.argv) < 2:
        print("用法: python duplicate_analyzer.py <command> [args]")
        print("\n可用命令:")
        print("  stat                  - 显示重复文件统计信息")
        print("  top [N]              - 显示最大的N个重复文件组（默认20个）")
        print("  details <hash>        - 查看特定哈希值的重复文件详情")
        print("  filter <type> <value> - 按文件类型、大小等过滤重复文件")
        print("                          type: extension/size/path")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'stat':
        stats = analyzer.get_statistics()
        print("\n重复文件统计报告")
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
    
    elif command == 'top':
        count = 20
        if len(sys.argv) > 2:
            try:
                count = int(sys.argv[2])
            except ValueError:
                print("错误: 请输入有效的数字")
                sys.exit(1)
        
        top_groups = analyzer.get_top_groups(count)
        print(f"\n最大的{count}个重复文件组（按可释放空间排序）:")
        print("=" * 60)
        
        for group in top_groups:
            print(f"\n组ID: {group['group_id']}")
            print(f"  文件大小: {group['size']:,} 字节 ({group['size']/1024/1024:.2f} MB)")
            print(f"  文件扩展名: {group['extension']}")
            print(f"  文件数量: {group['file_count']} 个")
            print(f"  总大小: {group['group_size']:,} 字节 ({group['group_size']/1024/1024/1024:.2f} GB)")
            print(f"  可释放空间: {group['savable_space']:,} 字节 ({group['savable_space']/1024/1024/1024:.2f} GB)")
            print(f"  包含的文件（前10个，按修改时间排序）:")
            for i, (disk, filepath) in enumerate(group['files'], 1):
                print(f"    {i}. [{disk}] {filepath}")
            
            if group['total_files'] > 10:
                print(f"    ... 还有 {group['total_files'] - 10} 个文件")
        
        print("=" * 60)
    
    elif command == 'details':
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
    
    elif command == 'filter':
        if len(sys.argv) < 4:
            print("错误: 请指定过滤类型和值")
            print("用法: python duplicate_analyzer.py filter <type> <value>")
            print("  type: extension/size/path")
            sys.exit(1)
        
        filter_type = sys.argv[2]
        value = sys.argv[3]
        
        groups = analyzer.filter_duplicates(filter_type, value)
        
        print(f"\n过滤结果（{filter_type} = {value}):")
        print("=" * 60)
        if not groups:
            print("  没有找到匹配的重复文件组")
        else:
            for i, group in enumerate(groups, 1):
                print(f"\n{i}. 组ID: {group['group_id']}")
                print(f"   文件大小: {group['size']:,} 字节")
                print(f"   文件扩展名: {group['extension']}")
                print(f"   文件数量: {group['file_count']} 个")
                print(f"   可释放空间: {group['savable_space']:,} 字节")
        print("=" * 60)
    
    else:
        print(f"未知命令: {command}")
        sys.exit(1)