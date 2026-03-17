import pytest
import os
import tempfile
import sqlite3
from core.database import DatabaseManager, set_db_path

@pytest.fixture
def temp_dir():
    """创建临时目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture
def temp_db(tmp_path):
    """创建临时数据库（使用与实际数据库相同的结构）"""
    db_path = str(tmp_path / "test.db")
    
    db_manager = DatabaseManager(db_path)
    db_manager.init_database(force=True)
    
    yield db_path

@pytest.fixture(autouse=True)
def isolate_db(temp_db, monkeypatch):
    """自动隔离数据库，确保测试不会影响实际数据库"""
    import core.database
    monkeypatch.setattr(core.database, 'DB_PATH', temp_db)
    monkeypatch.setattr(core.database, 'get_db_path', lambda: temp_db)
    yield

@pytest.fixture
def test_filesystem(temp_dir):
    """创建专用于单元测试的文件系统
    
    包含：
    - 普通文件
    - 重复文件组（相同内容）
    - 不同扩展名的文件
    - 不同大小的文件
    """
    fs = {
        'root': temp_dir,
        'files': {},
        'duplicate_groups': []
    }
    
    file1 = os.path.join(temp_dir, 'unique1.txt')
    with open(file1, 'w') as f:
        f.write('unique content 1')
    fs['files']['unique1'] = file1
    
    file2 = os.path.join(temp_dir, 'unique2.txt')
    with open(file2, 'w') as f:
        f.write('unique content 2')
    fs['files']['unique2'] = file2
    
    dup_content = 'duplicate content for testing'
    dup_files = []
    for i in range(3):
        dup_file = os.path.join(temp_dir, f'duplicate_{i}.txt')
        with open(dup_file, 'w') as f:
            f.write(dup_content)
        dup_files.append(dup_file)
        fs['files'][f'duplicate_{i}'] = dup_file
    fs['duplicate_groups'].append({
        'files': dup_files,
        'content': dup_content,
        'size': len(dup_content)
    })
    
    large_content = 'x' * 10000
    large_dup_files = []
    for i in range(2):
        large_file = os.path.join(temp_dir, f'large_dup_{i}.dat')
        with open(large_file, 'w') as f:
            f.write(large_content)
        large_dup_files.append(large_file)
        fs['files'][f'large_dup_{i}'] = large_file
    fs['duplicate_groups'].append({
        'files': large_dup_files,
        'content': large_content,
        'size': len(large_content)
    })
    
    json_file = os.path.join(temp_dir, 'data.json')
    with open(json_file, 'w') as f:
        f.write('{"key": "value"}')
    fs['files']['data_json'] = json_file
    
    return fs

@pytest.fixture
def test_db_with_data(temp_db, test_filesystem):
    """创建包含测试数据的数据库
    
    包含：
    - files 表中的文件记录
    - duplicate_groups 表中的重复组
    - duplicate_files 表中的关联
    """
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    for name, filepath in test_filesystem['files'].items():
        stat = os.stat(filepath)
        cursor.execute('''
            INSERT OR REPLACE INTO files (Filename, Extension, Size, Created, Modified, Accessed)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            filepath,
            os.path.splitext(filepath)[1] or '',
            stat.st_size,
            str(stat.st_ctime),
            str(stat.st_mtime),
            str(stat.st_atime)
        ))
    
    for group_idx, group in enumerate(test_filesystem['duplicate_groups']):
        cursor.execute('''
            INSERT INTO duplicate_groups (Size, Extension, Hash)
            VALUES (?, ?, ?)
        ''', (group['size'], '.txt', None))
        group_id = cursor.lastrowid
        
        for filepath in group['files']:
            cursor.execute('''
                INSERT INTO duplicate_files (Filepath, Group_ID)
                VALUES (?, ?)
            ''', (filepath, group_id))
    
    conn.commit()
    conn.close()
    
    return temp_db

@pytest.fixture
def test_db_with_hash(temp_db, test_filesystem):
    """创建包含哈希数据的数据库
    
    在 test_db_with_data 基础上，添加部分文件的哈希值
    """
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    for name, filepath in test_filesystem['files'].items():
        stat = os.stat(filepath)
        cursor.execute('''
            INSERT OR REPLACE INTO files (Filename, Extension, Size, Created, Modified, Accessed)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            filepath,
            os.path.splitext(filepath)[1] or '',
            stat.st_size,
            str(stat.st_ctime),
            str(stat.st_mtime),
            str(stat.st_atime)
        ))
    
    for group_idx, group in enumerate(test_filesystem['duplicate_groups']):
        import hashlib
        hash_value = hashlib.md5(group['content'].encode()).hexdigest()
        
        cursor.execute('''
            INSERT INTO duplicate_groups (Size, Extension, Hash)
            VALUES (?, ?, ?)
        ''', (group['size'], '.txt', hash_value if group_idx == 0 else None))
        group_id = cursor.lastrowid
        
        for filepath in group['files']:
            cursor.execute('''
                INSERT INTO duplicate_files (Filepath, Group_ID)
                VALUES (?, ?)
            ''', (filepath, group_id))
            
            if group_idx == 0:
                cursor.execute('''
                    INSERT OR REPLACE INTO file_hash (Filepath, Size, Hash, Modified, created_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                ''', (filepath, group['size'], hash_value, str(os.stat(filepath).st_mtime)))
    
    conn.commit()
    conn.close()
    
    return temp_db
