import pytest
import os
import tempfile
import sqlite3

@pytest.fixture
def temp_dir():
    """创建临时目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture
def temp_db():
    """创建临时数据库"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmpdb:
        db_path = tmpdb.name
    
    # 初始化数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建files表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS files (
        Filename TEXT PRIMARY KEY,
        Extension TEXT,
        Size INTEGER,
        Created REAL,
        Modified REAL,
        Accessed REAL
    )
    ''')
    
    # 创建duplicate_groups表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS duplicate_groups (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Extension TEXT,
        Size INTEGER,
        Hash TEXT
    )
    ''')
    
    # 创建duplicate_files表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS duplicate_files (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Group_ID INTEGER,
        Filepath TEXT,
        FOREIGN KEY (Group_ID) REFERENCES duplicate_groups (ID)
    )
    ''')
    
    # 创建file_hash表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS file_hash (
        Filepath TEXT PRIMARY KEY,
        Size INTEGER,
        Modified REAL,
        Hash TEXT,
        created_at TEXT
    )
    ''')
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # 清理临时数据库文件
    if os.path.exists(db_path):
        os.unlink(db_path)

@pytest.fixture
def test_files(temp_dir):
    """创建测试文件"""
    files = []
    
    # 创建测试文件1
    file1 = os.path.join(temp_dir, 'test1.txt')
    with open(file1, 'w') as f:
        f.write('test content 1')
    files.append(file1)
    
    # 创建测试文件2
    file2 = os.path.join(temp_dir, 'test2.txt')
    with open(file2, 'w') as f:
        f.write('test content 2')
    files.append(file2)
    
    # 创建重复文件
    file3 = os.path.join(temp_dir, 'test3.txt')
    with open(file3, 'w') as f:
        f.write('test content 1')  # 与file1内容相同
    files.append(file3)
    
    return files

@pytest.fixture
def mock_config():
    """模拟配置"""
    return {
        'limit_path': None,
        'excluded_patterns': []
    }
