#!/usr/bin/env python3
"""
哈希计算指令 - 计算和验证文件哈希值
"""
import typer
import os
import sqlite3
import time
import hashlib
import mmap
from typing import Optional
from datetime import datetime
from commands.config import ConfigManager
from commands.db import get_db_path

# 方案一：尝试导入 xxHash，如果失败则回退到 MD5
try:
    import xxhash
    HASH_ALGORITHM = 'xxhash'
    def get_hasher():
        return xxhash.xxh64()
    def get_hash_hexdigest(hasher):
        return hasher.hexdigest()
except ImportError:
    HASH_ALGORITHM = 'md5'
    def get_hasher():
        return hashlib.md5()
    def get_hash_hexdigest(hasher):
        return hasher.hexdigest()

app = typer.Typer(help="哈希计算和验证指令")

class HashCalculator:
    def __init__(self, db_path=None, quiet=False):
        self.db_path = db_path or get_db_path()
        self.quiet = quiet
        self.total_processed = 0
        self.total_calculated = 0
        self.total_skipped = 0
        self.total_size_processed = 0
        self.total_size_calculated = 0
        self.start_time = 0
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path, timeout=30.0, isolation_level='DEFERRED')
    
    def format_size(self, size):
        """格式化文件大小显示"""
        if size >= 1024 * 1024 * 1024:
            return f"{size / 1024 / 1024 / 1024:.2f} GB"
        elif size >= 1024 * 1024:
            return f"{size / 1024 / 1024:.2f} MB"
        elif size >= 1024:
            return f"{size / 1024:.2f} KB"
        else:
            return f"{size} B"
    
    def calculate_file_hash(self, file_path):
        """计算单个文件的哈希值（使用内存映射优化大文件）"""
        try:
            hasher = get_hasher()
            with open(file_path, 'rb') as f:
                # 对于大文件使用内存映射
                if os.path.getsize(file_path) > 10 * 1024 * 1024:  # 大于10MB
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                        hasher.update(mm)
                else:
                    # 小文件直接读取
                    while chunk := f.read(8192):
                        hasher.update(chunk)
            return get_hash_hexdigest(hasher)
        except Exception as e:
            print(f"计算哈希失败 {file_path}: {e}")
            return None
    
    def calculate_hash(self, mode='default', group_ids=None, filters=None):
        """
        计算哈希值
        
        Args:
            mode: 计算模式
                - 'default': 默认模式，计算所有未计算哈希的组
                - 'new': 仅新增模式，只计算从未计算过哈希值的文件
                - 'force': 强制更新模式，重新计算所有哈希值
                - 'verify': 验证模式，验证现有哈希值
            group_ids: 指定要处理的组ID列表
            filters: 过滤条件字典，支持 'extension', 'size', 'unconfirmed'
        """
        self.start_time = time.time()
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = []
            params = []
            
            if group_ids:
                placeholders = ','.join(['?'] * len(group_ids))
                conditions.append(f"dg.ID IN ({placeholders})")
                params.extend(group_ids)
            
            if filters:
                if 'extension' in filters:
                    conditions.append("dg.Extension = ?")
                    params.append(filters['extension'])
                if 'size' in filters:
                    size_filter = filters['size']
                    if size_filter.startswith('>'):
                        conditions.append("dg.Size > ?")
                        params.append(int(size_filter[1:]))
                    elif size_filter.startswith('<'):
                        conditions.append("dg.Size < ?")
                        params.append(int(size_filter[1:]))
                    elif size_filter.startswith('='):
                        conditions.append("dg.Size = ?")
                        params.append(int(size_filter[1:]))
                if 'unconfirmed' in filters and filters['unconfirmed']:
                    conditions.append("(dg.Hash IS NULL OR dg.Hash = '')")
            
            # 根据模式调整查询
            if mode == 'new':
                # 仅新增模式：只处理从未计算过哈希值的文件
                pass  # 在process_group中处理
            elif mode == 'verify':
                # 验证模式：只处理已有哈希值的文件
                conditions.append("dg.Hash IS NOT NULL AND dg.Hash != ''")
            
            # 构建WHERE子句
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # 获取要处理的组
            query = f'''
                SELECT DISTINCT dg.ID, dg.Extension, dg.Size, COUNT(df.Filepath) as file_count
                FROM duplicate_groups dg
                INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
                WHERE {where_clause}
                GROUP BY dg.ID
                ORDER BY dg.Size DESC
            '''
            
            cursor.execute(query, params)
            groups = cursor.fetchall()
            
            total_groups = len(groups)
            total_files = sum(g[3] for g in groups)
            total_size = sum(g[2] * g[3] for g in groups)
            
            if not self.quiet:
                print("=" * 80)
                print("哈希计算")
                print("=" * 80)
                print(f"计算模式: {mode}")
                print(f"哈希算法: {HASH_ALGORITHM}")
                if group_ids:
                    print(f"指定组ID: {', '.join(map(str, group_ids))}")
                if filters:
                    print(f"过滤条件: {filters}")
                print(f"重复文件组数量: {total_groups}")
                print(f"待处理文件数量: {total_files} 个")
                print(f"待处理文件总大小: {self.format_size(total_size)}")
                print("=" * 80)
            
            if total_groups == 0:
                if not self.quiet:
                    print("\n没有需要处理的文件")
                return
            
            # 按组处理
            for group_idx, (group_id, extension, size, file_count) in enumerate(groups, 1):
                if not self.quiet:
                    print(f"\n{'=' * 80}")
                    print(f"处理第 {group_idx}/{total_groups} 组 (Group_ID: {group_id})")
                    print(f"扩展名: {extension}, 文件大小: {self.format_size(size)}, 文件数量: {file_count}")
                    print(f"{'=' * 80}")
                
                # 处理这个组
                self.process_group(group_id, mode, total_files, total_size)
            
            elapsed = time.time() - self.start_time
            
            # 显示完成信息
            if not self.quiet:
                print("\n" + "=" * 80)
                print("哈希计算完成！")
                print("=" * 80)
                print(f"总处理文件数: {self.total_processed} 个")
                print(f"总处理大小: {self.format_size(self.total_size_processed)}")
                print(f"计算哈希文件数: {self.total_calculated} 个")
                print(f"计算哈希大小: {self.format_size(self.total_size_calculated)}")
                print(f"跳过文件数: {self.total_skipped} 个")
                print(f"耗时: {elapsed:.2f} 秒")
                
                if elapsed > 0:
                    speed_files = self.total_processed / elapsed
                    speed_size = self.total_size_processed / elapsed
                    print(f"平均速度: {speed_files:.1f} 文件/秒 ({self.format_size(speed_size)}/秒)")
                print("=" * 80)
        finally:
            if conn:
                conn.close()
    
    def process_group(self, group_id, mode, total_files, total_size):
        """处理一个重复文件组"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 获取该组的所有文件
            if mode == 'new':
                # 仅新增模式：只获取从未计算过哈希值的文件
                cursor.execute('''
                    SELECT df.Filepath, f.Size, f.Modified
                    FROM duplicate_files df
                    INNER JOIN files f ON df.Filepath = f.Filename
                    WHERE df.Group_ID = ? AND df.Filepath NOT IN (SELECT Filepath FROM file_hash)
                ''', (group_id,))
            else:
                # 默认模式和强制更新模式：获取所有文件
                cursor.execute('''
                    SELECT df.Filepath, f.Size, f.Modified
                    FROM duplicate_files df
                    INNER JOIN files f ON df.Filepath = f.Filename
                    WHERE df.Group_ID = ?
                ''', (group_id,))
            
            files = cursor.fetchall()
            
            if not files:
                if not self.quiet:
                    print("该组没有需要处理的文件")
                return
            
            # 获取已计算的哈希值
            file_paths = [file[0] for file in files]
            placeholders = ','.join(['?'] * len(file_paths))
            cursor.execute(f'SELECT Filepath, Size, Modified FROM file_hash WHERE Filepath IN ({placeholders})', file_paths)
            existing_hashes = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
            
            # 计算哈希值
            results = []
            for file_path, file_size, file_modified in files:
                # 显示即将处理的文件（不换行）
                if not self.quiet:
                    print(f"正在处理: {self.format_size(file_size):>10s}  {file_path} ... ", end='', flush=True)
                
                # 检查是否需要跳过计算
                should_skip = False
                
                if mode == 'new':
                    # 仅新增模式：如果file_hash表里有该文件的记录，就跳过
                    if file_path in existing_hashes:
                        should_skip = True
                        if not self.quiet:
                            print("跳过（已有哈希记录）")
                        self.total_skipped += 1
                elif mode == 'force':
                    # 强制更新模式：不跳过，重新计算
                    pass
                else:
                    # 默认模式：如果文件没有变化，跳过计算
                    if file_path in existing_hashes:
                        existing_size, existing_modified = existing_hashes[file_path]
                        # 确保类型一致
                        if isinstance(existing_modified, str):
                            try:
                                dt = datetime.fromisoformat(existing_modified)
                                existing_modified = dt.timestamp()
                            except:
                                existing_modified = float(existing_modified)
                        
                        if existing_size == file_size and abs(existing_modified - file_modified) < 0.001:
                            should_skip = True
                            if not self.quiet:
                                print("跳过（文件未变更）")
                            self.total_skipped += 1
                
                if should_skip:
                    self.total_processed += 1
                    self.total_size_processed += file_size
                    continue
                
                # 计算哈希值
                hash_value = self.calculate_file_hash(file_path)
                
                if hash_value:
                    results.append((file_path, file_size, file_modified, hash_value))
                    if not self.quiet:
                        print(f"完成 (Hash: {hash_value[:16]}...)")
                    self.total_calculated += 1
                    self.total_size_calculated += file_size
                else:
                    if not self.quiet:
                        print("失败")
                
                self.total_processed += 1
                self.total_size_processed += file_size
            
            # 批量插入或更新哈希值
            if results:
                for file_path, file_size, file_modified, hash_value in results:
                    # 检查是否已存在记录
                    cursor.execute('SELECT COUNT(*) FROM file_hash WHERE Filepath = ?', (file_path,))
                    if cursor.fetchone()[0] > 0:
                        # 更新现有记录
                        cursor.execute('''
                            UPDATE file_hash 
                            SET Size = ?, Modified = ?, Hash = ?, created_at = datetime('now')
                            WHERE Filepath = ?
                        ''', (file_size, file_modified, hash_value, file_path))
                    else:
                        # 插入新记录
                        cursor.execute('''
                            INSERT INTO file_hash (Filepath, Size, Modified, Hash, created_at)
                            VALUES (?, ?, ?, ?, datetime('now'))
                        ''', (file_path, file_size, file_modified, hash_value))
                
                conn.commit()
                
                # 更新duplicate_groups表的Hash字段
                self._update_group_hash(cursor, conn, group_id)
        finally:
            if conn:
                conn.close()
    
    def _update_group_hash(self, cursor, conn, group_id):
        """更新组的哈希值（取该组所有文件哈希值的最大值）"""
        cursor.execute('''
            SELECT fh.Hash
            FROM duplicate_files df
            INNER JOIN file_hash fh ON df.Filepath = fh.Filepath
            WHERE df.Group_ID = ? AND fh.Hash IS NOT NULL AND fh.Hash != ''
        ''', (group_id,))
        
        hashes = [row[0] for row in cursor.fetchall()]
        
        if hashes:
            # 使用第一个非空哈希值作为组的哈希值
            group_hash = hashes[0]
            cursor.execute('''
                UPDATE duplicate_groups SET Hash = ? WHERE ID = ?
            ''', (group_hash, group_id))
            conn.commit()


@app.command()
def calc(
    group_id: Optional[str] = typer.Option(None, "--group", "-g", help="指定组ID，多个用逗号分隔"),
    new: bool = typer.Option(False, "--new", "-n", help="仅计算从未计算过哈希值的文件"),
    force: bool = typer.Option(False, "--force", "-f", help="强制重新计算所有哈希值"),
    extension: Optional[str] = typer.Option(None, "--extension", "-e", help="按扩展名过滤"),
    size: Optional[str] = typer.Option(None, "--size", "-s", help="按大小过滤 (例如: >1G, <100M, =1K)"),
    path: Optional[str] = typer.Option(None, "--path", "-p", help="按路径过滤")
):
    """计算文件哈希值"""
    mode = 'default'
    group_ids = None
    filters = {}
    
    if new:
        mode = 'new'
    elif force:
        mode = 'force'
    
    if extension:
        filters['extension'] = extension
    if size:
        filters['size'] = size
    
    if group_id:
        try:
            group_ids = [int(gid) for gid in group_id.split(',')]
        except ValueError:
            typer.echo(f"错误: 无效的组ID: {group_id}")
            return
    
    calculator = HashCalculator()
    calculator.calculate_hash(mode, group_ids, filters)


@app.command()
def verify(
    group_id: Optional[str] = typer.Option(None, "--group", "-g", help="指定组ID验证")
):
    """验证文件哈希值"""
    group_ids = None
    
    if group_id:
        try:
            group_ids = [int(gid) for gid in group_id.split(',')]
        except ValueError:
            typer.echo(f"错误: 无效的组ID: {group_id}")
            return
    
    calculator = HashCalculator()
    calculator.calculate_hash('verify', group_ids, {})


@app.command()
def status():
    """显示哈希计算状态"""
    conn = sqlite3.connect(get_db_path(), timeout=30.0)
    cursor = conn.cursor()
    
    # 获取统计信息
    cursor.execute('SELECT COUNT(*) FROM duplicate_groups')
    total_groups = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM duplicate_groups WHERE Hash IS NOT NULL AND Hash != ''")
    hashed_groups = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM duplicate_files')
    total_files = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM file_hash')
    hashed_files = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) FROM duplicate_files df
        WHERE df.Filepath NOT IN (SELECT Filepath FROM file_hash)
    ''')
    unhashed_files = cursor.fetchone()[0]
    
    conn.close()
    
    typer.echo("\n哈希计算状态")
    typer.echo("=" * 60)
    typer.echo(f"重复文件组总数: {total_groups}")
    typer.echo(f"  - 已计算哈希: {hashed_groups}")
    typer.echo(f"  - 未计算哈希: {total_groups - hashed_groups}")
    typer.echo(f"\n重复文件总数: {total_files}")
    typer.echo(f"  - 已计算哈希: {hashed_files}")
    typer.echo(f"  - 未计算哈希: {unhashed_files}")
    
    if total_groups > 0:
        progress = (hashed_groups / total_groups) * 100
        typer.echo(f"\n总体进度: {progress:.1f}%")
    
    typer.echo("=" * 60)


@app.command()
def clear(
    group_id: Optional[str] = typer.Option(None, "--group", "-g", help="清除指定组的哈希值"),
    all: bool = typer.Option(False, "--all", "-a", help="清除所有哈希值")
):
    """清除哈希值"""
    if not group_id and not all:
        typer.echo("错误: 请指定 --group 或 --all 选项")
        return
    
    conn = sqlite3.connect(get_db_path(), timeout=30.0)
    cursor = conn.cursor()
    
    if all:
        # 清除所有哈希值
        cursor.execute('SELECT COUNT(*) FROM file_hash')
        count = cursor.fetchone()[0]
        
        cursor.execute('DELETE FROM file_hash')
        cursor.execute("UPDATE duplicate_groups SET Hash = NULL")
        conn.commit()
        
        typer.echo(f"已清除所有哈希值（共 {count} 条记录）")
    elif group_id:
        # 清除指定组的哈希值
        try:
            gid = int(group_id)
            
            # 获取该组的文件
            cursor.execute('SELECT Filepath FROM duplicate_files WHERE Group_ID = ?', (gid,))
            files = [row[0] for row in cursor.fetchall()]
            
            if files:
                placeholders = ','.join(['?'] * len(files))
                cursor.execute(f'DELETE FROM file_hash WHERE Filepath IN ({placeholders})', files)
                cursor.execute("UPDATE duplicate_groups SET Hash = NULL WHERE ID = ?", (gid,))
                conn.commit()
                
                typer.echo(f"已清除组 {gid} 的哈希值（共 {len(files)} 个文件）")
            else:
                typer.echo(f"组 {gid} 没有文件")
        except ValueError:
            typer.echo(f"错误: 无效的组ID: {group_id}")
    
    conn.close()


@app.command()
def backup(
    backup_path: str = typer.Argument(..., help="备份文件路径"),
    format: str = typer.Option("csv", "--format", "-f", help="备份格式: csv 或 json")
):
    """备份哈希值到文件"""
    import csv
    import json
    
    backup_path = os.path.abspath(backup_path)
    
    # 自动添加扩展名
    if format == "csv" and not backup_path.endswith('.csv'):
        backup_path += '.csv'
    elif format == "json" and not backup_path.endswith('.json'):
        backup_path += '.json'
    
    conn = sqlite3.connect(get_db_path(), timeout=30.0)
    cursor = conn.cursor()
    
    # 获取所有哈希值
    cursor.execute('SELECT Filepath, Size, Modified, Hash, created_at FROM file_hash WHERE Hash IS NOT NULL AND Hash != ""')
    rows = cursor.fetchall()
    conn.close()
    
    if format == "csv":
        # CSV格式备份
        with open(backup_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Filepath', 'Size', 'Modified', 'Hash', 'created_at'])
            writer.writerows(rows)
    elif format == "json":
        # JSON格式备份
        data = []
        for row in rows:
            data.append({
                'filepath': row[0],
                'size': row[1],
                'modified': row[2],
                'hash': row[3],
                'created_at': row[4]
            })
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    typer.echo(f"哈希值已备份到: {backup_path}")
    typer.echo(f"  共备份 {len(rows)} 条记录")


@app.command()
def restore(
    backup_path: str = typer.Argument(..., help="备份文件路径"),
    format: str = typer.Option("auto", "--format", "-f", help="备份格式: auto, csv 或 json"),
    merge: bool = typer.Option(False, "--merge", "-m", help="合并模式（保留现有数据）")
):
    """从文件还原哈希值"""
    import csv
    import json
    
    backup_path = os.path.abspath(backup_path)
    
    if not os.path.exists(backup_path):
        typer.echo(f"错误: 备份文件不存在: {backup_path}")
        return
    
    # 自动检测格式
    if format == "auto":
        if backup_path.endswith('.json'):
            format = "json"
        else:
            format = "csv"
    
    conn = sqlite3.connect(get_db_path(), timeout=30.0)
    cursor = conn.cursor()
    
    # 清空现有数据（非合并模式）
    if not merge:
        cursor.execute('DELETE FROM file_hash')
        typer.echo("已清空现有哈希值数据")
    
    imported_count = 0
    skipped_count = 0
    
    if format == "csv":
        # CSV格式还原
        with open(backup_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # 跳过表头
            
            for row in reader:
                if len(row) >= 4:
                    filepath, size, modified, hash_val = row[0], row[1], row[2], row[3]
                    created_at = row[4] if len(row) > 4 else None
                    
                    # 检查是否已存在
                    cursor.execute('SELECT COUNT(*) FROM file_hash WHERE Filepath = ?', (filepath,))
                    if cursor.fetchone()[0] > 0:
                        if merge:
                            cursor.execute('''
                                UPDATE file_hash SET Size = ?, Modified = ?, Hash = ?, created_at = ?
                                WHERE Filepath = ?
                            ''', (size, modified, hash_val, created_at, filepath))
                            imported_count += 1
                        else:
                            skipped_count += 1
                    else:
                        cursor.execute('''
                            INSERT INTO file_hash (Filepath, Size, Modified, Hash, created_at)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (filepath, size, modified, hash_val, created_at))
                        imported_count += 1
    
    elif format == "json":
        # JSON格式还原
        with open(backup_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for item in data:
            filepath = item.get('filepath') or item.get('Filepath')
            size = item.get('size') or item.get('Size')
            modified = item.get('modified') or item.get('Modified')
            hash_val = item.get('hash') or item.get('Hash')
            created_at = item.get('created_at') or item.get('created_at')
            
            if filepath and hash_val:
                cursor.execute('SELECT COUNT(*) FROM file_hash WHERE Filepath = ?', (filepath,))
                if cursor.fetchone()[0] > 0:
                    if merge:
                        cursor.execute('''
                            UPDATE file_hash SET Size = ?, Modified = ?, Hash = ?, created_at = ?
                            WHERE Filepath = ?
                        ''', (size, modified, hash_val, created_at, filepath))
                        imported_count += 1
                    else:
                        skipped_count += 1
                else:
                    cursor.execute('''
                        INSERT INTO file_hash (Filepath, Size, Modified, Hash, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (filepath, size, modified, hash_val, created_at))
                    imported_count += 1
    
    conn.commit()
    
    # 统计结果
    cursor.execute('SELECT COUNT(*) FROM file_hash WHERE Hash IS NOT NULL AND Hash != ""')
    total_count = cursor.fetchone()[0]
    
    conn.close()
    
    typer.echo(f"哈希值已从 {backup_path} 还原")
    typer.echo(f"  导入记录: {imported_count}")
    if skipped_count > 0:
        typer.echo(f"  跳过记录: {skipped_count}")
    typer.echo(f"  当前总记录数: {total_count}")
