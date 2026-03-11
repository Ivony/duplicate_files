import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path='file_index.db'):
        self.db_path = db_path
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path, timeout=60.0, isolation_level='IMMEDIATE')
    
    def init_database(self, force=False):
        """初始化数据库结构
        
        Args:
            force: 是否强制重建，如果为True则删除现有数据库文件
        """
        # 检查数据库文件是否存在
        if os.path.exists(self.db_path):
            if not force:
                print(f"警告: 数据库文件已存在: {self.db_path}")
                print("重建数据库将删除所有现有数据，此操作不可恢复！")
                print("\n数据库文件信息:")
                file_size = os.path.getsize(self.db_path)
                print(f"  文件大小: {file_size:,} 字节 ({file_size/1024/1024:.2f} MB)")
                
                # 尝试获取数据库中的数据量
                try:
                    conn = sqlite3.connect(self.db_path, timeout=60.0)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    print(f"  包含表数量: {len(tables)}")
                    for table in tables:
                        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                        count = cursor.fetchone()[0]
                        print(f"  表 {table[0]}: {count} 条记录")
                    conn.close()
                except Exception as e:
                    print(f"  无法读取数据库信息: {e}")
                
                print("\n确认要删除并重建数据库吗？")
                confirmation = input("请输入 'yes' 确认，或按任意键取消: ").strip().lower()
                
                if confirmation != 'yes':
                    print("操作已取消")
                    return False
            else:
                print(f"强制重建数据库: {self.db_path}")
            
            # 删除现有数据库文件
            try:
                os.remove(self.db_path)
                print(f"已删除现有数据库文件: {self.db_path}")
            except Exception as e:
                print(f"删除数据库文件失败: {e}")
                return False
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 创建files表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            Filename TEXT PRIMARY KEY,
            Extension TEXT,
            Size INTEGER,
            Created TEXT,
            Modified TEXT,
            Accessed TEXT
        )
        ''')
        
        # 创建duplicate_groups表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS duplicate_groups (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Size INTEGER,
            Extension TEXT,
            Hash TEXT
        )
        ''')
        
        # 创建duplicate_files表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS duplicate_files (
            Filepath TEXT PRIMARY KEY,
            Group_ID INTEGER,
            FOREIGN KEY (Group_ID) REFERENCES duplicate_groups(ID) ON DELETE CASCADE
        )
        ''')
        
        # 创建file_hash表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_hash (
            Filepath TEXT PRIMARY KEY,
            Size INTEGER,
            Hash TEXT,
            Modified TEXT,
            created_at TEXT
        )
        ''')
        
        conn.commit()
        conn.close()
        print("数据库结构初始化完成")
        return True
    
    def check_database(self):
        """检查数据库结构和数据"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print("数据库中的表:")
        for table in tables:
            print(f"  {table[0]}")
        
        for table in tables:
            table_name = table[0]
            print(f"\n表 {table_name} 的结构:")
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
            
            print(f"表 {table_name} 的数据量:")
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  总记录数: {count}")
            
            if count > 0:
                print(f"表 {table_name} 的前5条记录:")
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                rows = cursor.fetchall()
                for row in rows:
                    print(f"  {row}")
        
        conn.close()
    
    def optimize_database(self):
        """优化数据库性能"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("VACUUM")
        cursor.execute("ANALYZE")
        
        conn.commit()
        conn.close()
        print("数据库优化完成")
    
    def backup_database(self, backup_path):
        """备份数据库"""
        import shutil
        shutil.copy2(self.db_path, backup_path)
        print(f"数据库已备份到: {backup_path}")
    
    def restore_database(self, backup_path):
        """从备份恢复数据库"""
        import shutil
        shutil.copy2(backup_path, self.db_path)
        print(f"数据库已从 {backup_path} 恢复")
    
    def get_index_status(self):
        """获取索引状态"""
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
        
        conn.close()
        
        print("\n索引状态:")
        print(f"总计索引的文件数量: {total_files}")
        print(f"可能重复的文件组数量: {duplicate_groups}")
        print(f"重复文件关联数量: {duplicate_files}")
        print(f"已经计算了哈希值的文件数量: {hashed_files}")
        print(f"待计算哈希值的文件数量: {unhashed_files}")
        
        return {
            'total_files': total_files,
            'duplicate_groups': duplicate_groups,
            'duplicate_files': duplicate_files,
            'hashed_files': hashed_files,
            'unhashed_files': unhashed_files
        }
    
    def list_indexed_files(self, path):
        """列举指定路径下已经索引的文件和哈希值状态"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 查询指定路径下的文件
        cursor.execute('''
        SELECT f.Filename, f.Size, f.Modified, fh.Hash
        FROM files f
        LEFT JOIN file_hash fh ON f.Filename = fh.Filepath
        WHERE f.Filename LIKE ?
        ORDER BY f.Filename
        LIMIT 100
        ''', (f"{path}%",))
        
        files = cursor.fetchall()
        conn.close()
        
        print(f"\n路径 {path} 下已索引的文件:")
        if not files:
            print("  没有找到已索引的文件")
        else:
            for i, (filename, size, modified, hash_val) in enumerate(files, 1):
                hash_status = "已计算" if hash_val else "未计算"
                print(f"  {i}. {filename}")
                print(f"     大小: {size} 字节, 修改时间: {modified}, 哈希状态: {hash_status}")
                if hash_val:
                    print(f"     哈希值: {hash_val}")
        
        if len(files) >= 100:
            print(f"\n... 还有更多文件（仅显示前100个）")

if __name__ == '__main__':
    import sys
    
    manager = DatabaseManager()
    
    if len(sys.argv) < 2:
        print("用法: python database_manager.py <command> [args]")
        print("\n可用命令:")
        print("  init [--force]  - 初始化数据库结构（--force 强制重建，不询问）")
        print("  check          - 检查数据库结构和数据")
        print("  optimize        - 优化数据库性能")
        print("  backup <path>  - 备份数据库")
        print("  restore <path> - 从备份恢复数据库")
        print("  status         - 查看索引状态")
        print("  list <path>    - 列举指定路径的索引文件")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'init':
        force = '--force' in sys.argv
        manager.init_database(force)
    elif command == 'check':
        manager.check_database()
    elif command == 'optimize':
        manager.optimize_database()
    elif command == 'backup':
        if len(sys.argv) < 3:
            print("错误: 请指定备份路径")
            sys.exit(1)
        manager.backup_database(sys.argv[2])
    elif command == 'restore':
        if len(sys.argv) < 3:
            print("错误: 请指定备份文件路径")
            sys.exit(1)
        manager.restore_database(sys.argv[2])
    elif command == 'status':
        manager.get_index_status()
    elif command == 'list':
        if len(sys.argv) < 3:
            print("错误: 请指定路径")
            sys.exit(1)
        manager.list_indexed_files(sys.argv[2])
    else:
        print(f"未知命令: {command}")
        sys.exit(1)