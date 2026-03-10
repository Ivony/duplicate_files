import sqlite3
import csv
import json
from datetime import datetime

class ExportManager:
    def __init__(self, db_path='file_index.db'):
        self.db_path = db_path
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path, timeout=60.0, isolation_level='IMMEDIATE')
    
    def export_csv(self, output_path):
        """导出为CSV格式"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        print(f"开始导出为CSV格式: {output_path}")
        
        # 获取所有重复文件组
        cursor.execute('''
        SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count
        FROM duplicate_groups dg
        INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
        GROUP BY dg.ID
        ORDER BY (COUNT(*) - 1) * dg.Size DESC
        ''')
        
        groups = cursor.fetchall()
        
        # 准备CSV数据
        csv_data = []
        for group_id, size, extension, file_count in groups:
            # 获取该组的文件列表
            cursor.execute('''
            SELECT f.Filename, f.Size, f.Modified, fh.Hash
            FROM duplicate_files df
            INNER JOIN files f ON df.Filepath = f.Filename
            LEFT JOIN file_hash fh ON df.Filepath = fh.Filepath
            WHERE df.Group_ID = ?
            ORDER BY f.Modified DESC
            ''', (group_id,))
            
            files = cursor.fetchall()
            
            for i, (filename, file_size, modified, hash_val) in enumerate(files, 1):
                csv_data.append({
                    'group_id': group_id,
                    'file_index': i,
                    'filename': filename,
                    'size': file_size,
                    'extension': extension,
                    'modified': modified,
                    'hash': hash_val or '',
                    'group_size': size,
                    'group_file_count': file_count
                })
        
        conn.close()
        
        # 写入CSV文件
        try:
            with open(output_path, 'w', encoding='utf-8', newline='') as csvfile:
                fieldnames = ['group_id', 'file_index', 'filename', 'size', 'extension', 'modified', 'hash', 'group_size', 'group_file_count']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_data)
            
            print(f"CSV导出完成！")
            print(f"导出了 {len(csv_data)} 条记录到 {output_path}")
        except Exception as e:
            print(f"CSV导出失败: {e}")
    
    def export_json(self, output_path):
        """导出为JSON格式"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        print(f"开始导出为JSON格式: {output_path}")
        
        # 获取所有重复文件组
        cursor.execute('''
        SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count
        FROM duplicate_groups dg
        INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
        GROUP BY dg.ID
        ORDER BY (COUNT(*) - 1) * dg.Size DESC
        ''')
        
        groups = cursor.fetchall()
        
        # 准备JSON数据
        json_data = {
            'export_time': datetime.now().isoformat(),
            'total_groups': len(groups),
            'groups': []
        }
        
        for group_id, size, extension, file_count in groups:
            # 获取该组的文件列表
            cursor.execute('''
            SELECT f.Filename, f.Size, f.Modified, fh.Hash
            FROM duplicate_files df
            INNER JOIN files f ON df.Filepath = f.Filename
            LEFT JOIN file_hash fh ON df.Filepath = fh.Filepath
            WHERE df.Group_ID = ?
            ORDER BY f.Modified DESC
            ''', (group_id,))
            
            files = cursor.fetchall()
            
            group_data = {
                'group_id': group_id,
                'size': size,
                'extension': extension,
                'file_count': file_count,
                'savable_space': (file_count - 1) * size,
                'files': []
            }
            
            for filename, file_size, modified, hash_val in files:
                group_data['files'].append({
                    'filename': filename,
                    'size': file_size,
                    'modified': modified,
                    'hash': hash_val or ''
                })
            
            json_data['groups'].append(group_data)
        
        conn.close()
        
        # 写入JSON文件
        try:
            with open(output_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(json_data, jsonfile, ensure_ascii=False, indent=2)
            
            print(f"JSON导出完成！")
            print(f"导出了 {len(json_data['groups'])} 个组到 {output_path}")
        except Exception as e:
            print(f"JSON导出失败: {e}")
    
    def generate_report(self, output_path):
        """生成详细的重复文件报告"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        print(f"开始生成详细报告: {output_path}")
        
        # 获取统计信息
        cursor.execute('SELECT COUNT(*) FROM files')
        total_files = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM duplicate_groups')
        duplicate_groups = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM duplicate_files')
        duplicate_files = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(Size) FROM files')
        total_size = cursor.fetchone()[0] or 0
        
        # 获取最大的重复文件组
        cursor.execute('''
        SELECT dg.ID, dg.Size, dg.Extension, COUNT(*) as file_count
        FROM duplicate_groups dg
        INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
        GROUP BY dg.ID
        ORDER BY (COUNT(*) - 1) * dg.Size DESC
        LIMIT 10
        ''')
        
        top_groups = cursor.fetchall()
        
        conn.close()
        
        # 生成报告内容
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("重复文件分析报告")
        report_lines.append("=" * 80)
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        report_lines.append("总体统计:")
        report_lines.append("-" * 40)
        report_lines.append(f"总文件数: {total_files:,}")
        report_lines.append(f"重复文件组数: {duplicate_groups:,}")
        report_lines.append(f"重复文件关联数: {duplicate_files:,}")
        report_lines.append(f"总文件大小: {total_size:,} 字节 ({total_size/1024/1024/1024:.2f} GB)")
        report_lines.append("")
        
        if duplicate_files > 0:
            savable_files = duplicate_files - duplicate_groups
            savable_space = 0
            
            # 计算可节省空间
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            SELECT SUM(duplicate_size)
            FROM (
                SELECT (COUNT(*) - 1) * dg.Size as duplicate_size
                FROM duplicate_groups dg
                INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
                GROUP BY dg.ID
            )
            ''')
            result = cursor.fetchone()
            if result and result[0]:
                savable_space = result[0]
            conn.close()
            
            report_lines.append("重复文件分析:")
            report_lines.append("-" * 40)
            report_lines.append(f"可删除文件数: {savable_files:,}")
            report_lines.append(f"可节省空间: {savable_space:,} 字节 ({savable_space/1024/1024/1024:.2f} GB)")
            report_lines.append("")
            
            report_lines.append("最大的10个重复文件组:")
            report_lines.append("-" * 40)
            
            for i, (group_id, size, extension, file_count) in enumerate(top_groups, 1):
                group_size = size * file_count
                savable_space = (file_count - 1) * size
                
                report_lines.append(f"\n{i}. 组ID: {group_id}")
                report_lines.append(f"   文件大小: {size:,} 字节 ({size/1024/1024:.2f} MB)")
                report_lines.append(f"   文件扩展名: {extension}")
                report_lines.append(f"   文件数量: {file_count} 个")
                report_lines.append(f"   总大小: {group_size:,} 字节 ({group_size/1024/1024/1024:.2f} GB)")
                report_lines.append(f"   可释放空间: {savable_space:,} 字节 ({savable_space/1024/1024/1024:.2f} GB)")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        
        # 写入报告文件
        try:
            with open(output_path, 'w', encoding='utf-8') as reportfile:
                reportfile.write('\n'.join(report_lines))
            
            print(f"报告生成完成！")
            print(f"报告已保存到: {output_path}")
        except Exception as e:
            print(f"报告生成失败: {e}")

if __name__ == '__main__':
    import sys
    
    exporter = ExportManager()
    
    if len(sys.argv) < 2:
        print("用法: python export_manager.py <command> <path>")
        print("\n可用命令:")
        print("  csv <path>     - 导出为CSV格式")
        print("  json <path>    - 导出为JSON格式")
        print("  report <path>   - 生成详细的重复文件报告")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if len(sys.argv) < 3:
        print("错误: 请指定输出路径")
        sys.exit(1)
    
    output_path = sys.argv[2]
    
    if command == 'csv':
        exporter.export_csv(output_path)
    elif command == 'json':
        exporter.export_json(output_path)
    elif command == 'report':
        exporter.generate_report(output_path)
    else:
        print(f"未知命令: {command}")
        sys.exit(1)