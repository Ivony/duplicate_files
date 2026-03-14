DB_PATH = 'file_index.db'

def get_db_path():
    """获取数据库路径"""
    return DB_PATH

def set_db_path(path):
    """设置数据库路径（用于测试）"""
    global DB_PATH
    DB_PATH = path
