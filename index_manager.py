import sqlite3
import os
import shutil
from datetime import datetime

class IndexManager:
    def __init__(self, db_path='file_index.db'):
        self.db_path = db_path
    
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
    
    def clean_hash(self):
        """清除哈希数据"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM file_hash')
        count = cursor.fetchone()[0]
        
        cursor.execute('DELETE FROM file_hash')
        
        conn.commit()
        conn.close()
        
        print(f"已清除哈希数据，删除了 {count} 条哈希记录")
    
    def clean_full(self):
        """清除所有数据"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM files')
        files_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM file_hash')
        hash_count = cursor.fetchone()[0]
        
        cursor.execute('DELETE FROM files')
        cursor.execute('DELETE FROM duplicate_files')
        cursor.execute('DELETE FROM duplicate_groups')
        cursor.execute('DELETE FROM file_hash')
        
        conn.commit()
        conn.close()
        
        print(f"已清除所有数据")
        print(f"删除了 {files_count} 个文件记录")
        print(f"删除了 {hash_count} 条哈希记录")
    
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
            
            # 按扩展名和大小分组
            groups = {}
            for filepath, ext, size in duplicate_files:
                key = (ext, size)
                if key not in groups:
                    groups[key] = []
                groups[key].append(filepath)
            
            # 插入重复文件组
            for (ext, size), filepaths in groups.items():
                cursor.execute('''
                    INSERT INTO duplicate_groups (Extension, Size)
                    VALUES (?, ?)
                ''', (ext, size))
                group_id = cursor.lastrowid
                
                for filepath in filepaths:
                    cursor.execute('''
                        INSERT INTO duplicate_files (Group_ID, Filepath)
                        VALUES (?, ?)
                    ''', (group_id, filepath))
            
            conn.commit()
            
            print(f"创建了 {len(groups)} 个重复文件组")
            print(f"共有 {len(duplicate_files)} 个文件被分配到组中")
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
        self.clean_full()
        
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
        from file_scanner import FileScanner
        scanner = FileScanner(self.db_path)
        
        for path in scan_paths:
            if os.path.exists(path) and os.path.isdir(path):
                print(f"\n扫描路径: {path}")
                scanner.scan_directory(path)
            else:
                print(f"跳过不存在的路径: {path}")
        
        print("\n索引重建完成！")

if __name__ == '__main__':
    import sys
    
    manager = IndexManager()
    
    if len(sys.argv) < 2:
        print("用法: python index_manager.py <command> [args]")
        print("\n可用命令:")
        print("  clean           - 检查并清理索引文件（删除丢失文件、更新变更文件）")
        print("  clean files     - 清除文件索引")
        print("  clean hash      - 清除哈希数据")
        print("  clean full      - 清除所有数据")
        print("  rebuild         - 重建索引（清除所有数据后重新扫描所有磁盘）")
        print("  rebuild <path>  - 重建索引并扫描指定路径")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'clean':
        if len(sys.argv) < 3:
            # 没有指定清理类型，执行索引清理
            manager.clean_index()
        else:
            clean_type = sys.argv[2]
            if clean_type == 'files':
                manager.clean_files()
            elif clean_type == 'hash':
                manager.clean_hash()
            elif clean_type == 'full':
                manager.clean_full()
            else:
                print(f"错误: 未知的清理类型: {clean_type}")
                sys.exit(1)
    elif command == 'rebuild':
        if len(sys.argv) > 2:
            scan_paths = sys.argv[2:]
            manager.rebuild_index(scan_paths)
        else:
            manager.rebuild_index()
    else:
        print(f"未知命令: {command}")
        sys.exit(1)