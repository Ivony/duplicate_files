import sqlite3
import os

class DuplicateFinder:
    def __init__(self, db_path):
        self.db_path = db_path
        self.duplicate_groups = []
        self.total_groups = 0
        self.total_files = 0
        self.total_size = 0
        self.max_files_in_group = 0
        self.total_deletable_files = 0
        self.total_savable_space = 0
        self.avg_count = 0
        self.path_limit = None
        
    def reset_stats(self):
        self.duplicate_groups = []
        self.total_groups = 0
        self.total_files = 0
        self.total_size = 0
        self.max_files_in_group = 0
        self.total_deletable_files = 0
        self.total_savable_space = 0
        self.avg_count = 0

    def load_data(self):
        self.reset_stats()
        print("正在加载数据...")
        conn = sqlite3.connect(self.db_path, timeout=60.0, isolation_level='IMMEDIATE')
        cursor = conn.cursor()
        
        if self.path_limit:
            print(f"限制检索范围: {self.path_limit}")
            cursor.execute('''
            SELECT Hash, Size, COUNT(*) as count
            FROM Hash
            WHERE Hash != '' AND Hash IS NOT NULL AND Filepath LIKE ?
            GROUP BY Hash, Size
            HAVING count > 1
            ORDER BY (count - 1) * Size DESC
            ''', (f"{self.path_limit}%",))
        else:
            cursor.execute('''
            SELECT Hash, Size, COUNT(*) as count
            FROM Hash
            WHERE Hash != '' AND Hash IS NOT NULL
            GROUP BY Hash, Size
            HAVING count > 1
            ORDER BY (count - 1) * Size DESC
            ''')
        
        self.duplicate_groups = cursor.fetchall()
        self.total_groups = len(self.duplicate_groups)
        
        for hash_value, file_size, file_count in self.duplicate_groups:
            self.total_files += file_count
            self.total_size += file_size * file_count
            self.max_files_in_group = max(self.max_files_in_group, file_count)
            self.total_deletable_files += (file_count - 1)
            self.total_savable_space += (file_count - 1) * file_size
        
        self.avg_count = self.total_files / self.total_groups if self.total_groups > 0 else 0
        
        conn.close()
        print(f"数据加载完成！找到 {self.total_groups} 个重复文件组")
    
    def get_duplicate_files_by_hash(self, hash_value):
        conn = sqlite3.connect(self.db_path, timeout=60.0, isolation_level='IMMEDIATE')
        cursor = conn.cursor()
        
        if self.path_limit:
            cursor.execute('''
            SELECT Filepath, Size, Modified
            FROM Hash
            WHERE Hash = ? AND Filepath LIKE ?
            ORDER BY Modified DESC
            ''', (hash_value, f"{self.path_limit}%"))
        else:
            cursor.execute('''
            SELECT Filepath, Size, Modified
            FROM Hash
            WHERE Hash = ?
            ORDER BY Modified DESC
            ''', (hash_value,))
        
        files = cursor.fetchall()
        conn.close()
        
        return files
    
    def extract_disk_from_path(self, filepath):
        return os.path.splitdrive(filepath)[0].upper()
    
    def get_statistics(self):
        return {
            'total_groups': self.total_groups,
            'max_files_in_group': self.max_files_in_group,
            'total_files': self.total_files,
            'total_size': self.total_size,
            'avg_count': self.avg_count,
            'total_deletable_files': self.total_deletable_files,
            'total_savable_space': self.total_savable_space
        }
    
    def get_top_groups(self, count=20):
        top_groups = []
        for i, (hash_value, file_size, file_count) in enumerate(self.duplicate_groups[:count], 1):
            group_size = file_size * file_count
            savable_space = (file_count - 1) * file_size
            files = self.get_duplicate_files_by_hash(hash_value)
            disk_files = [(self.extract_disk_from_path(filepath), filepath) for filepath, size, modified in files[:10]]
            
            top_groups.append({
                'index': i,
                'hash': hash_value,
                'file_size': file_size,
                'file_count': file_count,
                'group_size': group_size,
                'savable_space': savable_space,
                'files': disk_files,
                'total_files': len(files)
            })
        
        return top_groups