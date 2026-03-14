import typer
import os
import sqlite3
from datetime import datetime

DB_PATH = 'file_index.db'

def get_db_path():
    """获取数据库路径"""
    return DB_PATH

def set_db_path(path):
    """设置数据库路径（用于测试）"""
    global DB_PATH
    DB_PATH = path

class DatabaseManager:
    def __init__(self, db_path=None):
        self.db_path = db_path or get_db_path()
    
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

    def backup_file_hash(self, backup_path):
        """备份file_hash表到CSV文件

        Args:
            backup_path: 备份文件路径（.csv格式）
        """
        import csv

        conn = self.get_connection()
        cursor = conn.cursor()

        # 获取file_hash表的所有数据
        cursor.execute('SELECT Filepath, Hash, created_at FROM file_hash WHERE Hash IS NOT NULL AND Hash != ""')
        rows = cursor.fetchall()

        conn.close()

        # 写入CSV文件
        with open(backup_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Filepath', 'Hash', 'created_at'])  # 表头
            writer.writerows(rows)

        print(f"file_hash表已备份到: {backup_path}")
        print(f"  共备份 {len(rows)} 条哈希记录")

    def restore_file_hash(self, backup_path, merge=False):
        """从CSV文件还原file_hash表

        Args:
            backup_path: 备份文件路径（.csv格式）
            merge: 是否合并模式（True则保留现有数据，False则清空后导入）
        """
        import csv

        if not os.path.exists(backup_path):
            print(f"错误: 备份文件不存在: {backup_path}")
            return False

        conn = self.get_connection()
        cursor = conn.cursor()

        # 清空现有数据（非合并模式）
        if not merge:
            cursor.execute('DELETE FROM file_hash')
            print("已清空现有file_hash表数据")

        # 读取CSV文件并导入
        imported_count = 0
        skipped_count = 0

        with open(backup_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # 跳过表头

            for row in reader:
                if len(row) >= 2:
                    filepath, hash_val = row[0], row[1]
                    created_at = row[2] if len(row) > 2 else None

                    # 检查是否已存在
                    cursor.execute('SELECT COUNT(*) FROM file_hash WHERE Filepath = ?', (filepath,))
                    if cursor.fetchone()[0] > 0:
                        if merge:
                            # 合并模式：更新现有记录
                            cursor.execute('''
                                UPDATE file_hash SET Hash = ?, created_at = ?
                                WHERE Filepath = ?
                            ''', (hash_val, created_at, filepath))
                            imported_count += 1
                        else:
                            skipped_count += 1
                    else:
                        # 插入新记录
                        cursor.execute('''
                            INSERT INTO file_hash (Filepath, Hash, created_at)
                            VALUES (?, ?, ?)
                        ''', (filepath, hash_val, created_at))
                        imported_count += 1

        conn.commit()

        # 统计结果
        cursor.execute('SELECT COUNT(*) FROM file_hash WHERE Hash IS NOT NULL AND Hash != ""')
        total_count = cursor.fetchone()[0]

        conn.close()

        print(f"file_hash表已从 {backup_path} 还原")
        print(f"  导入记录: {imported_count}")
        if skipped_count > 0:
            print(f"  跳过记录: {skipped_count}（已存在）")
        print(f"  当前总记录数: {total_count}")

        return True

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

app = typer.Typer()

@app.command()
def check():
    """检查数据库结构和数据"""
    db_manager = DatabaseManager()
    db_manager.check_database()

@app.command()
def optimize():
    """优化数据库性能"""
    db_manager = DatabaseManager()
    db_manager.optimize_database()

@app.command()
def init(
    force: bool = False
):
    """重建数据库结构，--force 强制重建，不询问"""
    db_manager = DatabaseManager()
    db_manager.init_database(force)
