import sqlite3

def check_database(db_path):
    conn = sqlite3.connect(db_path)
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

if __name__ == '__main__':
    db_path = 'file_index.db'
    check_database(db_path)