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
        print("  clean files    - 清除文件索引")
        print("  clean hash     - 清除哈希数据")
        print("  clean full     - 清除所有数据")
        print("  rebuild         - 重建索引（清除所有数据后重新扫描所有磁盘）")
        print("  rebuild <path> - 重建索引并扫描指定路径")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'clean':
        if len(sys.argv) < 3:
            print("错误: 请指定清理类型（files/hash/full）")
            sys.exit(1)
        
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