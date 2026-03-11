import sqlite3
import os
from datetime import datetime
import sys

class FileCleaner:
    def __init__(self, db_path='file_index.db'):
        self.db_path = db_path
        self.dryrun = False
        self.auto_confirm = False
        self.sort_strategy = 'newest'  # 默认策略
        self.group_ids = None
        self.min_size = None
        self.max_size = None
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path, timeout=60.0, isolation_level='IMMEDIATE')
    
    def delete_file(self, filepath):
        """删除文件，支持模拟模式"""
        if self.dryrun:
            print(f"    [模拟] 删除文件: {filepath}")
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
    
    def verify_group(self, group_id):
        """验证文件组的哈希值一致性"""
        from hash_calculator import HashCalculator
        
        print(f"  验证文件组 {group_id} 的哈希值一致性...")
        calculator = HashCalculator(self.db_path)
        calculator.calculate_hash('verify', [group_id])
        
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
                    choice = input("  请选择要保留的文件序号 (默认 1): ").strip()
                    if not choice:
                        break
                    try:
                        keep_index = int(choice) - 1
                        if 0 <= keep_index < len(file_infos):
                            break
                        else:
                            print("  无效的选择，请重新输入")
                    except ValueError:
                        print("  无效的输入，请输入数字")
            
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
        
        print("\n" + "=" * 80)
        print(f"清理完成！")
        print(f"总计:")
        print(f"  已删除文件数: {total_files:,} 个")
        print(f"  已释放空间: {total_size:,} 字节 ({total_size/1024/1024/1024:.2f} GB)")
        
        if failed_files:
            print(f"  删除失败文件数: {len(failed_files)} 个")
        
        if self.dryrun:
            print("\n注意：这是模拟操作，没有实际删除任何文件")
        
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
    
    # 简单测试
    if len(sys.argv) > 1:
        cleaner.dryrun = '--dryrun' in sys.argv
        cleaner.auto_confirm = '--yes' in sys.argv
        
        # 解析排序策略
        strategies = ['newest', 'oldest', 'longest_name', 'shortest_name', 
                     'longest_path', 'shortest_path', 'first_alpha_name', 
                     'last_alpha_name', 'first_alpha_path', 'last_alpha_path', 
                     'deepest', 'shallowest']
        
        for arg in sys.argv:
            for strategy in strategies:
                if arg == f'--keep-{strategy}':
                    cleaner.sort_strategy = strategy
                    break
        
        cleaner.clean()
    else:
        print("用法: python file_cleaner.py [选项] [排序策略]")
        print("\n选项:")
        print("  --dryrun    模拟执行，不实际删除文件")
        print("  --yes       自动确认，不询问")
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
