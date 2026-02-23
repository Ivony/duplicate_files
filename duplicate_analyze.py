import sqlite3
import sys

class DuplicateAnalyzer:
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
        
    def load_data(self):
        print("正在加载数据...")
        conn = sqlite3.connect(self.db_path, timeout=60.0, isolation_level='IMMEDIATE')
        cursor = conn.cursor()
        
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
        import os
        return os.path.splitdrive(filepath)[0].upper()
    
    def show_stat(self):
        print(f"\n重复文件统计报告")
        print(f"=" * 60)
        print(f"总共有 {self.total_groups} 组重复的文件")
        print(f"包含重复文件最多的组包含了 {self.max_files_in_group} 个文件")
        print(f"重复文件总数: {self.total_files} 个")
        print(f"重复文件总大小: {self.total_size:,} 字节 ({self.total_size/1024/1024/1024:.2f} GB)")
        print(f"平均每组文件数: {self.avg_count:.2f}")
        print(f"\n如果将这些组里面的文件都删除到只剩一个:")
        print(f"  可以删除 {self.total_deletable_files} 个文件")
        print(f"  可以节省磁盘空间: {self.total_savable_space:,} 字节 ({self.total_savable_space/1024/1024/1024:.2f} GB)")
        print(f"=" * 60)
    
    def show_top_groups(self, count=20):
        print(f"\n最大的{count}个重复文件组（按可释放空间排序）:")
        print(f"=" * 60)
        
        for i, (hash_value, file_size, file_count) in enumerate(self.duplicate_groups[:count], 1):
            group_size = file_size * file_count
            savable_space = (file_count - 1) * file_size
            print(f"\n{i}. 哈希: {hash_value[:16]}...")
            print(f"   文件大小: {file_size:,} 字节 ({file_size/1024/1024:.2f} MB)")
            print(f"   文件数量: {file_count} 个")
            print(f"   总大小: {group_size:,} 字节 ({group_size/1024/1024/1024:.2f} GB)")
            print(f"   可释放空间: {savable_space:,} 字节 ({savable_space/1024/1024/1024:.2f} GB)")
            
            files = self.get_duplicate_files_by_hash(hash_value)
            print(f"   包含的文件（前10个，按修改时间排序）:")
            for j, (filepath, size, modified) in enumerate(files[:10], 1):
                disk = self.extract_disk_from_path(filepath)
                print(f"     {j}. [{disk}] {filepath}")
            
            if file_count > 10:
                print(f"     ... 还有 {file_count - 10} 个文件")
        
        print(f"=" * 60)
    
    def show_help(self):
        print(f"\n可用命令:")
        print(f"=" * 60)
        print(f"  stat      - 显示重复文件统计信息")
        print(f"  top [N]   - 显示最大的N个重复文件组（默认20个）")
        print(f"  help      - 显示此帮助信息")
        print(f"  quit      - 退出程序")
        print(f"=" * 60)
    
    def run(self):
        print("重复文件分析工具")
        print(f"=" * 60)
        print(f"数据库路径: {self.db_path}")
        print(f"=" * 60)
        
        self.load_data()
        self.show_help()
        
        while True:
            try:
                command = input("\n请输入命令 (输入 help 查看帮助): ").strip().lower()
                
                if not command:
                    continue
                
                if command == 'quit' or command == 'exit' or command == 'q':
                    print("感谢使用重复文件分析工具！")
                    break
                elif command == 'help' or command == 'h' or command == '?':
                    self.show_help()
                elif command == 'stat' or command == 's':
                    self.show_stat()
                elif command.startswith('top '):
                    try:
                        parts = command.split()
                        if len(parts) > 1:
                            count = int(parts[1])
                            self.show_top_groups(count)
                        else:
                            self.show_top_groups(20)
                    except ValueError:
                        print("错误：请输入有效的数字")
                elif command == 'top':
                    self.show_top_groups(20)
                else:
                    print(f"未知命令: {command}，输入 help 查看帮助")
                    
            except KeyboardInterrupt:
                print("\n\n感谢使用重复文件分析工具！")
                break
            except Exception as e:
                print(f"错误: {e}")

def main():
    db_path = 'file_index.db'
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    analyzer = DuplicateAnalyzer(db_path)
    analyzer.run()

if __name__ == '__main__':
    main()