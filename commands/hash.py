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
import sys
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from rich.console import Console
from rich.text import Text
from commands.config import ConfigManager
from commands.db import get_db_path

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

console = Console()

CLEAR_LINE = "\033[2K"
MOVE_UP = "\033[1A"

app = typer.Typer(
    name="hash",
    help="[bold blue]🔐 哈希计算[/bold blue]",
    rich_markup_mode=True
)

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
        self.completed_groups: List[Dict] = []
        self.current_group_lines = 0
    
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
                if os.path.getsize(file_path) > 10 * 1024 * 1024:
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                        hasher.update(mm)
                else:
                    while chunk := f.read(8192):
                        hasher.update(chunk)
            return get_hash_hexdigest(hasher)
        except Exception as e:
            print(f"计算哈希失败 {file_path}: {e}")
            return None
    
    def _clear_current_group_output(self):
        """清除当前组的输出"""
        if self.current_group_lines > 0:
            for _ in range(self.current_group_lines):
                sys.stdout.write(MOVE_UP + CLEAR_LINE)
            sys.stdout.flush()
            self.current_group_lines = 0
    
    def _print_completed_groups(self):
        """打印已完成的组列表"""
        for group_info in self.completed_groups:
            status_icon = group_info['status_icon']
            status_text = group_info['status_text']
            status_color = group_info['status_color']
            
            line = f"  {status_icon} 组 {group_info['group_id']} ({group_info['file_count']} 文件, {self.format_size(group_info['size'])}) - [{status_color}]{status_text}[/{status_color}]"
            console.print(line)
    
    def _print_group_result(self, group_id: int, file_count: int, size: int, 
                            calculated: int, skipped: int, result: str, 
                            new_groups: int = 0):
        """打印组的处理结果"""
        if result == 'confirmed':
            status_icon = "✅"
            status_text = f"已确认 (计算 {calculated}, 跳过 {skipped})"
            status_color = "green"
        elif result == 'split':
            status_icon = "🔀"
            status_text = f"已拆分为 {new_groups} 个组 (计算 {calculated}, 跳过 {skipped})"
            status_color = "yellow"
        elif result == 'dissolved':
            status_icon = "💨"
            status_text = f"已解散 (计算 {calculated}, 跳过 {skipped})"
            status_color = "dim"
        else:
            status_icon = "❓"
            status_text = f"未知状态 (计算 {calculated}, 跳过 {skipped})"
            status_color = "red"
        
        self.completed_groups.append({
            'group_id': group_id,
            'file_count': file_count,
            'size': size,
            'calculated': calculated,
            'skipped': skipped,
            'result': result,
            'new_groups': new_groups,
            'status_icon': status_icon,
            'status_text': status_text,
            'status_color': status_color
        })
        
        self._clear_current_group_output()
        self._print_completed_groups()
    
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
        self.completed_groups = []
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
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
            
            if mode == 'verify':
                conditions.append("dg.Hash IS NOT NULL AND dg.Hash != ''")
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
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
                mode_names = {
                    'default': '默认模式',
                    'new': '仅新增模式',
                    'force': '强制更新模式',
                    'verify': '验证模式'
                }
                
                console.print()
                console.print("[bold blue]🔐 哈希计算[/bold blue]")
                console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
                console.print()
                console.print(f"  计算模式      {mode_names.get(mode, mode)}")
                console.print(f"  哈希算法      {HASH_ALGORITHM}")
                if group_ids:
                    console.print(f"  指定组ID      {', '.join(map(str, group_ids))}")
                if filters:
                    console.print(f"  过滤条件      {filters}")
                console.print(f"  开始时间      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                console.print()
                console.print(f"  重复文件组    [bold]{total_groups:,}[/bold] 组")
                console.print(f"  待处理文件    [bold]{total_files:,}[/bold] 个")
                console.print(f"  待处理大小    [bold]{self.format_size(total_size)}[/bold]")
                console.print()
            
            if total_groups == 0:
                if not self.quiet:
                    console.print("  [yellow]没有需要处理的文件[/yellow]")
                    console.print()
                return
            
            for group_idx, (group_id, extension, size, file_count) in enumerate(groups, 1):
                if not self.quiet:
                    console.print(f"  [dim]───────────────────────────────────────────────[/dim]")
                    console.print(f"  [yellow]⏳[/yellow] 第 {group_idx}/{total_groups} 组 (ID: {group_id})  扩展名: {extension}  大小: {self.format_size(size)}  文件数: {file_count}")
                    console.print(f"  [dim]───────────────────────────────────────────────[/dim]")
                    console.print()
                    self.current_group_lines = 0
                
                result = self.process_group(group_id, mode, extension, size, file_count)
                
                if not self.quiet:
                    self._print_group_result(
                        group_id=group_id,
                        file_count=file_count,
                        size=size,
                        calculated=result['calculated'],
                        skipped=result['skipped'],
                        result=result['result'],
                        new_groups=result.get('new_groups', 0)
                    )
            
            elapsed = time.time() - self.start_time
            
            if not self.quiet:
                console.print()
                console.print()
                console.print("[bold green]✅ 哈希计算完成[/bold green]")
                console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
                console.print()
                console.print(f"  总处理文件数      [bold]{self.total_processed:,}[/bold] 个")
                console.print(f"  总处理大小        [bold]{self.format_size(self.total_size_processed)}[/bold]")
                console.print(f"  计算哈希文件数    [bold]{self.total_calculated:,}[/bold] 个")
                console.print(f"  计算哈希大小      [bold]{self.format_size(self.total_size_calculated)}[/bold]")
                console.print(f"  跳过文件数        [bold]{self.total_skipped:,}[/bold] 个")
                console.print(f"  耗时              [bold]{elapsed:.2f}[/bold] 秒")
                
                if elapsed > 0:
                    speed_files = self.total_processed / elapsed
                    speed_size = self.total_size_processed / elapsed
                    console.print(f"  平均速度          [bold]{speed_files:.0f}[/bold] 文件/秒 ([bold]{self.format_size(speed_size)}[/bold]/秒)")
                console.print()
        finally:
            if conn:
                conn.close()
    
    def process_group(self, group_id, mode, extension, size, file_count) -> Dict:
        """处理一个重复文件组，返回处理结果"""
        conn = None
        result = {
            'calculated': 0,
            'skipped': 0,
            'result': 'unknown',
            'new_groups': 0
        }
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if mode == 'new':
                cursor.execute('''
                    SELECT df.Filepath, f.Size, f.Modified
                    FROM duplicate_files df
                    INNER JOIN files f ON df.Filepath = f.Filename
                    WHERE df.Group_ID = ? AND df.Filepath NOT IN (SELECT Filepath FROM file_hash)
                ''', (group_id,))
            else:
                cursor.execute('''
                    SELECT df.Filepath, f.Size, f.Modified
                    FROM duplicate_files df
                    INNER JOIN files f ON df.Filepath = f.Filename
                    WHERE df.Group_ID = ?
                ''', (group_id,))
            
            files = cursor.fetchall()
            
            if not files:
                result['result'] = 'confirmed'
                return result
            
            file_paths = [file[0] for file in files]
            placeholders = ','.join(['?'] * len(file_paths))
            cursor.execute(f'SELECT Filepath, Size, Modified, Hash FROM file_hash WHERE Filepath IN ({placeholders})', file_paths)
            existing_hash_rows = cursor.fetchall()
            existing_hashes = {row[0]: (row[1], row[2], row[3]) for row in existing_hash_rows}
            
            results = []
            file_hash_map: Dict[str, str] = {}
            
            for file_path, file_size, file_modified in files:
                if isinstance(file_modified, str):
                    try:
                        dt = datetime.fromisoformat(file_modified)
                        file_modified = dt.timestamp()
                    except:
                        try:
                            file_modified = float(file_modified)
                        except:
                            file_modified = 0
                
                should_skip = False
                skip_reason = ""
                
                if mode == 'new':
                    if file_path in existing_hashes:
                        should_skip = True
                        skip_reason = "已有哈希"
                        self.total_skipped += 1
                        result['skipped'] += 1
                        if existing_hashes[file_path][2]:
                            file_hash_map[file_path] = existing_hashes[file_path][2]
                elif mode == 'force':
                    pass
                else:
                    if file_path in existing_hashes:
                        existing_size, existing_modified, existing_hash = existing_hashes[file_path]
                        if isinstance(existing_modified, str):
                            try:
                                dt = datetime.fromisoformat(existing_modified)
                                existing_modified = dt.timestamp()
                            except:
                                try:
                                    existing_modified = float(existing_modified)
                                except:
                                    existing_modified = 0
                        
                        if existing_size == file_size and abs(existing_modified - file_modified) < 0.001:
                            should_skip = True
                            skip_reason = "文件未变"
                            self.total_skipped += 1
                            result['skipped'] += 1
                            if existing_hash:
                                file_hash_map[file_path] = existing_hash
                
                if not self.quiet:
                    short_path = file_path
                    if len(short_path) > 50:
                        short_path = "..." + short_path[-47:]
                    
                    if should_skip:
                        line = f"    [dim]{self.format_size(file_size):>10s}  {short_path}[/dim] [yellow]⏭️ {skip_reason}[/yellow]"
                    else:
                        line = f"    {self.format_size(file_size):>10s}  {short_path} [cyan]⏳ 计算中...[/cyan]"
                    
                    console.print(line)
                    self.current_group_lines += 1
                
                if should_skip:
                    self.total_processed += 1
                    self.total_size_processed += file_size
                    continue
                
                hash_value = self.calculate_file_hash(file_path)
                
                if hash_value:
                    results.append((file_path, file_size, file_modified, hash_value))
                    file_hash_map[file_path] = hash_value
                    self.total_calculated += 1
                    self.total_size_calculated += file_size
                    result['calculated'] += 1
                    
                    if not self.quiet:
                        sys.stdout.write(MOVE_UP + CLEAR_LINE)
                        sys.stdout.flush()
                        self.current_group_lines -= 1
                        
                        line = f"    {self.format_size(file_size):>10s}  {short_path} [green]✅ 已计算[/green]"
                        console.print(line)
                        self.current_group_lines += 1
                
                self.total_processed += 1
                self.total_size_processed += file_size
            
            if results:
                for file_path, file_size, file_modified, hash_value in results:
                    cursor.execute('SELECT COUNT(*) FROM file_hash WHERE Filepath = ?', (file_path,))
                    if cursor.fetchone()[0] > 0:
                        cursor.execute('''
                            UPDATE file_hash 
                            SET Size = ?, Modified = ?, Hash = ?, created_at = datetime('now')
                            WHERE Filepath = ?
                        ''', (file_size, file_modified, hash_value, file_path))
                    else:
                        cursor.execute('''
                            INSERT INTO file_hash (Filepath, Size, Modified, Hash, created_at)
                            VALUES (?, ?, ?, ?, datetime('now'))
                        ''', (file_path, file_size, file_modified, hash_value))
                
                conn.commit()
            
            group_result = self._update_group_hash(cursor, conn, group_id, file_hash_map)
            result['result'] = group_result['result']
            result['new_groups'] = group_result.get('new_groups', 0)
            
        finally:
            if conn:
                conn.close()
        
        return result
    
    def _update_group_hash(self, cursor, conn, group_id: int, file_hash_map: Dict[str, str]) -> Dict:
        """更新组的哈希值，处理组的拆分或解散"""
        cursor.execute('''
            SELECT df.Filepath
            FROM duplicate_files df
            INNER JOIN file_hash fh ON df.Filepath = fh.Filepath
            WHERE df.Group_ID = ? AND fh.Hash IS NOT NULL AND fh.Hash != ''
        ''', (group_id,))
        
        files_with_hash = cursor.fetchall()
        
        if not files_with_hash:
            return {'result': 'dissolved'}
        
        hash_groups: Dict[str, List[str]] = {}
        for (filepath,) in files_with_hash:
            if filepath in file_hash_map:
                hash_value = file_hash_map[filepath]
                if hash_value not in hash_groups:
                    hash_groups[hash_value] = []
                hash_groups[hash_value].append(filepath)
        
        if len(hash_groups) == 0:
            return {'result': 'dissolved'}
        
        if len(hash_groups) == 1:
            group_hash = list(hash_groups.keys())[0]
            cursor.execute('''
                UPDATE duplicate_groups SET Hash = ? WHERE ID = ?
            ''', (group_hash, group_id))
            conn.commit()
            return {'result': 'confirmed'}
        
        if len(hash_groups) > 1:
            cursor.execute('SELECT Size, Extension FROM duplicate_groups WHERE ID = ?', (group_id,))
            group_info = cursor.fetchone()
            if not group_info:
                return {'result': 'dissolved'}
            
            group_size, group_extension = group_info
            
            sorted_groups = sorted(hash_groups.items(), key=lambda x: len(x[1]), reverse=True)
            
            main_hash, main_files = sorted_groups[0]
            cursor.execute('''
                UPDATE duplicate_groups SET Hash = ? WHERE ID = ?
            ''', (main_hash, group_id))
            
            new_group_count = 0
            for hash_value, filepaths in sorted_groups[1:]:
                if len(filepaths) >= 2:
                    cursor.execute('''
                        INSERT INTO duplicate_groups (Size, Extension, Hash)
                        VALUES (?, ?, ?)
                    ''', (group_size, group_extension, hash_value))
                    new_group_id = cursor.lastrowid
                    new_group_count += 1
                    
                    for filepath in filepaths:
                        cursor.execute('''
                            UPDATE duplicate_files SET Group_ID = ? WHERE Filepath = ?
                        ''', (new_group_id, filepath))
                else:
                    for filepath in filepaths:
                        cursor.execute('DELETE FROM duplicate_files WHERE Filepath = ?', (filepath,))
            
            conn.commit()
            
            if new_group_count > 0:
                return {'result': 'split', 'new_groups': new_group_count + 1}
            else:
                main_file_count = len(main_files)
                total_files = sum(len(files) for files in hash_groups.values())
                if main_file_count < 2:
                    return {'result': 'dissolved'}
                return {'result': 'confirmed'}
        
        return {'result': 'unknown'}


@app.command()
def calc(
    group_id: Optional[str] = typer.Option(None, "--group", "-g", help="指定组ID，多个用逗号分隔"),
    new: bool = typer.Option(False, "--new", "-n", help="仅计算从未计算过哈希值的文件"),
    force: bool = typer.Option(False, "--force", "-f", help="强制重新计算所有哈希值"),
    extension: Optional[str] = typer.Option(None, "--extension", "-e", help="按扩展名过滤"),
    size: Optional[str] = typer.Option(None, "--size", "-s", help="按大小过滤 (例如: >1G, <100M, =1K)"),
    path: Optional[str] = typer.Option(None, "--path", "-p", help="按路径过滤")
):
    """[bold]计算文件哈希值[/bold]
    
    [dim]计算重复文件组中文件的哈希值[/dim]
    """
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
            console.print(f"[red]错误: 无效的组ID: {group_id}[/red]")
            return
    
    calculator = HashCalculator()
    calculator.calculate_hash(mode, group_ids, filters)


@app.command()
def verify(
    group_id: Optional[str] = typer.Option(None, "--group", "-g", help="指定组ID验证")
):
    """[bold]验证文件哈希值[/bold]
    
    [dim]验证已有哈希值是否正确[/dim]
    """
    group_ids = None
    
    if group_id:
        try:
            group_ids = [int(gid) for gid in group_id.split(',')]
        except ValueError:
            console.print(f"[red]错误: 无效的组ID: {group_id}[/red]")
            return
    
    calculator = HashCalculator()
    calculator.calculate_hash('verify', group_ids, {})


@app.command()
def status():
    """[bold]显示哈希计算状态[/bold]
    
    [dim]显示哈希计算的进度和统计信息[/dim]
    """
    conn = sqlite3.connect(get_db_path(), timeout=30.0)
    cursor = conn.cursor()
    
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
    
    def print_progress_bar(progress, width=30):
        filled = int(progress / 100 * width)
        return f"[green]{'█' * filled}[/green][dim]{'░' * (width - filled)}[/dim]"
    
    console.print()
    console.print("[bold blue]📊 哈希计算状态[/bold blue]")
    console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
    console.print()
    
    console.print("  [bold]📁 重复文件组[/bold]")
    console.print(f"    总数          [bold]{total_groups:,}[/bold]")
    console.print(f"    已计算哈希    [green]{hashed_groups:,}[/green]")
    console.print(f"    未计算哈希    [yellow]{total_groups - hashed_groups:,}[/yellow]")
    
    if total_groups > 0:
        progress = (hashed_groups / total_groups) * 100
        console.print(f"    进度          {print_progress_bar(progress)} [bold]{progress:.1f}%[/bold]")
    
    console.print()
    console.print("  [bold]📄 重复文件[/bold]")
    console.print(f"    总数          [bold]{total_files:,}[/bold]")
    console.print(f"    已计算哈希    [green]{hashed_files:,}[/green]")
    console.print(f"    未计算哈希    [yellow]{unhashed_files:,}[/yellow]")
    
    if total_files > 0:
        progress = (hashed_files / total_files) * 100
        console.print(f"    进度          {print_progress_bar(progress)} [bold]{progress:.1f}%[/bold]")
    
    console.print()


@app.command()
def clear(
    group_id: Optional[str] = typer.Option(None, "--group", "-g", help="清除指定组的哈希值"),
    all: bool = typer.Option(False, "--all", "-a", help="清除所有哈希值")
):
    """[bold]清除哈希值[/bold]
    
    [dim]清除已计算的哈希值[/dim]
    """
    if not group_id and not all:
        console.print()
        console.print("[bold blue]🗑️ 清除哈希值[/bold blue]")
        console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
        console.print()
        console.print("  [red]错误: 请指定 --group 或 --all 选项[/red]")
        console.print()
        return
    
    conn = sqlite3.connect(get_db_path(), timeout=30.0)
    cursor = conn.cursor()
    
    console.print()
    console.print("[bold blue]🗑️ 清除哈希值[/bold blue]")
    console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
    console.print()
    
    if all:
        cursor.execute('SELECT COUNT(*) FROM file_hash')
        count = cursor.fetchone()[0]
        
        cursor.execute('DELETE FROM file_hash')
        cursor.execute("UPDATE duplicate_groups SET Hash = NULL")
        conn.commit()
        
        console.print(f"  [green]✅ 已清除所有哈希值[/green]")
        console.print(f"  共清除 [bold]{count:,}[/bold] 条记录")
    elif group_id:
        try:
            gid = int(group_id)
            
            cursor.execute('SELECT Filepath FROM duplicate_files WHERE Group_ID = ?', (gid,))
            files = [row[0] for row in cursor.fetchall()]
            
            if files:
                placeholders = ','.join(['?'] * len(files))
                cursor.execute(f'DELETE FROM file_hash WHERE Filepath IN ({placeholders})', files)
                cursor.execute("UPDATE duplicate_groups SET Hash = NULL WHERE ID = ?", (gid,))
                conn.commit()
                
                console.print(f"  [green]✅ 已清除组 {gid} 的哈希值[/green]")
                console.print(f"  共清除 [bold]{len(files):,}[/bold] 个文件")
            else:
                console.print(f"  [yellow]组 {gid} 没有文件[/yellow]")
        except ValueError:
            console.print(f"  [red]错误: 无效的组ID: {group_id}[/red]")
    
    console.print()
    conn.close()


@app.command()
def backup(
    backup_path: str = typer.Argument(..., help="备份文件路径"),
    format: str = typer.Option("csv", "--format", "-f", help="备份格式: csv 或 json")
):
    """[bold]备份哈希值[/bold]
    
    [dim]将哈希值备份到文件[/dim]
    """
    import csv
    import json
    
    backup_path = os.path.abspath(backup_path)
    
    if format == "csv" and not backup_path.endswith('.csv'):
        backup_path += '.csv'
    elif format == "json" and not backup_path.endswith('.json'):
        backup_path += '.json'
    
    conn = sqlite3.connect(get_db_path(), timeout=30.0)
    cursor = conn.cursor()
    
    cursor.execute('SELECT Filepath, Size, Modified, Hash, created_at FROM file_hash WHERE Hash IS NOT NULL AND Hash != ""')
    rows = cursor.fetchall()
    conn.close()
    
    if format == "csv":
        with open(backup_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Filepath', 'Size', 'Modified', 'Hash', 'created_at'])
            writer.writerows(rows)
    elif format == "json":
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
    
    console.print()
    console.print("[bold blue]💾 备份哈希值[/bold blue]")
    console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
    console.print()
    console.print(f"  [green]✅ 哈希值已备份[/green]")
    console.print(f"  备份路径    {backup_path}")
    console.print(f"  备份记录    [bold]{len(rows):,}[/bold] 条")
    console.print()


@app.command()
def restore(
    backup_path: str = typer.Argument(..., help="备份文件路径"),
    format: str = typer.Option("auto", "--format", "-f", help="备份格式: auto, csv 或 json"),
    merge: bool = typer.Option(False, "--merge", "-m", help="合并模式（保留现有数据）")
):
    """[bold]还原哈希值[/bold]
    
    [dim]从备份文件还原哈希值[/dim]
    """
    import csv
    import json
    
    backup_path = os.path.abspath(backup_path)
    
    if not os.path.exists(backup_path):
        console.print()
        console.print("[bold blue]📥 还原哈希值[/bold blue]")
        console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
        console.print()
        console.print(f"  [red]错误: 备份文件不存在: {backup_path}[/red]")
        console.print()
        return
    
    if format == "auto":
        if backup_path.endswith('.json'):
            format = "json"
        else:
            format = "csv"
    
    conn = sqlite3.connect(get_db_path(), timeout=30.0)
    cursor = conn.cursor()
    
    console.print()
    console.print("[bold blue]📥 还原哈希值[/bold blue]")
    console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
    console.print()
    console.print(f"  备份文件    {backup_path}")
    console.print(f"  文件格式    {format.upper()}")
    console.print(f"  还原模式    {'合并模式' if merge else '覆盖模式'}")
    console.print()
    
    if not merge:
        cursor.execute('DELETE FROM file_hash')
        console.print("  已清空现有哈希值数据")
    
    imported_count = 0
    skipped_count = 0
    
    if format == "csv":
        with open(backup_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            
            for row in reader:
                if len(row) >= 4:
                    filepath, size, modified, hash_val = row[0], row[1], row[2], row[3]
                    created_at = row[4] if len(row) > 4 else None
                    
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
    
    cursor.execute('SELECT COUNT(*) FROM file_hash WHERE Hash IS NOT NULL AND Hash != ""')
    total_count = cursor.fetchone()[0]
    
    conn.close()
    
    console.print()
    console.print("  [dim]───────────────────────────────────────────────[/dim]")
    console.print("  [green]✅ 哈希值已还原[/green]")
    console.print(f"  导入记录    [bold]{imported_count:,}[/bold] 条")
    if skipped_count > 0:
        console.print(f"  跳过记录    [yellow]{skipped_count:,}[/yellow] 条")
    console.print(f"  当前总数    [bold]{total_count:,}[/bold] 条")
    console.print()
