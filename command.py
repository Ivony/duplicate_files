import sys
import os
from database_manager import DatabaseManager
from file_scanner import FileScanner
from hash_calculator import HashCalculator
from index_manager import IndexManager
from data_viewer import DataViewer
from export_manager import ExportManager
from config_manager import ConfigManager
from file_cleaner import FileCleaner

class CommandInterface:
    def __init__(self, db_path='file_index.db'):
        self.db_path = db_path
        self.db_manager = DatabaseManager(db_path)
        self.config_manager = ConfigManager()
        self.analyzer = DataViewer(db_path)
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
        print(f"                              扫描后会自动重建重复文件组")
        print(f"  index import <csv>       - 从CSV文件导入文件列表")
        print(f"                              导入后会自动重建重复文件组")
        print(f"                              --encoding <编码>  指定CSV文件的字符编码（默认utf-8）")
        print(f"  index rebuild            - 重建重复文件组（按扩展名和大小分组）")
        print(f"  index hash [group_id]   - 计算指定组或所有组的hash值")
        print(f"                              group_id: 指定组ID，可以是单个或多个（逗号分隔）")
        print(f"                              --new       仅新增模式：仅计算从未计算过hash值的文件")
        print(f"                              --force     强制更新模式：对所有文件重新计算哈希值")
        print(f"                              --verify    验证模式：验证组的哈希值是否与所有文件一致")
        print(f"                              --extension <ext>  只计算指定扩展名的组")
        print(f"                              --size <op><size> 按文件大小过滤组（如>1000000）")
        print(f"                              --unconfirmed  只计算未确认哈希值的组")
        print(f"  index clean             - 检查并清理索引文件（删除丢失文件、更新变更文件）")
        print(f"  index clean files       - 清除文件索引，删除files表中的所有数据")
        print(f"  index clean hash        - 清除哈希数据，删除file_hash表中的所有数据")
        print(f"  index clean full        - 清除所有数据，删除files表和file_hash表中的所有数据")
        
        print(f"\nshow 指令:")
        print(f"  show groups [options]     - 显示重复文件组列表")
        print(f"    options:")
        print(f"      --top N               - 显示最大的N个组（默认20）")
        print(f"      --min-size <size>     - 只显示大于指定大小的组")
        print(f"      --max-size <size>     - 只显示小于指定大小的组")
        print(f"      --extension <ext>     - 只显示指定扩展名的组")
        print(f"      --unconfirmed         - 包括未确认哈希值的组")
        print(f"      --sort size|count|path - 排序方式（默认size）")
        print(f"      --detail <id>         - 显示指定组的详细信息")
        print(f"  show files <pattern|path> [options] - 查询文件")
        print(f"                              支持路径: E:\\Downloads")
        print(f"                              支持模式: *.mp4, E:\\Downloads\\*.mp4")
        print(f"                              options:")
        print(f"                                --all       显示所有文件（包括非重复）")
        print(f"                                --hash      显示哈希状态和哈希值")
        print(f"                                --limit N   限制显示数量（默认100）")
        print(f"  show hash <hash>          - 显示指定哈希值的所有文件")
        print(f"  show stats [options]      - 显示统计分析（无参数时显示数据汇总）")
        print(f"    options:")
        print(f"      --by-extension        - 按扩展名统计")
        print(f"      --by-size-range       - 按大小范围统计")
        print(f"      --by-date             - 按日期统计")
        
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
        print(f"  db backup <path> [--hash-only]  - 备份数据库")
        print(f"                            默认: 备份整个数据库(.db)")
        print(f"                            --hash-only: 只备份file_hash表(.csv)")
        print(f"  db restore <path> [--hash-only] [--merge]  - 恢复数据库")
        print(f"                            默认: 恢复整个数据库")
        print(f"                            --hash-only: 只恢复file_hash表")
        print(f"                            --merge: 合并模式（保留现有数据）")
        print(f"  db init [--force]       - 重建数据库结构（--force 强制重建，不询问）")
        
        print(f"\nclean 指令:")
        print(f"  clean [选项] [排序策略]  - 清理重复文件")
        print(f"    选项:")
        print(f"      --dryrun            - 模拟执行，不实际删除文件")
        print(f"      --script [path]     - 生成删除脚本，不实际删除文件")
        print(f"                            path: 脚本文件路径（可选，根据扩展名自动判断类型）")
        print(f"                            支持: .cmd/.bat (CMD), .sh/.bash (Bash), .ps1 (PowerShell)")
        print(f"      --yes, -y           - 自动确认，不询问")
        print(f"      --group <ids>       - 只清理指定的组ID（多个ID用逗号分隔）")
        print(f"      --min-size <size>   - 只清理大于指定大小的文件组（支持K/M/G单位）")
        print(f"      --max-size <size>   - 只清理小于指定大小的文件组（支持K/M/G单位）")
        print(f"    排序策略:")
        print(f"      --keep-newest           - 保留最新文件 (默认)")
        print(f"      --keep-oldest           - 保留最旧文件")
        print(f"      --keep-longest-name     - 保留文件名最长的文件")
        print(f"      --keep-shortest-name    - 保留文件名最短的文件")
        print(f"      --keep-longest-path     - 保留路径最长的文件")
        print(f"      --keep-shortest-path    - 保留路径最短的文件")
        print(f"      --keep-first-alpha-name - 按文件名字母顺序保留第一个")
        print(f"      --keep-last-alpha-name  - 按文件名字母顺序保留最后一个")
        print(f"      --keep-first-alpha-path - 按路径字母顺序保留第一个")
        print(f"      --keep-last-alpha-path  - 按路径字母顺序保留最后一个")
        print(f"      --keep-deepest          - 保留目录最深的文件")
        print(f"      --keep-shallowest       - 保留目录最浅的文件")
        
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
                    'scan': '扫描指定路径，将文件放入files表（自动重建重复文件组）',
                    'import': '从CSV文件导入文件列表（自动重建重复文件组）',
                    'rebuild': '重建重复文件组（按扩展名和大小分组）',
                    'hash': '计算所有可能重复文件的hash值',
                    'clean': '清除索引数据'
                }
            },
            'show': {
                'description': '显示数据指令',
                'usage': 'show <子命令> [选项]',
                'subcommands': {
                    'groups [options]': '显示重复文件组列表（使用 --detail <id> 查看组详情）',
                    'files <pattern|path> [options]': '查询文件（支持路径或模式）',
                    'hash <hash>': '显示指定哈希值的所有文件',
                    'stats [options]': '显示统计分析（无参数时显示数据汇总）'
                },
                'files_options': {
                    '--all': '显示所有文件（包括非重复）',
                    '--hash': '显示哈希状态和哈希值',
                    '--limit N': '限制显示数量（默认100）'
                },
                'group_options': {
                    '--top N': '显示最大的N个组（默认20）',
                    '--min-size <size>': '只显示大于指定大小的组',
                    '--max-size <size>': '只显示小于指定大小的组',
                    '--extension <ext>': '只显示指定扩展名的组',
                    '--unconfirmed': '包括未确认哈希值的组',
                    '--sort size|count|path': '排序方式（默认size）'
                },
                'stats_options': {
                    '--by-extension': '按扩展名统计',
                    '--by-size-range': '按大小范围统计',
                    '--by-date': '按日期统计'
                },
                'files_examples': [
                    'E:\\Downloads - 查询路径下的所有文件',
                    '*.mp4 - 查询所有mp4文件',
                    'E:\\Downloads\\*.mp4 - 查询Downloads目录下的mp4文件',
                    'E:\\Downloads --all --hash - 查询路径下所有文件及哈希状态'
                ]
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
                    'backup <path> [--hash-only]': '备份数据库（--hash-only只备份哈希表）',
                    'restore <path> [--hash-only] [--merge]': '恢复数据库（--hash-only只恢复哈希表，--merge合并模式）',
                    'init': '重建数据库结构'
                }
            },
            'clean': {
                'description': '清理指令',
                'usage': 'clean [选项] [排序策略]',
                'options': {
                    '--dryrun': '模拟执行，不实际删除文件',
                    '--script [path]': '生成删除脚本，不实际删除文件（支持.cmd/.sh/.ps1）',
                    '--yes, -y': '自动确认，不询问',
                    '--group <ids>': '只清理指定的组ID（多个ID用逗号分隔）',
                    '--min-size <size>': '只清理大于指定大小的文件组（支持K/M/G单位）',
                    '--max-size <size>': '只清理小于指定大小的文件组（支持K/M/G单位）'
                },
                'strategies': {
                    '--keep-newest': '保留最新文件 (默认)',
                    '--keep-oldest': '保留最旧文件',
                    '--keep-longest-name': '保留文件名最长的文件',
                    '--keep-shortest-name': '保留文件名最短的文件',
                    '--keep-longest-path': '保留路径最长的文件',
                    '--keep-shortest-path': '保留路径最短的文件',
                    '--keep-first-alpha-name': '按文件名字母顺序保留第一个',
                    '--keep-last-alpha-name': '按文件名字母顺序保留最后一个',
                    '--keep-first-alpha-path': '按路径字母顺序保留第一个',
                    '--keep-last-alpha-path': '按路径字母顺序保留最后一个',
                    '--keep-deepest': '保留目录最深的文件',
                    '--keep-shallowest': '保留目录最浅的文件'
                }
            }
        }
        
        if command in help_info:
            info = help_info[command]
            print(f"\n{command} 指令 - {info['description']}")
            print(f"=" * 60)
            
            # 显示用法
            if 'usage' in info:
                print(f"用法: {info['usage']}")
                print()
            
            # 显示子命令（旧格式）
            if 'subcommands' in info:
                print("子命令:")
                for subcmd, desc in info['subcommands'].items():
                    print(f"  {subcmd:<15} - {desc}")
                print()
            
            # 显示选项（新格式）
            if 'options' in info:
                print("选项:")
                for opt, desc in info['options'].items():
                    print(f"  {opt:<20} - {desc}")
                print()
            
            # 显示排序策略（新格式）
            if 'strategies' in info:
                print("排序策略:")
                for strat, desc in info['strategies'].items():
                    print(f"  {strat:<25} - {desc}")
                print()
            
            # 显示group_options（show特有）
            if 'group_options' in info:
                print("groups选项:")
                for opt, desc in info['group_options'].items():
                    print(f"  {opt:<25} - {desc}")
                print()
            
            # 显示stats_options（show特有）
            if 'stats_options' in info:
                print("stats选项:")
                for opt, desc in info['stats_options'].items():
                    print(f"  {opt:<25} - {desc}")
                print()
            
            # 显示筛选示例（show特有）
            if 'filter_examples' in info:
                print("files筛选示例:")
                for example in info['filter_examples']:
                    print(f"  {example}")
                print()
            
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
            
            # 自动重建重复文件组
            self._rebuild_duplicate_groups()
            
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
            
            # 自动重建重复文件组
            self._rebuild_duplicate_groups()
            
        elif subcommand == 'rebuild':
            # 重建重复文件组
            self._rebuild_duplicate_groups()
            
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
                elif arg == '--verify':
                    mode = 'verify'
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
            
        else:
            print(f"错误: 未知的index子命令: {subcommand}")
            self.show_command_help('index')
    
    def execute_show_command(self, args):
        """执行show命令"""
        if not args:
            print("错误: 请指定show子命令")
            self.show_command_help('show')
            return
        
        subcommand = args[0]
        
        if subcommand == 'groups':
            # 显示重复文件组列表或指定组的详细信息
            count = 20
            hash_only = True
            min_size = None
            max_size = None
            extension = None
            sort_by = 'size'
            detail_id = None
            
            # 解析参数
            i = 1
            while i < len(args):
                arg = args[i]
                if arg == '--top' and i + 1 < len(args):
                    count = int(args[i + 1])
                    i += 1
                elif arg == '--unconfirmed':
                    hash_only = False
                elif arg == '--min-size' and i + 1 < len(args):
                    size_str = args[i + 1]
                    min_size = self._parse_size(size_str)
                    i += 1
                elif arg == '--max-size' and i + 1 < len(args):
                    size_str = args[i + 1]
                    max_size = self._parse_size(size_str)
                    i += 1
                elif arg == '--extension' and i + 1 < len(args):
                    extension = args[i + 1]
                    i += 1
                elif arg == '--sort' and i + 1 < len(args):
                    sort_by = args[i + 1]
                    i += 1
                elif arg == '--detail' and i + 1 < len(args):
                    try:
                        detail_id = int(args[i + 1])
                    except ValueError:
                        print(f"错误: 无效的组ID: {args[i + 1]}")
                        return
                    i += 1
                i += 1
            
            # 如果指定了 --detail，显示组详情
            if detail_id is not None:
                self._show_group_detail(detail_id)
                return
            
            # 获取组列表
            groups = self.analyzer.get_groups_list(
                count=count,
                hash_only=hash_only,
                min_size=min_size,
                max_size=max_size,
                extension=extension,
                sort_by=sort_by
            )
            
            print(f"\n重复文件组列表")
            print(f"=" * 60)
            
            if not groups:
                print("  没有找到符合条件的重复文件组")
            else:
                for group in groups:
                    print(f"\n组ID: {group['group_id']}")
                    print(f"  文件大小: {group['size']:,} 字节 ({group['size']/1024/1024:.2f} MB)")
                    print(f"  文件扩展名: {group['extension']}")
                    print(f"  文件数量: {group['file_count']} 个")
                    print(f"  可释放空间: {group['savable_space']:,} 字节 ({group['savable_space']/1024/1024/1024:.2f} GB)")
                    if group['hash']:
                        print(f"  哈希值: {group['hash']}")
                    else:
                        print(f"  哈希值: 未确认")
            
            print(f"=" * 60)
            
        elif subcommand == 'files':
            # 统一的文件查询指令
            if len(args) < 2:
                print("错误: 请指定路径或模式")
                return
            
            pattern = args[1]
            show_all = False
            show_hash = False
            limit = 100
            
            # 解析选项
            i = 2
            while i < len(args):
                arg = args[i]
                if arg == '--all':
                    show_all = True
                elif arg == '--hash':
                    show_hash = True
                elif arg == '--limit' and i + 1 < len(args):
                    try:
                        limit = int(args[i + 1])
                        i += 1
                    except ValueError:
                        print(f"错误: 无效的限制数量: {args[i + 1]}")
                        return
                i += 1
            
            # 判断是路径还是模式（包含通配符）
            has_wildcard = '*' in pattern or '?' in pattern
            
            if has_wildcard:
                # 模式搜索：查找重复文件组
                groups = self.analyzer.filter_by_pattern(pattern, hash_only=True)
                
                print(f"\n文件搜索结果（模式: {pattern}）")
                print(f"=" * 60)
                
                if not groups:
                    print("  没有找到匹配的文件")
                else:
                    print(f"  找到 {len(groups)} 个匹配的重复文件组")
                    for i, group in enumerate(groups[:limit], 1):
                        print(f"\n{i}. 组ID: {group['group_id']}")
                        print(f"   文件大小: {group['size']:,} 字节")
                        print(f"   文件扩展名: {group['extension']}")
                        print(f"   文件数量: {group['file_count']} 个")
                        print(f"   匹配的文件:")
                        for j, filepath in enumerate(group['matched_files'][:5], 1):
                            print(f"     {j}. {filepath}")
                        if len(group['matched_files']) > 5:
                            print(f"     ... 还有 {len(group['matched_files']) - 5} 个匹配文件")
                    
                    if len(groups) > limit:
                        print(f"\n... 还有 {len(groups) - limit} 个组未显示（使用 --limit {limit + 20} 显示更多）")
                
                print(f"=" * 60)
            else:
                # 路径查询：显示已索引的文件
                if show_all:
                    # 显示所有已索引文件
                    conn = self.db_manager.get_connection()
                    cursor = conn.cursor()
                    
                    query = '''
                        SELECT f.Filename, f.Size, f.Modified, fh.Hash, fh.created_at
                        FROM files f
                        LEFT JOIN file_hash fh ON f.Filename = fh.Filepath
                        WHERE f.Filename LIKE ?
                        ORDER BY f.Filename
                        LIMIT ?
                    '''
                    cursor.execute(query, (f"{pattern}%", limit))
                    files = cursor.fetchall()
                    conn.close()
                    
                    print(f"\n路径 {pattern} 下已索引的文件:")
                    if not files:
                        print("  没有找到已索引的文件")
                    else:
                        for i, (filename, size, modified, hash_val, created_at) in enumerate(files, 1):
                            hash_status = "已计算" if hash_val else "未计算"
                            print(f"  {i}. {filename}")
                            print(f"     大小: {size:,} 字节, 修改时间: {modified}, 哈希状态: {hash_status}")
                            if show_hash and hash_val:
                                print(f"     哈希值: {hash_val}")
                                if created_at:
                                    print(f"     计算时间: {created_at}")
                    
                    if len(files) >= limit:
                        print(f"\n... 还有更多文件（仅显示前{limit}个，使用 --limit {limit + 100} 显示更多）")
                else:
                    # 显示路径下的重复文件组
                    groups = self.analyzer.get_groups_by_path(pattern)
                    
                    print(f"\n路径 {pattern} 下的重复文件")
                    print(f"=" * 60)
                    
                    if not groups:
                        print("  没有找到重复文件")
                    else:
                        print(f"  找到 {len(groups)} 个重复文件组")
                        for i, group in enumerate(groups[:limit], 1):
                            print(f"\n{i}. 组ID: {group['group_id']}")
                            print(f"   文件大小: {group['size']:,} 字节")
                            print(f"   文件扩展名: {group['extension']}")
                            print(f"   文件数量: {group['file_count']} 个")
                            print(f"   包含的文件:")
                            for j, filepath in enumerate(group['files'][:5], 1):
                                print(f"     {j}. {filepath}")
                            if len(group['files']) > 5:
                                print(f"     ... 还有 {len(group['files']) - 5} 个文件")
                        
                        if len(groups) > limit:
                            print(f"\n... 还有 {len(groups) - limit} 个组未显示（使用 --limit {limit + 20} 显示更多）")
                    
                    print(f"=" * 60)
            
        elif subcommand == 'hash':
            # 显示指定哈希值的所有文件
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
            
        elif subcommand == 'stats':
            # 显示统计分析
            by_extension = False
            by_size_range = False
            by_date = False
            
            for arg in args[1:]:
                if arg == '--by-extension':
                    by_extension = True
                elif arg == '--by-size-range':
                    by_size_range = True
                elif arg == '--by-date':
                    by_date = True
            
            if by_extension:
                stats = self.analyzer.get_stats_by_extension()
                print(f"\n按扩展名统计")
                print(f"=" * 60)
                for ext, count in stats.items():
                    print(f"  {ext or '(无扩展名)'}: {count} 个组")
                print(f"=" * 60)
            elif by_size_range:
                stats = self.analyzer.get_stats_by_size_range()
                print(f"\n按大小范围统计")
                print(f"=" * 60)
                for range_name, count in stats.items():
                    print(f"  {range_name}: {count} 个组")
                print(f"=" * 60)
            elif by_date:
                stats = self.analyzer.get_stats_by_date()
                print(f"\n按日期统计")
                print(f"=" * 60)
                for date, count in stats.items():
                    print(f"  {date}: {count} 个组")
                print(f"=" * 60)
            else:
                # 默认显示数据汇总报告
                stats = self.analyzer.get_statistics(hash_only=False)
                
                print(f"\n数据汇总报告")
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
                
        else:
            print(f"错误: 未知的show子命令: {subcommand}")
            self.show_command_help('show')
    
    def _parse_size(self, size_str):
        """解析大小字符串（支持K/M/G单位）"""
        size_str = size_str.upper()
        if size_str.endswith('K'):
            return int(size_str[:-1]) * 1024
        elif size_str.endswith('M'):
            return int(size_str[:-1]) * 1024 * 1024
        elif size_str.endswith('G'):
            return int(size_str[:-1]) * 1024 * 1024 * 1024
        else:
            return int(size_str)

    def _show_group_detail(self, group_id):
        """显示指定组的详细信息（优化格式）"""
        group = self.analyzer.get_group_details(group_id)

        if not group:
            print(f"错误: 找不到组ID: {group_id}")
            return

        # 格式化文件大小
        size = group['size']
        if size >= 1024 * 1024 * 1024:
            size_str = f"{size / 1024 / 1024 / 1024:.2f} GB"
        elif size >= 1024 * 1024:
            size_str = f"{size / 1024 / 1024:.2f} MB"
        elif size >= 1024:
            size_str = f"{size / 1024:.2f} KB"
        else:
            size_str = f"{size} B"

        # 格式化可释放空间
        savable = group['savable_space']
        if savable >= 1024 * 1024 * 1024:
            savable_str = f"{savable / 1024 / 1024 / 1024:.2f} GB"
        elif savable >= 1024 * 1024:
            savable_str = f"{savable / 1024 / 1024:.2f} MB"
        elif savable >= 1024:
            savable_str = f"{savable / 1024:.2f} KB"
        else:
            savable_str = f"{savable} B"

        # 哈希值显示（截短）
        hash_str = group['hash'] if group['hash'] else "未确认"
        if hash_str != "未确认" and len(hash_str) > 16:
            hash_str = hash_str[:16] + "..."

        print(f"\n组 #{group_id} | 大小: {size_str} | 扩展名: {group['extension'] or '无'} | 文件数: {group['file_count']} | 可释放: {savable_str} | 哈希: {hash_str}")
        print(f"{'=' * 100}")

        # 列出重复文件的绝对路径
        for i, file_info in enumerate(group['files'], 1):
            print(f"  {i}. {file_info['filepath']}")

        print(f"{'=' * 100}")

    def _rebuild_duplicate_groups(self):
        """重建重复文件组
        
        扫描files表，按照扩展名和大小创建重复文件组
        调用 IndexManager 中的公共方法
        """
        index_manager = IndexManager(self.db_path)
        index_manager.rebuild_duplicate_groups()
    
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
            backup_path = args[1]
            hash_only = '--hash-only' in args
            if hash_only:
                if not backup_path.endswith('.csv'):
                    backup_path += '.csv'
                self.db_manager.backup_file_hash(backup_path)
            else:
                self.db_manager.backup_database(backup_path)
        elif subcommand == 'restore':
            if len(args) < 2:
                print("错误: 请指定备份文件路径")
                return
            backup_path = args[1]
            hash_only = '--hash-only' in args
            if hash_only:
                merge = '--merge' in args
                self.db_manager.restore_file_hash(backup_path, merge=merge)
            else:
                self.db_manager.restore_database(backup_path)
        elif subcommand == 'init':
            force = '--force' in args
            self.db_manager.init_database(force)
        else:
            print(f"错误: 未知的db子命令: {subcommand}")
            self.show_command_help('db')
    
    def execute_clean_command(self, args):
        """执行clean命令"""
        cleaner = FileCleaner(self.db_path)
        
        # 解析参数
        remaining_args = args
        i = 0
        while i < len(remaining_args):
            arg = remaining_args[i]
            
            if arg == '--dryrun':
                cleaner.dryrun = True
            elif arg == '--script':
                cleaner.script_mode = True
                # 检查是否有路径参数（下一个参数不以--开头）
                if i + 1 < len(remaining_args) and not remaining_args[i + 1].startswith('--'):
                    cleaner.script_path = remaining_args[i + 1]
                    i += 1  # 跳过路径参数
            elif arg == '--yes' or arg == '-y':
                cleaner.auto_confirm = True
            elif arg == '--group' and i + 1 < len(remaining_args):
                # 解析组ID
                try:
                    cleaner.group_ids = [int(gid) for gid in remaining_args[i + 1].split(',')]
                except ValueError:
                    print(f"错误: 无效的组ID: {remaining_args[i + 1]}")
                    return
                i += 1  # 跳过参数值
            elif arg == '--min-size' and i + 1 < len(remaining_args):
                # 解析最小大小
                try:
                    size_str = remaining_args[i + 1]
                    if size_str.endswith('K'):
                        cleaner.min_size = int(size_str[:-1]) * 1024
                    elif size_str.endswith('M'):
                        cleaner.min_size = int(size_str[:-1]) * 1024 * 1024
                    elif size_str.endswith('G'):
                        cleaner.min_size = int(size_str[:-1]) * 1024 * 1024 * 1024
                    else:
                        cleaner.min_size = int(size_str)
                except ValueError:
                    print(f"错误: 无效的大小值: {remaining_args[i + 1]}")
                    return
                i += 1  # 跳过参数值
            elif arg == '--max-size' and i + 1 < len(remaining_args):
                # 解析最大大小
                try:
                    size_str = remaining_args[i + 1]
                    if size_str.endswith('K'):
                        cleaner.max_size = int(size_str[:-1]) * 1024
                    elif size_str.endswith('M'):
                        cleaner.max_size = int(size_str[:-1]) * 1024 * 1024
                    elif size_str.endswith('G'):
                        cleaner.max_size = int(size_str[:-1]) * 1024 * 1024 * 1024
                    else:
                        cleaner.max_size = int(size_str)
                except ValueError:
                    print(f"错误: 无效的大小值: {remaining_args[i + 1]}")
                    return
                i += 1  # 跳过参数值
            elif arg.startswith('--keep-'):
                # 解析排序策略
                strategy = arg[7:]  # 去掉 --keep-
                valid_strategies = ['newest', 'oldest', 'longest_name', 'shortest_name', 
                                   'longest_path', 'shortest_path', 'first_alpha_name', 
                                   'last_alpha_name', 'first_alpha_path', 'last_alpha_path', 
                                   'deepest', 'shallowest']
                if strategy in valid_strategies:
                    cleaner.sort_strategy = strategy
                else:
                    print(f"错误: 无效的排序策略: {strategy}")
                    return
            else:
                print(f"错误: 未知的参数: {arg}")
                return
            
            i += 1
        
        # 执行清理操作
        cleaner.clean()
    
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
                elif main_command == 'show':
                    self.execute_show_command(args)
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
    
    # 检查是否指定了数据库路径（--db 参数）
    args = sys.argv[1:]
    if '--db' in args:
        db_index = args.index('--db')
        if db_index + 1 < len(args):
            db_path = args[db_index + 1]
            args = args[:db_index] + args[db_index + 2:]
    
    interface = CommandInterface(db_path)
    
    # 如果有命令行参数，直接执行命令
    if args:
        command = ' '.join(args)
        parts = command.split()
        if parts:
            main_command = parts[0].lower()
            cmd_args = parts[1:]
            
            if main_command == 'help' or main_command == 'h' or main_command == '?':
                if cmd_args:
                    interface.show_command_help(cmd_args[0])
                else:
                    interface.show_help()
            elif main_command == 'version':
                print("重复文件分析工具 v2.0")
                print("重构版本 - 支持新的指令系统和模块化架构")
            elif main_command == 'index':
                interface.execute_index_command(cmd_args)
            elif main_command == 'show':
                interface.execute_show_command(cmd_args)
            elif main_command == 'export':
                interface.execute_export_command(cmd_args)
            elif main_command == 'config':
                interface.execute_config_command(cmd_args)
            elif main_command == 'db':
                interface.execute_db_command(cmd_args)
            elif main_command == 'clean':
                interface.execute_clean_command(cmd_args)
            else:
                print(f"未知命令: {main_command}，输入 help 查看帮助")
    else:
        interface.run()

if __name__ == '__main__':
    main()