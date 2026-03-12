import sqlite3
import os
from datetime import datetime
import sys

class FileCleaner:
    def __init__(self, db_path='file_index.db'):
        self.db_path = db_path
        self.dryrun = False
        self.script_mode = False
        self.script_path = None
        self.script_file = None
        self.script_type = None  # 'cmd', 'bash', 'powershell'
        self.auto_confirm = False
        self.sort_strategy = 'newest'  # 默认策略
        self.group_ids = None
        self.min_size = None
        self.max_size = None
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path, timeout=60.0, isolation_level='IMMEDIATE')
    
    def delete_file(self, filepath):
        """删除文件，支持模拟模式和脚本模式"""
        if self.dryrun:
            print(f"    [模拟] 删除文件: {filepath}")
            return True
        
        if self.script_mode:
            # 脚本模式：将删除命令写入脚本文件
            self._write_delete_command(filepath)
            return True
        
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"    已删除: {filepath}")
                return True
            else:
                print(f"    警告: 文件不存在 {filepath}")
                return False
        except Exception as e:
            print(f"    错误: 删除文件失败 {filepath}: {e}")
            return False
    
    def init_script_file(self, script_path=None):
        """初始化脚本文件"""
        # 确定脚本路径
        if script_path:
            self.script_path = script_path
        else:
            # 默认路径
            self.script_path = self._get_default_script_path()
        
        # 检查文件是否存在
        if os.path.exists(self.script_path):
            print(f"\n脚本文件已存在: {self.script_path}")
            choice = input("是否覆盖? (y/n): ").strip().lower()
            if choice != 'y':
                print("取消脚本生成")
                return False
        
        # 确定脚本类型
        self.script_type = self._detect_script_type(self.script_path)
        
        # 创建脚本文件并写入头部
        self.script_file = open(self.script_path, 'w', encoding='utf-8')
        self._write_script_header()
        
        print(f"脚本文件: {self.script_path}")
        print(f"脚本类型: {self.script_type}")
        return True
    
    def _get_default_script_path(self):
        """获取默认脚本路径"""
        # 根据操作系统选择默认脚本类型
        if os.name == 'nt':  # Windows
            return 'clean_duplicate.cmd'
        else:
            return 'clean_duplicate.sh'
    
    def _detect_script_type(self, script_path):
        """根据文件扩展名检测脚本类型"""
        ext = os.path.splitext(script_path)[1].lower()
        if ext in ['.cmd', '.bat']:
            return 'cmd'
        elif ext in ['.sh', '.bash']:
            return 'bash'
        elif ext in ['.ps1']:
            return 'powershell'
        else:
            # 根据操作系统默认
            return 'cmd' if os.name == 'nt' else 'bash'
    
    def _write_script_header(self):
        """写入脚本头部"""
        if self.script_type == 'cmd':
            self.script_file.write('@echo off\n')
            self.script_file.write('REM 自动生成的重复文件清理脚本\n')
            self.script_file.write(f'REM 生成时间: {datetime.now().isoformat()}\n')
            self.script_file.write('REM 请仔细审查后再执行此脚本\n\n')
        elif self.script_type == 'bash':
            self.script_file.write('#!/bin/bash\n')
            self.script_file.write('# 自动生成的重复文件清理脚本\n')
            self.script_file.write(f'# 生成时间: {datetime.now().isoformat()}\n')
            self.script_file.write('# 请仔细审查后再执行此脚本\n\n')
        elif self.script_type == 'powershell':
            self.script_file.write('# 自动生成的重复文件清理脚本\n')
            self.script_file.write(f'# 生成时间: {datetime.now().isoformat()}\n')
            self.script_file.write('# 请仔细审查后再执行此脚本\n\n')
    
    def _write_delete_command(self, filepath):
        """写入删除命令到脚本"""
        # 转义特殊字符
        escaped_path = filepath.replace('"', '\\"')
        
        if self.script_type == 'cmd':
            # CMD: 使用 if exist 检查文件是否存在
            self.script_file.write(f'if exist "{escaped_path}" (\n')
            self.script_file.write(f'    echo 删除: {escaped_path}\n')
            self.script_file.write(f'    del /f "{escaped_path}"\n')
            self.script_file.write(f') else (\n')
            self.script_file.write(f'    echo 文件不存在: {escaped_path}\n')
            self.script_file.write(f')\n\n')
        elif self.script_type == 'bash':
            # Bash: 使用 [ -f ] 检查文件是否存在
            escaped_path = filepath.replace('"', '\\"').replace('$', '\\$')
            self.script_file.write(f'if [ -f "{escaped_path}" ]; then\n')
            self.script_file.write(f'    echo "删除: {escaped_path}"\n')
            self.script_file.write(f'    rm -f "{escaped_path}"\n')
            self.script_file.write(f'else\n')
            self.script_file.write(f'    echo "文件不存在: {escaped_path}"\n')
            self.script_file.write(f'fi\n\n')
        elif self.script_type == 'powershell':
            # PowerShell: 使用 Test-Path 检查文件是否存在
            self.script_file.write(f'if (Test-Path "{escaped_path}") {{\n')
            self.script_file.write(f'    Write-Host "删除: {escaped_path}"\n')
            self.script_file.write(f'    Remove-Item -Force "{escaped_path}"\n')
            self.script_file.write(f'}} else {{\n')
            self.script_file.write(f'    Write-Host "文件不存在: {escaped_path}"\n')
            self.script_file.write(f'}}\n\n')
    
    def close_script_file(self):
        """关闭脚本文件"""
        if self.script_file:
            self.script_file.close()
            self.script_file = None
            print(f"\n脚本已生成: {self.script_path}")
            print(f"请仔细审查脚本内容后再执行")
    
    def verify_group(self, group_id):
        """验证文件组的哈希值一致性"""
        from hash_calculator import HashCalculator
        
        print(f"  正在校验组 {group_id}...")
        calculator = HashCalculator(self.db_path)
        # 调用哈希计算器的验证模式，减少输出
        calculator.calculate_hash('verify', [group_id], quiet=True)
        
        # 检查验证后组是否还有哈希值
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT Hash FROM duplicate_groups WHERE ID = ?', (group_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result and result[0] is not None
    
    def get_sort_key(self, strategy):
        """获取排序键函数"""
        def get_file_info(filepath):
            """获取文件信息"""
            filename = os.path.basename(filepath)
            dir_depth = len(filepath.split(os.sep))
            return {
                'filepath': filepath,
                'filename': filename,
                'dir_depth': dir_depth
            }
        
        sort_functions = {
            'newest': lambda f: (f['modified'], f['filename'], f['filepath']),
            'oldest': lambda f: (f['modified'], f['filename'], f['filepath']),
            'longest_name': lambda f: (len(f['filename']), f['filename'], f['filepath']),
            'shortest_name': lambda f: (len(f['filename']), f['filename'], f['filepath']),
            'longest_path': lambda f: (len(f['filepath']), f['filename'], f['filepath']),
            'shortest_path': lambda f: (len(f['filepath']), f['filename'], f['filepath']),
            'first_alpha_name': lambda f: (f['filename'], f['filepath']),
            'last_alpha_name': lambda f: (f['filename'], f['filepath']),
            'first_alpha_path': lambda f: (f['filepath'], f['filename']),
            'last_alpha_path': lambda f: (f['filepath'], f['filename']),
            'deepest': lambda f: (len(f['filepath'].split(os.sep)), f['filename'], f['filepath']),
            'shallowest': lambda f: (len(f['filepath'].split(os.sep)), f['filename'], f['filepath'])
        }
        
        return sort_functions.get(strategy, sort_functions['newest'])
    
    def get_sort_reverse(self, strategy):
        """获取排序方向"""
        reverse_map = {
            'newest': True,
            'oldest': False,
            'longest_name': True,
            'shortest_name': False,
            'longest_path': True,
            'shortest_path': False,
            'first_alpha_name': False,
            'last_alpha_name': True,
            'first_alpha_path': False,
            'last_alpha_path': True,
            'deepest': True,
            'shallowest': False
        }
        
        return reverse_map.get(strategy, True)
    
    def clean(self):
        """执行清理操作"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        print("开始清理操作...")
        print(f"排序策略: {self.get_strategy_name()}")
        if self.dryrun:
            print("模式: 模拟执行 (不实际删除文件)")
        elif self.script_mode:
            print("模式: 脚本生成 (生成删除脚本)")
            # 初始化脚本文件
            if not self.init_script_file(self.script_path):
                conn.close()
                return
        
        # 构建查询语句
        query = '''
        SELECT dg.ID, dg.Size, dg.Extension, dg.Hash, COUNT(*) as file_count
        FROM duplicate_groups dg
        INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
        WHERE dg.Hash IS NOT NULL
        '''
        
        params = []
        
        if self.group_ids:
            placeholders = ','.join(['?'] * len(self.group_ids))
            query += f" AND dg.ID IN ({placeholders})"
            params.extend(self.group_ids)
        
        if self.min_size:
            query += " AND dg.Size >= ?"
            params.append(self.min_size)
        
        if self.max_size:
            query += " AND dg.Size <= ?"
            params.append(self.max_size)
        
        query += '''
        GROUP BY dg.ID
        HAVING COUNT(*) > 1
        ORDER BY (COUNT(*) - 1) * dg.Size DESC
        '''
        
        cursor.execute(query, params)
        groups = cursor.fetchall()
        
        if not groups:
            print("没有找到符合条件的重复文件组")
            conn.close()
            return
        
        total_files = 0
        total_size = 0
        failed_files = []
        
        print(f"\n找到 {len(groups)} 个符合条件的重复文件组")
        print("=" * 80)
        
        for group_id, size, extension, hash_val, file_count in groups:
            # 验证文件组
            if not self.verify_group(group_id):
                print(f"  跳过文件组 {group_id}: 验证失败，哈希值不一致")
                continue
            
            # 获取该组的文件列表
            cursor.execute('''
            SELECT f.Filename, f.Modified
            FROM duplicate_files df
            INNER JOIN files f ON df.Filepath = f.Filename
            WHERE df.Group_ID = ?
            ''', (group_id,))
            
            files = cursor.fetchall()
            
            # 准备文件信息
            file_infos = []
            for filepath, modified in files:
                # 确保修改时间是数值类型
                if isinstance(modified, str):
                    try:
                        dt = datetime.fromisoformat(modified)
                        modified = dt.timestamp()
                    except:
                        modified = float(modified)
                
                file_infos.append({
                    'filepath': filepath,
                    'filename': os.path.basename(filepath),
                    'modified': modified
                })
            
            # 应用排序策略
            sort_key = self.get_sort_key(self.sort_strategy)
            reverse = self.get_sort_reverse(self.sort_strategy)
            file_infos.sort(key=sort_key, reverse=reverse)
            
            # 显示文件组信息
            print(f"\n文件组 {group_id}:")
            print(f"  哈希值: {hash_val}")
            print(f"  文件大小: {size:,} 字节")
            print(f"  文件扩展名: {extension}")
            print(f"  文件数量: {file_count} 个")
            print(f"  排序策略: {self.get_strategy_name()}")
            print(f"  可释放空间: {(file_count - 1) * size:,} 字节")
            print("  文件列表:")
            
            for i, file_info in enumerate(file_infos, 1):
                print(f"    {i}. {file_info['filepath']}")
                print(f"       修改时间: {datetime.fromtimestamp(file_info['modified'])}")
            
            # 询问用户确认
            keep_index = 0
            if not self.auto_confirm:
                while True:
                    choice = input("  请选择要保留的文件序号 (默认 1, 输入 q 退出): ").strip().lower()
                    if not choice:
                        break
                    if choice == 'q':
                        print("  退出清理模式")
                        conn.close()
                        return
                    try:
                        keep_index = int(choice) - 1
                        if 0 <= keep_index < len(file_infos):
                            break
                        else:
                            print("  无效的选择，请重新输入")
                    except ValueError:
                        print("  无效的输入，请输入数字或 q 退出")
            
            # 确定要保留和删除的文件
            keep_file = file_infos[keep_index]
            delete_files = [f for i, f in enumerate(file_infos) if i != keep_index]
            
            print(f"  保留文件: {keep_file['filepath']}")
            print(f"  删除文件数: {len(delete_files)} 个")
            
            # 执行删除操作
            for file_info in delete_files:
                if self.delete_file(file_info['filepath']):
                    total_files += 1
                    total_size += size
                else:
                    failed_files.append(file_info['filepath'])
        
        conn.close()
        
        # 关闭脚本文件
        if self.script_mode:
            self.close_script_file()
        
        print("\n" + "=" * 80)
        print(f"清理完成！")
        print(f"总计:")
        print(f"  已删除文件数: {total_files:,} 个")
        print(f"  已释放空间: {total_size:,} 字节 ({total_size/1024/1024/1024:.2f} GB)")
        
        if failed_files:
            print(f"  删除失败文件数: {len(failed_files)} 个")
        
        if self.dryrun:
            print("\n注意：这是模拟操作，没有实际删除任何文件")
        elif self.script_mode:
            print(f"\n注意：已生成删除脚本，请审查后再执行: {self.script_path}")
        
        print("=" * 80)
    
    def get_strategy_name(self):
        """获取排序策略的中文名称"""
        strategy_names = {
            'newest': '保留最新文件',
            'oldest': '保留最旧文件',
            'longest_name': '保留文件名最长的文件',
            'shortest_name': '保留文件名最短的文件',
            'longest_path': '保留路径最长的文件',
            'shortest_path': '保留路径最短的文件',
            'first_alpha_name': '按文件名字母顺序保留第一个',
            'last_alpha_name': '按文件名字母顺序保留最后一个',
            'first_alpha_path': '按路径字母顺序保留第一个',
            'last_alpha_path': '按路径字母顺序保留最后一个',
            'deepest': '保留目录最深的文件',
            'shallowest': '保留目录最浅的文件'
        }
        
        return strategy_names.get(self.sort_strategy, '保留最新文件')

if __name__ == '__main__':
    cleaner = FileCleaner()
    
    if len(sys.argv) > 1:
        # 解析所有参数
        i = 1
        while i < len(sys.argv):
            arg = sys.argv[i]
            
            if arg == '--dryrun':
                cleaner.dryrun = True
            elif arg == '--script':
                cleaner.script_mode = True
                # 检查是否有路径参数（下一个参数不以--开头）
                if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('--'):
                    cleaner.script_path = sys.argv[i + 1]
                    i += 1
            elif arg == '--yes' or arg == '-y':
                cleaner.auto_confirm = True
            elif arg == '--group' and i + 1 < len(sys.argv):
                # 解析组ID
                try:
                    cleaner.group_ids = [int(gid) for gid in sys.argv[i + 1].split(',')]
                    i += 1
                except ValueError:
                    print(f"错误: 无效的组ID: {sys.argv[i + 1]}")
                    sys.exit(1)
            elif arg == '--min-size' and i + 1 < len(sys.argv):
                # 解析最小大小
                try:
                    size_str = sys.argv[i + 1]
                    if size_str.endswith('K'):
                        cleaner.min_size = int(size_str[:-1]) * 1024
                    elif size_str.endswith('M'):
                        cleaner.min_size = int(size_str[:-1]) * 1024 * 1024
                    elif size_str.endswith('G'):
                        cleaner.min_size = int(size_str[:-1]) * 1024 * 1024 * 1024
                    else:
                        cleaner.min_size = int(size_str)
                    i += 1
                except ValueError:
                    print(f"错误: 无效的大小值: {sys.argv[i + 1]}")
                    sys.exit(1)
            elif arg == '--max-size' and i + 1 < len(sys.argv):
                # 解析最大大小
                try:
                    size_str = sys.argv[i + 1]
                    if size_str.endswith('K'):
                        cleaner.max_size = int(size_str[:-1]) * 1024
                    elif size_str.endswith('M'):
                        cleaner.max_size = int(size_str[:-1]) * 1024 * 1024
                    elif size_str.endswith('G'):
                        cleaner.max_size = int(size_str[:-1]) * 1024 * 1024 * 1024
                    else:
                        cleaner.max_size = int(size_str)
                    i += 1
                except ValueError:
                    print(f"错误: 无效的大小值: {sys.argv[i + 1]}")
                    sys.exit(1)
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
                    sys.exit(1)
            else:
                print(f"错误: 未知的参数: {arg}")
                sys.exit(1)
            
            i += 1
        
        cleaner.clean()
    else:
        print("用法: python file_cleaner.py [选项] [排序策略]")
        print("\n选项:")
        print("  --dryrun                模拟执行，不实际删除文件")
        print("  --script [path]         生成删除脚本，不实际删除文件")
        print("                          path: 脚本文件路径（可选，根据扩展名自动判断类型）")
        print("                          支持: .cmd/.bat (CMD), .sh/.bash (Bash), .ps1 (PowerShell)")
        print("  --yes, -y               自动确认，不询问")
        print("  --group <id1,id2,...>   只处理指定的组ID（逗号分隔）")
        print("  --min-size <size>       最小文件大小（支持K/M/G后缀）")
        print("  --max-size <size>       最大文件大小（支持K/M/G后缀）")
        print("\n排序策略:")
        print("  --keep-newest           保留最新文件 (默认)")
        print("  --keep-oldest           保留最旧文件")
        print("  --keep-longest-name     保留文件名最长的文件")
        print("  --keep-shortest-name    保留文件名最短的文件")
        print("  --keep-longest-path     保留路径最长的文件")
        print("  --keep-shortest-path    保留路径最短的文件")
        print("  --keep-first-alpha-name 按文件名字母顺序保留第一个")
        print("  --keep-last-alpha-name  按文件名字母顺序保留最后一个")
        print("  --keep-first-alpha-path 按路径字母顺序保留第一个")
        print("  --keep-last-alpha-path  按路径字母顺序保留最后一个")
        print("  --keep-deepest          保留目录最深的文件")
        print("  --keep-shallowest       保留目录最浅的文件")
