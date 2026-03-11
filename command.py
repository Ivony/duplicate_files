import sys
import os
from database_manager import DatabaseManager
from file_scanner import FileScanner
from hash_calculator import HashCalculator
from index_manager import IndexManager
from duplicate_analyzer import DuplicateAnalyzer
from export_manager import ExportManager
from config_manager import ConfigManager
from file_cleaner import FileCleaner

class CommandInterface:
    def __init__(self, db_path='file_index.db'):
        self.db_path = db_path
        self.db_manager = DatabaseManager(db_path)
        self.config_manager = ConfigManager()
        self.analyzer = DuplicateAnalyzer(db_path)
        self.analyzer.path_limit = self.config_manager.get_limit_path()
    
    def show_help(self, command=None):
        """显示帮助信息"""
        print(f"\n重复文件分析工具")
        print(f"=" * 60)
        print(f"数据库路径: {self.db_path}")
        print(f"=" * 60)
        
        if command:
            self.show_command_help(command)
        else:
            self.show_all_help()
    
    def show_all_help(self):
        """显示所有帮助信息"""
        print(f"\n可用命令:")
        print(f"=" * 60)
        
        print(f"\nindex 指令:")
        print(f"  index scan <path>        - 扫描指定路径，将文件放入files表")
        print(f"  index full <path>       - 执行完整扫描流程：扫描 → 索引 → 哈希计算")
        print(f"  index import <csv>       - 从CSV文件导入文件列表")
        print(f"                              --encoding <编码>  指定CSV文件的字符编码（默认utf-8）")
        print(f"  index hash [group_id]   - 计算指定组或所有组的hash值")
        print(f"                              group_id: 指定组ID，可以是单个或多个（逗号分隔）")
        print(f"                              --new       仅新增模式：仅计算从未计算过hash值的文件")
        print(f"                              --force     强制更新模式：对所有文件重新计算哈希值")
        print(f"                              --extension <ext>  只计算指定扩展名的组")
        print(f"                              --size <op><size> 按文件大小过滤组（如>1000000）")
        print(f"                              --unconfirmed  只计算未确认哈希值的组")
        print(f"  index clean             - 检查并清理索引文件（删除丢失文件、更新变更文件）")
        print(f"  index clean files       - 清除文件索引，删除files表中的所有数据")
        print(f"  index clean hash        - 清除哈希数据，删除file_hash表中的所有数据")
        print(f"  index clean full        - 清除所有数据，删除files表和file_hash表中的所有数据")
        print(f"  index rebuild           - 重建索引，删除所有数据后重新扫描所有磁盘")
        print(f"  index status            - 索引状态，展示索引的文件、重复文件组数量等")
        print(f"  index list <path>       - 列举索引，显示指定路径下已经索引的文件和哈希值状态")
        
        print(f"\nanalyze 指令:")
        print(f"  analyze stat           - 显示重复文件统计信息")
        print(f"  analyze top [N] [--all] - 显示最大的N个重复文件组（默认20个）")
        print(f"                              --all 显示所有组（包括未确认哈希值的）")
        print(f"  analyze details <hash>   - 查看特定哈希值的重复文件详情")
        print(f"  analyze filter <type> <value> [--all] - 按文件类型、大小等过滤重复文件")
        print(f"                              --all 显示所有组（包括未确认哈希值的）")
        
        print(f"\nexport 指令:")
        print(f"  export csv <path>      - 导出分析结果为CSV格式")
        print(f"  export json <path>     - 导出分析结果为JSON格式")
        print(f"  export report <path>    - 生成详细的重复文件报告")
        
        print(f"\nconfig 指令:")
        print(f"  config limit <path>         - 设置检索范围限制")
        print(f"  config limit clear         - 解除检索范围限制")
        print(f"  config exclude add <pattern>    - 添加路径排除模式")
        print(f"  config exclude list        - 查看当前排除模式")
        print(f"  config exclude remove <pattern> - 移除路径排除模式")
        
        print(f"\ndb 指令:")
        print(f"  db check                - 检查数据库结构和数据")
        print(f"  db optimize             - 优化数据库性能")
        print(f"  db backup <path>        - 备份数据库")
        print(f"  db restore <path>       - 从备份恢复数据库")
        print(f"  db init [--force]       - 重建数据库结构（--force 强制重建，不询问）")
        
        print(f"\nclean 指令:")
        print(f"  clean dryrun            - 模拟清理操作，不实际删除文件")
        print(f"  clean safe              - 安全模式清理，保留每个组中最新的文件")
        print(f"  clean auto               - 自动模式清理，根据规则自动选择保留的文件")
        print(f"  clean preview            - 预览清理操作的结果")
        
        print(f"\n系统指令:")
        print(f"  help [command]          - 显示帮助信息，可指定命令查看详细帮助")
        print(f"  version                - 显示版本信息")
        print(f"  exit                   - 退出程序")
        print(f"=" * 60)
    
    def show_command_help(self, command):
        """显示特定命令的帮助"""
        help_info = {
            'index': {
                'description': '扫描与索引指令',
                'subcommands': {
                    'scan': '扫描指定路径，将文件放入files表',
                    'full': '执行完整扫描流程：扫描 → 索引 → 哈希计算',
                    'import': '从CSV文件导入文件列表',
                    'hash': '计算所有可能重复文件的hash值',
                    'clean': '清除索引数据',
                    'rebuild': '重建索引',
                    'status': '索引状态',
                    'list': '列举索引'
                }
            },
            'analyze': {
                'description': '分析指令',
                'subcommands': {
                    'stat': '显示重复文件统计信息',
                    'top': '显示最大的N个重复文件组',
                    'details': '查看特定哈希值的重复文件详情',
                    'filter': '按文件类型、大小等过滤重复文件'
                }
            },
            'export': {
                'description': '导出指令',
                'subcommands': {
                    'csv': '导出为CSV格式',
                    'json': '导出为JSON格式',
                    'report': '生成详细的重复文件报告'
                }
            },
            'config': {
                'description': '配置指令',
                'subcommands': {
                    'limit': '设置检索范围限制',
                    'exclude': '路径排除模式管理'
                }
            },
            'db': {
                'description': '数据库指令',
                'subcommands': {
                    'check': '检查数据库结构和数据',
                    'optimize': '优化数据库性能',
                    'backup': '备份数据库',
                    'restore': '从备份恢复数据库',
                    'init': '重建数据库结构'
                }
            },
            'clean': {
                'description': '清理指令',
                'subcommands': {
                    'dryrun': '模拟清理操作',
                    'safe': '安全模式清理',
                    'auto': '自动模式清理',
                    'preview': '预览清理操作'
                }
            }
        }
        
        if command in help_info:
            info = help_info[command]
            print(f"\n{command} 指令 - {info['description']}")
            print(f"=" * 60)
            for subcmd, desc in info['subcommands'].items():
                print(f"  {subcmd:<15} - {desc}")
            print(f"=" * 60)
        else:
            print(f"\n未知的命令: {command}")
            print("使用 'help' 查看所有可用命令")
    
    def execute_index_command(self, args):
        """执行index命令"""
        if not args:
            print("错误: 请指定index子命令")
            self.show_command_help('index')
            return
        
        subcommand = args[0]
        
        if subcommand == 'scan':
            if len(args) < 2:
                print("错误: 请指定要扫描的路径")
                return
            path = args[1]
            if not os.path.exists(path) or not os.path.isdir(path):
                print(f"错误: 路径不存在或不是目录: {path}")
                return
            
            scanner = FileScanner(self.db_path)
            scanner.scan_directory(path)
            
        elif subcommand == 'full':
            if len(args) < 2:
                print("错误: 请指定要扫描的路径")
                return
            path = args[1]
            if not os.path.exists(path) or not os.path.isdir(path):
                print(f"错误: 路径不存在或不是目录: {path}")
                return
            
            scanner = FileScanner(self.db_path)
            scanner.scan_directory(path)
            
            calculator = HashCalculator(self.db_path)
            calculator.calculate_hash('default')
            
        elif subcommand == 'import':
            if len(args) < 2:
                print("错误: 请指定CSV文件路径")
                return
            csv_path = args[1]
            if not os.path.exists(csv_path) or not os.path.isfile(csv_path):
                print(f"错误: CSV文件不存在: {csv_path}")
                return
            
            encoding = 'utf-8'
            if '--encoding' in args:
                idx = args.index('--encoding')
                if idx + 1 < len(args):
                    encoding = args[idx + 1]
            
            scanner = FileScanner(self.db_path)
            scanner.scan_from_csv(csv_path, encoding)
            
        elif subcommand == 'hash':
            mode = 'default'
            group_ids = None
            filters = {}
            
            # 解析参数
            remaining_args = args[1:]
            i = 0
            while i < len(remaining_args):
                arg = remaining_args[i]
                
                if arg == '--new':
                    mode = 'new'
                elif arg == '--force':
                    mode = 'force'
                elif arg == '--unconfirmed':
                    filters['unconfirmed'] = True
                elif arg == '--extension' and i + 1 < len(remaining_args):
                    filters['extension'] = remaining_args[i + 1]
                    i += 1  # 跳过参数值
                elif arg == '--size' and i + 1 < len(remaining_args):
                    filters['size'] = remaining_args[i + 1]
                    i += 1  # 跳过参数值
                elif arg.isdigit() or ',' in arg:
                    # 组ID（单个或多个）
                    try:
                        group_ids = [int(gid) for gid in arg.split(',')]
                    except ValueError:
                        print(f"错误: 无效的组ID: {arg}")
                        return
                
                i += 1
            
            calculator = HashCalculator(self.db_path)
            calculator.calculate_hash(mode, group_ids, filters)
            
        elif subcommand == 'clean':
            manager = IndexManager(self.db_path)
            
            if len(args) < 2:
                # 没有指定清理类型，执行索引清理
                manager.clean_index()
            else:
                clean_type = args[1]
                
                if clean_type == 'files':
                    manager.clean_files()
                elif clean_type == 'hash':
                    manager.clean_hash()
                elif clean_type == 'full':
                    manager.clean_full()
                else:
                    print(f"错误: 未知的清理类型: {clean_type}")
            
        elif subcommand == 'rebuild':
            manager = IndexManager(self.db_path)
            if len(args) > 1:
                scan_paths = args[1:]
                manager.rebuild_index(scan_paths)
            else:
                manager.rebuild_index()
            
        elif subcommand == 'status':
            self.db_manager.get_index_status()
            
        elif subcommand == 'list':
            if len(args) < 2:
                print("错误: 请指定路径")
                return
            
            self.db_manager.list_indexed_files(args[1])
            
        else:
            print(f"错误: 未知的index子命令: {subcommand}")
            self.show_command_help('index')
    
    def execute_analyze_command(self, args):
        """执行analyze命令"""
        if not args:
            print("错误: 请指定analyze子命令")
            self.show_command_help('analyze')
            return
        
        subcommand = args[0]
        
        if subcommand == 'stat':
            stats = self.analyzer.get_statistics()
            print(f"\n重复文件统计报告")
            print(f"=" * 60)
            print(f"总文件数: {stats['total_files']:,}")
            print(f"重复文件组数: {stats['duplicate_groups']:,}")
            print(f"重复文件关联数: {stats['duplicate_files']:,}")
            print(f"已计算哈希的文件数: {stats['hashed_files']:,}")
            print(f"待计算哈希的文件数: {stats['unhashed_files']:,}")
            print(f"总文件大小: {stats['total_size']:,} 字节 ({stats['total_size']/1024/1024/1024:.2f} GB)")
            print(f"重复文件总大小: {stats['duplicate_size']:,} 字节 ({stats['duplicate_size']/1024/1024/1024:.2f} GB)")
            print(f"\n如果删除重复文件:")
            print(f"  可以删除 {stats['duplicate_files'] - stats['duplicate_groups']} 个文件")
            print(f"  可以节省磁盘空间: {stats['duplicate_size']:,} 字节 ({stats['duplicate_size']/1024/1024/1024:.2f} GB)")
            print(f"=" * 60)
            
        elif subcommand == 'top':
            count = 20
            hash_only = True  # 默认只显示已确认哈希值的组
            
            # 解析参数
            for arg in args[1:]:
                if arg == '--all':
                    hash_only = False
                elif arg.isdigit():
                    count = int(arg)
            
            top_groups = self.analyzer.get_top_groups(count, hash_only)
            
            if hash_only:
                print(f"\n最大的{count}个已确认哈希值的重复文件组（按可释放空间排序）:")
            else:
                print(f"\n最大的{count}个重复文件组（按可释放空间排序，包括未确认哈希值的）:")
            print(f"=" * 60)
            
            if not top_groups:
                print("  没有找到符合条件的重复文件组")
                if hash_only:
                    print("\n提示: 使用 --all 参数可以查看所有组（包括未确认哈希值的）")
                    print("      运行 'index hash' 可以计算未确认组的哈希值")
            else:
                for group in top_groups:
                    print(f"\n组ID: {group['group_id']}")
                    print(f"  文件大小: {group['size']:,} 字节 ({group['size']/1024/1024:.2f} MB)")
                    print(f"  文件扩展名: {group['extension']}")
                    print(f"  文件数量: {group['file_count']} 个")
                    print(f"  总大小: {group['group_size']:,} 字节 ({group['group_size']/1024/1024/1024:.2f} GB)")
                    print(f"  可释放空间: {group['savable_space']:,} 字节 ({group['savable_space']/1024/1024/1024:.2f} GB)")
                    if group['hash']:
                        print(f"  哈希值: {group['hash']}")
                    else:
                        print(f"  哈希值: 未确认")
                    print(f"  包含的文件（前10个，按修改时间排序）:")
                    for i, (disk, filepath) in enumerate(group['files'], 1):
                        print(f"    {i}. [{disk}] {filepath}")
                    
                    if group['total_files'] > 10:
                        print(f"    ... 还有 {group['total_files'] - 10} 个文件")
            
            print(f"=" * 60)
            
        elif subcommand == 'details':
            if len(args) < 2:
                print("错误: 请指定哈希值")
                return
            
            hash_value = args[1]
            files = self.analyzer.get_duplicate_details(hash_value)
            
            print(f"\n哈希值为 {hash_value} 的重复文件:")
            print(f"=" * 60)
            if not files:
                print("  没有找到文件")
            else:
                for i, file_info in enumerate(files, 1):
                    print(f"\n{i}. 文件路径: {file_info['filepath']}")
                    print(f"   磁盘: {file_info['disk']}")
                    print(f"   大小: {file_info['size']:,} 字节")
                    print(f"   修改时间: {file_info['modified']}")
                    print(f"   哈希值: {file_info['hash']}")
                    print(f"   计算时间: {file_info['created_at']}")
            print(f"=" * 60)
            
        elif subcommand == 'filter':
            if len(args) < 3:
                print("错误: 请指定过滤类型和值")
                print("用法: analyze filter <type> <value> [--all]")
                print("  type: extension/size/path")
                print("  --all: 显示所有组（包括未确认哈希值的）")
                return
            
            filter_type = args[1]
            value = args[2]
            hash_only = '--all' not in args  # 默认只显示已确认哈希值的组
            
            groups = self.analyzer.filter_duplicates(filter_type, value, hash_only)
            
            if hash_only:
                print(f"\n过滤结果（{filter_type} = {value}，已确认哈希值的组）:")
            else:
                print(f"\n过滤结果（{filter_type} = {value}，包括未确认哈希值的组）:")
            print(f"=" * 60)
            if not groups:
                print("  没有找到匹配的重复文件组")
                if hash_only:
                    print("\n提示: 使用 --all 参数可以查看所有组（包括未确认哈希值的）")
                    print("      运行 'index hash' 可以计算未确认组的哈希值")
            else:
                for i, group in enumerate(groups, 1):
                    print(f"\n{i}. 组ID: {group['group_id']}")
                    print(f"   文件大小: {group['size']:,} 字节")
                    print(f"   文件扩展名: {group['extension']}")
                    print(f"   文件数量: {group['file_count']} 个")
                    print(f"   可释放空间: {group['savable_space']:,} 字节")
                    if group['hash']:
                        print(f"   哈希值: {group['hash']}")
                    else:
                        print(f"   哈希值: 未确认")
            print(f"=" * 60)
            
        else:
            print(f"错误: 未知的analyze子命令: {subcommand}")
            self.show_command_help('analyze')
    
    def execute_export_command(self, args):
        """执行export命令"""
        if not args:
            print("错误: 请指定export子命令")
            self.show_command_help('export')
            return
        
        subcommand = args[0]
        
        if len(args) < 2:
            print("错误: 请指定输出路径")
            return
        
        output_path = args[1]
        exporter = ExportManager(self.db_path)
        
        if subcommand == 'csv':
            exporter.export_csv(output_path)
        elif subcommand == 'json':
            exporter.export_json(output_path)
        elif subcommand == 'report':
            exporter.generate_report(output_path)
        else:
            print(f"错误: 未知的export子命令: {subcommand}")
            self.show_command_help('export')
    
    def execute_config_command(self, args):
        """执行config命令"""
        if not args:
            print("错误: 请指定config子命令")
            self.show_command_help('config')
            return
        
        subcommand = args[0]
        
        if subcommand == 'limit':
            if len(args) < 2:
                print("错误: 请指定路径或使用clear清除限制")
                return
            
            if args[1] == 'clear':
                self.config_manager.clear_limit()
                self.analyzer.path_limit = None
            else:
                if self.config_manager.set_limit(args[1]):
                    self.analyzer.path_limit = self.config_manager.get_limit_path()
            
        elif subcommand == 'exclude':
            if len(args) < 2:
                print("错误: 请指定子命令（add/list/remove）")
                return
            
            exclude_subcommand = args[1]
            
            if exclude_subcommand == 'add':
                if len(args) < 3:
                    print("错误: 请指定排除模式")
                    return
                self.config_manager.add_exclude_pattern(args[2])
            elif exclude_subcommand == 'list':
                self.config_manager.list_exclude_patterns()
            elif exclude_subcommand == 'remove':
                if len(args) < 3:
                    print("错误: 请指定排除模式")
                    return
                self.config_manager.remove_exclude_pattern(args[2])
            else:
                print(f"错误: 未知的exclude子命令: {exclude_subcommand}")
                return
            
        else:
            print(f"错误: 未知的config子命令: {subcommand}")
            self.show_command_help('config')
    
    def execute_db_command(self, args):
        """执行db命令"""
        if not args:
            print("错误: 请指定db子命令")
            self.show_command_help('db')
            return
        
        subcommand = args[0]
        
        if subcommand == 'check':
            self.db_manager.check_database()
        elif subcommand == 'optimize':
            self.db_manager.optimize_database()
        elif subcommand == 'backup':
            if len(args) < 2:
                print("错误: 请指定备份路径")
                return
            self.db_manager.backup_database(args[1])
        elif subcommand == 'restore':
            if len(args) < 2:
                print("错误: 请指定备份文件路径")
                return
            self.db_manager.restore_database(args[1])
        elif subcommand == 'init':
            force = '--force' in args
            self.db_manager.init_database(force)
        else:
            print(f"错误: 未知的db子命令: {subcommand}")
            self.show_command_help('db')
    
    def execute_clean_command(self, args):
        """执行clean命令"""
        if not args:
            print("错误: 请指定clean子命令")
            self.show_command_help('clean')
            return
        
        subcommand = args[0]
        cleaner = FileCleaner(self.db_path)
        
        if subcommand == 'dryrun':
            cleaner.dryrun_clean()
        elif subcommand == 'safe':
            cleaner.safe_clean()
        elif subcommand == 'auto':
            cleaner.auto_clean()
        elif subcommand == 'preview':
            cleaner.preview_clean()
        else:
            print(f"错误: 未知的clean子命令: {subcommand}")
            self.show_command_help('clean')
    
    def run(self):
        """运行交互式界面"""
        print("重复文件分析工具")
        print(f"=" * 60)
        print(f"数据库路径: {self.db_path}")
        print(f"=" * 60)
        
        self.show_help()
        
        while True:
            try:
                command = input("\n请输入命令 (输入 help 查看帮助): ").strip()
                
                if not command:
                    continue
                
                parts = command.split()
                if not parts:
                    continue
                
                main_command = parts[0].lower()
                args = parts[1:]
                
                if main_command in ('exit', 'quit', 'q'):
                    print("感谢使用重复文件分析工具！")
                    break
                elif main_command == 'help' or main_command == 'h' or main_command == '?':
                    if args:
                        self.show_command_help(args[0])
                    else:
                        self.show_help()
                elif main_command == 'version':
                    print("重复文件分析工具 v2.0")
                    print("重构版本 - 支持新的指令系统和模块化架构")
                elif main_command == 'index':
                    self.execute_index_command(args)
                elif main_command == 'analyze':
                    self.execute_analyze_command(args)
                elif main_command == 'export':
                    self.execute_export_command(args)
                elif main_command == 'config':
                    self.execute_config_command(args)
                elif main_command == 'db':
                    self.execute_db_command(args)
                elif main_command == 'clean':
                    self.execute_clean_command(args)
                else:
                    print(f"未知命令: {main_command}，输入 help 查看帮助")
                    
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