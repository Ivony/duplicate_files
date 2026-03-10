import sqlite3

class DuplicateGroupCreator:
    def __init__(self, db_path):
        self.db_path = db_path
    
    def init_tables(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建duplicate_group表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS duplicate_group (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Size INTEGER,
            Extension TEXT,
            Count INTEGER
        )
        ''')
        
        # 确保duplicate表存在
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS duplicate (
            Filepath TEXT PRIMARY KEY,
            Size INTEGER,
            Modified REAL,
            Disk TEXT,
            Group_ID INTEGER
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def clear_existing_data(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 清空duplicate_group表
        cursor.execute('DELETE FROM duplicate_group')
        # 清空duplicate表
        cursor.execute('DELETE FROM duplicate')
        
        conn.commit()
        conn.close()
    
    def extract_extension(self, filepath):
        import os
        _, ext = os.path.splitext(filepath)
        return ext.lower() if ext else ''
    
    def create_duplicate_groups(self):
        self.init_tables()
        self.clear_existing_data()
        
        print("开始创建重复文件组...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 首先，我们需要从Hash表中获取文件信息，并提取扩展名
        # 创建临时表来存储文件信息和扩展名
        cursor.execute('''
        CREATE TEMP TABLE IF NOT EXISTS files_with_extension AS
        SELECT 
            Filepath,
            Size,
            Modified,
            SUBSTR(Filepath, INSTR(Filepath, '.') + 1) AS Extension,
            Disk
        FROM Hash
        WHERE Size > 0
        ''')
        
        # 插入到duplicate_group表
        cursor.execute('''
        INSERT INTO duplicate_group (Size, Extension, Count)
        SELECT Size, Extension, COUNT(*)
        FROM files_with_extension
        GROUP BY Size, Extension
        HAVING COUNT(*) > 1
        ''')
        
        # 重新插入到duplicate表
        cursor.execute('''
        INSERT INTO duplicate (Filepath, Size, Modified, Disk, Group_ID)
        SELECT 
            F.Filepath,
            F.Size,
            F.Modified,
            F.Disk,
            G.ID
        FROM files_with_extension AS F
        INNER JOIN duplicate_group AS G ON F.Size = G.Size AND F.Extension = G.Extension
        ''')
        
        # 获取创建的组数量
        cursor.execute('SELECT COUNT(*) FROM duplicate_group')
        group_count = cursor.fetchone()[0]
        
        # 获取有多少文件被分配到组
        cursor.execute('SELECT COUNT(*) FROM duplicate WHERE Group_ID IS NOT NULL')
        file_count = cursor.fetchone()[0]
        
        # 清理临时表
        cursor.execute('DROP TABLE IF EXISTS files_with_extension')
        
        conn.commit()
        conn.close()
        
        print(f"\n重复文件组创建完成！")
        print(f"创建了 {group_count} 个重复文件组")
        print(f"共有 {file_count} 个文件被分配到组中")

if __name__ == '__main__':
    creator = DuplicateGroupCreator('file_index.db')
    creator.create_duplicate_groups()