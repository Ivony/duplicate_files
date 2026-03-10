import sqlite3
import os
from datetime import datetime

class FileCleaner:
    def __init__(self, db_path='file_index.db'):
        self.db_path = db_path
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path, timeout=60.0, isolation_level='IMMEDIATE')
    
    def dryrun_clean(self):
        """模拟清理操作"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        print("开始模拟清理操作...")
        
        # 获取所有重复文件组
        cursor.execute('''
        SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count
        FROM duplicate_groups dg
        INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
        GROUP BY dg.ID
        ORDER BY (COUNT(*) - 1) * dg.Size DESC
        ''')
        
        groups = cursor.fetchall()
        
        total_files = 0
        total_size = 0
        
        print(f"\n模拟清理结果:")
        print("=" * 60)
        
        for group_id, size, extension, file_count in groups:
            # 获取该组的文件列表
            cursor.execute('''
            SELECT f.Filename, f.Modified, fh.Hash
            FROM duplicate_files df
            INNER JOIN files f ON df.Filepath = f.Filename
            LEFT JOIN file_hash fh ON df.Filepath = fh.Filepath
            WHERE df.Group_ID = ?
            ORDER BY f.Modified DESC
            ''', (group_id,))
            
            files = cursor.fetchall()
            
            if file_count > 1:
                # 保留最新的文件，删除其他文件
                keep_file = files[0]
                delete_files = files[1:]
                
                print(f"\n组ID: {group_id}")
                print(f"  文件扩展名: {extension}")
                print(f"  文件大小: {size:,} 字节")
                print(f"  文件数量: {file_count} 个")
                print(f"  保留文件: {keep_file[0]}")
                print(f"  删除文件数: {len(delete_files)} 个")
                print(f"  可释放空间: {(file_count - 1) * size:,} 字节")
                
                for i, (filename, _, _) in enumerate(delete_files, 1):
                    print(f"    {i}. {filename}")
                
                total_files += len(delete_files)
                total_size += (file_count - 1) * size
        
        conn.close()
        
        print("\n" + "=" * 60)
        print(f"总计:")
        print(f"  可删除文件数: {total_files:,} 个")
        print(f"  可释放空间: {total_size:,} 字节 ({total_size/1024/1024/1024:.2f} GB)")
        print("=" * 60)
        print("\n注意：这是模拟操作，没有实际删除任何文件")
    
    def safe_clean(self):
        """安全模式清理，保留每个组中最新的文件"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        print("开始安全模式清理...")
        
        # 获取所有重复文件组
        cursor.execute('''
        SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count
        FROM duplicate_groups dg
        INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
        GROUP BY dg.ID
        ORDER BY (COUNT(*) - 1) * dg.Size DESC
        ''')
        
        groups = cursor.fetchall()
        
        total_files = 0
        total_size = 0
        failed_files = []
        
        print(f"\n安全模式清理结果:")
        print("=" * 60)
        
        for group_id, size, extension, file_count in groups:
            if file_count <= 1:
                continue
            
            # 获取该组的文件列表
            cursor.execute('''
            SELECT f.Filename, f.Modified, fh.Hash
            FROM duplicate_files df
            INNER JOIN files f ON df.Filepath = f.Filename
            LEFT JOIN file_hash fh ON df.Filepath = fh.Filepath
            WHERE df.Group_ID = ?
            ORDER BY f.Modified DESC
            ''', (group_id,))
            
            files = cursor.fetchall()
            
            # 保留最新的文件，删除其他文件
            keep_file = files[0]
            delete_files = files[1:]
            
            print(f"\n组ID: {group_id}")
            print(f"  文件扩展名: {extension}")
            print(f"  文件大小: {size:,} 字节")
            print(f"  文件数量: {file_count} 个")
            print(f"   保留文件: {keep_file[0]}")
            print(f"  删除文件数: {len(delete_files)} 个")
            print(f"  可释放空间: {(file_count - 1) * size:,} 字节")
            
            for i, (filename, _, _) in enumerate(delete_files, 1):
                print(f"    {i}. {filename}")
                
                try:
                    if os.path.exists(filename):
                        os.remove(filename)
                        total_files += 1
                        total_size += size
                    else:
                        print(f"    警告: 文件不存在 {filename}")
                        failed_files.append(filename)
                except Exception as e:
                    print(f"    错误: 删除文件失败 {filename}: {e}")
                    failed_files.append(filename)
        
        conn.close()
        
        print("\n" + "=" * 60)
        print(f"清理完成！")
        print(f"总计:")
        print(f"  已删除文件数: {total_files:,} 个")
        print(f"  已释放空间: {total_size:,} 字节 ({total_size/1024/1024/1024:.2f} GB)")
        
        if failed_files:
            print(f"  删除失败文件数: {len(failed_files)} 个")
        
        print("=" * 60)
    
    def auto_clean(self):
        """自动模式清理，根据规则自动选择保留的文件"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        print("开始自动模式清理...")
        print("规则: 保留哈希值相同且最新的文件")
        
        # 获取所有有哈希值的重复文件组
        cursor.execute('''
        SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count
        FROM duplicate_groups dg
        INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
        INNER JOIN file_hash fh ON df.Filepath = fh.Filepath
        GROUP BY dg.ID
        HAVING COUNT(*) > 1
        ORDER BY (COUNT(*) - 1) * dg.Size DESC
        ''')
        
        groups = cursor.fetchall()
        
        total_files = 0
        total_size = 0
        failed_files = []
        
        print(f"\n自动模式清理结果:")
        print("=" * 60)
        
        for group_id, size, extension, file_count in groups:
            # 获取该组的文件列表，按哈希值分组
            cursor.execute('''
            SELECT f.Filename, f.Modified, fh.Hash
            FROM duplicate_files df
            INNER JOIN files f ON df.Filepath = f.Filename
            INNER JOIN file_hash fh ON df.Filepath = fh.Filepath
            WHERE df.Group_ID = ?
            ORDER BY fh.Hash, f.Modified DESC
            ''', (group_id,))
            
            files = cursor.fetchall()
            
            # 按哈希值分组，每个哈希值保留最新的文件
            hash_groups = {}
            for filename, modified, hash_val in files:
                if hash_val not in hash_groups:
                    hash_groups[hash_val] = []
                hash_groups[hash_val].append((filename, modified))
            
            keep_files = []
            delete_files = []
            
            for hash_val, file_list in hash_groups.items():
                # 保留最新的文件
                file_list.sort(key=lambda x: x[1], reverse=True)
                keep_files.append(file_list[0])
                delete_files.extend(file_list[1:])
            
            print(f"\n组ID: {group_id}")
            print(f"  文件扩展名: {extension}")
            print(f"  文件大小: {size:,} 字节")
            print(f"  文件数量: {file_count} 个")
            print(f"  哈希值组数: {len(hash_groups)} 个")
            print(f"  保留文件数: {len(keep_files)} 个")
            print(f"  删除文件数: {len(delete_files)} 个")
            print(f"  可释放空间: {len(delete_files) * size:,} 字节")
            
            for i, (filename, _) in enumerate(delete_files, 1):
                print(f"    {i}. {filename}")
                
                try:
                    if os.path.exists(filename):
                        os.remove(filename)
                        total_files += 1
                        total_size += size
                    else:
                        print(f"    警告: 文件不存在 {filename}")
                        failed_files.append(filename)
                except Exception as e:
                    print(f"    错误: 删除文件失败 {filename}: {e}")
                    failed_files.append(filename)
        
        conn.close()
        
        print("\n" + "=" * 60)
        print(f"清理完成！")
        print(f"总计:")
        print(f"  已删除文件数: {total_files:,} 个")
        print(f"  已释放空间: {total_size:,} 字节 ({total_size/1024/1024/1024:.2f} GB)")
        
        if failed_files:
            print(f"  删除失败文件数: {len(failed_files)} 个")
        
        print("=" * 60)
    
    def preview_clean(self):
        """预览清理操作的结果"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        print("开始预览清理操作...")
        
        # 获取所有重复文件组
        cursor.execute('''
        SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count
        FROM duplicate_groups dg
        INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
        GROUP BY dg.ID
        ORDER BY (COUNT(*) - 1) * dg.Size DESC
        ''')
        
        groups = cursor.fetchall()
        
        total_files = 0
        total_size = 0
        
        print(f"\n预览清理结果:")
        print("=" * 60)
        
        for group_id, size, extension, file_count in groups:
            if file_count <= 1:
                continue
            
            # 获取该组的文件列表
            cursor.execute('''
            SELECT f.Filename, f.Modified, fh.Hash
            FROM duplicate_files df
            INNER JOIN files f ON df.Filepath = f.Filename
            LEFT JOIN file_hash fh ON df.Filepath = fh.Filepath
            WHERE df.Group_ID = ?
            ORDER BY f.Modified DESC
            ''', (group_id,))
            
            files = cursor.fetchall()
            
            # 保留最新的文件，删除其他文件
            keep_file = files[0]
            delete_files = files[1:]
            
            print(f"\n组ID: {group_id}")
            print(f"  文件扩展名: {extension}")
            print(f"  文件大小: {size:,} 字节")
            print(f"  文件数量: {file_count} 个")
            print(f"  保留文件: {keep_file[0]}")
            print(f"  删除文件数: {len(delete_files)} 个")
            print(f"  可释放空间: {(file_count - 1) * size:,} 字节")
            
            for i, (filename, _, _) in enumerate(delete_files, 1):
                print(f"    {i}. {filename}")
            
            total_files += len(delete_files)
            total_size += (file_count - 1) * size
        
        conn.close()
        
        print("\n" + "=" * 60)
        print(f"预览总计:")
        print(f"  可删除文件数: {total_files:,} 个")
        print(f"  可释放空间: {total_size:,} 字节 ({total_size/1024/1024/1024:.2f} GB)")
        print("=" * 60)
        print("\n注意：这是预览操作，没有实际删除任何文件")
        print("使用 'clean safe' 或 'clean auto' 命令执行实际的清理操作")

if __name__ == '__main__':
    import sys
    
    cleaner = FileCleaner()
    
    if len(sys.argv) < 2:
        print("用法: python file_cleaner.py <command>")
        print("\n可用命令:")
        print("  dryrun    - 模拟清理操作，不实际删除文件")
        print("  safe      - 安全模式清理，保留每个组中最新的文件")
        print("  auto       - 自动模式清理，根据规则自动选择保留的文件")
        print("  preview    - 预览清理操作的结果")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'dryrun':
        cleaner.dryrun_clean()
    elif command == 'safe':
        cleaner.safe_clean()
    elif command == 'auto':
        cleaner.auto_clean()
    elif command == 'preview':
        cleaner.preview_clean()
    else:
        print(f"未知命令: {command}")
        sys.exit(1)