import sys
import os
from duplicate_finder import DuplicateFinder
from hash_calculator import populate_hash_table, show_statistics
from database_manager import check_database
from file_scanner import FileScanner

class CommandInterface:
    def __init__(self, db_path):
        self.db_path = db_path
        self.finder = DuplicateFinder(db_path)
    
    def show_help(self):
        print(f"\n可用命令:")
        print(f"=" * 60)
        print(f"  stat      - 显示重复文件统计信息")
        print(f"  top [N]   - 显示最大的N个重复文件组（默认20个）")
        print(f"  limit [PATH] - 限制检索范围到指定路径（如 C: 或 C:\\Users）")
        print(f"              不带参数时解除限制")
        print(f"  scan [PATH] - 扫描指定路径下的所有文件并建立索引")
        print(f"  hash      - 计算文件哈希并填充Hash表")
        print(f"  hashstat  - 显示哈希表统计信息")
        print(f"  dbcheck   - 检查数据库结构和数据")
        print(f"  help      - 显示此帮助信息")
        print(f"  quit      - 退出程序")
        print(f"=" * 60)
    
    def show_stat(self):
        stats = self.finder.get_statistics()
        print(f"\n重复文件统计报告")
        print(f"=" * 60)
        if self.finder.path_limit:
            print(f"当前限制范围: {self.finder.path_limit}")
        print(f"总共有 {stats['total_groups']} 组重复的文件")
        print(f"包含重复文件最多的组包含了 {stats['max_files_in_group']} 个文件")
        print(f"重复文件总数: {stats['total_files']} 个")
        print(f"重复文件总大小: {stats['total_size']:,} 字节 ({stats['total_size']/1024/1024/1024:.2f} GB)")
        print(f"平均每组文件数: {stats['avg_count']:.2f}")
        print(f"\n如果将这些组里面的文件都删除到只剩一个:")
        print(f"  可以删除 {stats['total_deletable_files']} 个文件")
        print(f"  可以节省磁盘空间: {stats['total_savable_space']:,} 字节 ({stats['total_savable_space']/1024/1024/1024:.2f} GB)")
        print(f"=" * 60)
    
    def show_top_groups(self, count=20):
        print(f"\n最大的{count}个重复文件组（按可释放空间排序）:")
        print(f"=" * 60)
        if self.finder.path_limit:
            print(f"当前限制范围: {self.finder.path_limit}")
        
        top_groups = self.finder.get_top_groups(count)
        for group in top_groups:
            print(f"\n{group['index']}. 哈希: {group['hash'][:16]}...")
            print(f"   文件大小: {group['file_size']:,} 字节 ({group['file_size']/1024/1024:.2f} MB)")
            print(f"   文件数量: {group['file_count']} 个")
            print(f"   总大小: {group['group_size']:,} 字节 ({group['group_size']/1024/1024/1024:.2f} GB)")
            print(f"   可释放空间: {group['savable_space']:,} 字节 ({group['savable_space']/1024/1024/1024:.2f} GB)")
            
            print(f"   包含的文件（前10个，按修改时间排序）:")
            for j, (disk, filepath) in enumerate(group['files'], 1):
                print(f"     {j}. [{disk}] {filepath}")
            
            if group['total_files'] > 10:
                print(f"     ... 还有 {group['total_files'] - 10} 个文件")
        
        print(f"=" * 60)
    
    def run(self):
        print("重复文件分析工具")
        print(f"=" * 60)
        print(f"数据库路径: {self.db_path}")
        print(f"=" * 60)
        
        self.finder.load_data()
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
                elif command.startswith('limit '):
                    parts = command.split(maxsplit=1)
                    if len(parts) > 1:
                        new_path = parts[1].strip()
                        if new_path:
                            self.finder.path_limit = new_path
                            print(f"已设置检索范围限制: {self.finder.path_limit}")
                            self.finder.load_data()
                        else:
                            self.finder.path_limit = None
                            print("已解除检索范围限制")
                            self.finder.load_data()
                    else:
                        if self.finder.path_limit:
                            print(f"已解除检索范围限制（原限制: {self.finder.path_limit}）")
                            self.finder.path_limit = None
                            self.finder.load_data()
                        else:
                            print("当前没有设置检索范围限制")
                elif command == 'limit':
                    if self.finder.path_limit:
                        print(f"已解除检索范围限制（原限制: {self.finder.path_limit}）")
                        self.finder.path_limit = None
                        self.finder.load_data()
                    else:
                        print("当前没有设置检索范围限制")
                elif command == 'hash':
                    print("开始计算文件哈希并填充Hash表...")
                    populate_hash_table(self.db_path)
                    print("哈希计算完成！重新加载数据...")
                    self.finder.load_data()
                elif command == 'hashstat':
                    show_statistics(self.db_path)
                elif command == 'dbcheck':
                    check_database(self.db_path)
                elif command.startswith('scan '):
                    parts = command.split(maxsplit=1)
                    if len(parts) > 1:
                        path = parts[1].strip()
                        if os.path.exists(path) and os.path.isdir(path):
                            scanner = FileScanner(self.db_path)
                            scanner.scan_directory(path)
                            print("扫描完成！重新加载数据...")
                            self.finder.load_data()
                        else:
                            print(f"错误：路径不存在或不是目录: {path}")
                    else:
                        print("错误：请指定要扫描的路径")
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
    
    interface = CommandInterface(db_path)
    interface.run()

if __name__ == '__main__':
    main()