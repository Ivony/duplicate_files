#!/usr/bin/env python3
"""
Clean 指令 - 重复文件清理

支持两种操作：
- delete: 删除重复文件
- link: 创建软链接替换重复文件

支持三种执行模式：
- immediate: 选择后立即执行
- script: 选择后生成脚本
- summary: 选择后汇总确认
"""
import typer
import sqlite3
import os
from datetime import datetime
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from core.database import get_db_path

app = typer.Typer(
    name="clean",
    help="🧹 清理重复文件"
)
console = Console()

SORT_STRATEGIES = [
    'newest', 'oldest',
    'longest-name', 'shortest-name',
    'longest-path', 'shortest-path',
    'name-asc', 'name-desc',
    'path-asc', 'path-desc',
    'deepest', 'shallowest'
]

MODE_CHOICES = ['immediate', 'script', 'summary']


class FileCleaner:
    def __init__(self, db_path=None):
        self.db_path = db_path or get_db_path()
        self.script_path = None
        self.script_file = None
        self.script_type = None
        self.sort_strategy = 'newest'
        self.group_ids = None
        self.min_size = None
        self.max_size = None
        self.extension = None
        self.disk = None
        self.auto_select = False
        self.mode = 'immediate'
        self.selections = {}
    
    def get_connection(self):
        return sqlite3.connect(self.db_path, timeout=60.0, isolation_level='IMMEDIATE')
    
    def format_size(self, size):
        if size >= 1073741824:
            return f"{size/1073741824:.2f} GB"
        elif size >= 1048576:
            return f"{size/1048576:.2f} MB"
        elif size >= 1024:
            return f"{size/1024:.2f} KB"
        else:
            return f"{size} B"
    
    def parse_size(self, size_str: str) -> int:
        size_str = size_str.upper()
        if size_str.endswith('K'):
            return int(size_str[:-1]) * 1024
        elif size_str.endswith('M'):
            return int(size_str[:-1]) * 1024 * 1024
        elif size_str.endswith('G'):
            return int(size_str[:-1]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def get_strategy_name(self):
        strategy_names = {
            'newest': '保留最新文件',
            'oldest': '保留最旧文件',
            'longest-name': '保留文件名最长的文件',
            'shortest-name': '保留文件名最短的文件',
            'longest-path': '保留路径最长的文件',
            'shortest-path': '保留路径最短的文件',
            'name-asc': '按文件名升序保留第一个',
            'name-desc': '按文件名降序保留第一个',
            'path-asc': '按路径升序保留第一个',
            'path-desc': '按路径降序保留第一个',
            'deepest': '保留目录最深的文件',
            'shallowest': '保留目录最浅的文件'
        }
        return strategy_names.get(self.sort_strategy, '保留最新文件')
    
    def get_sort_key(self):
        def key_func(file_info):
            return {
                'newest': (file_info['modified'],),
                'oldest': (file_info['modified'],),
                'longest-name': (len(file_info['filename']),),
                'shortest-name': (len(file_info['filename']),),
                'longest-path': (len(file_info['filepath']),),
                'shortest-path': (len(file_info['filepath']),),
                'name-asc': (file_info['filename'],),
                'name-desc': (file_info['filename'],),
                'path-asc': (file_info['filepath'],),
                'path-desc': (file_info['filepath'],),
                'deepest': (file_info['depth'],),
                'shallowest': (file_info['depth'],)
            }.get(self.sort_strategy, (file_info['modified'],))
        return key_func
    
    def get_sort_reverse(self):
        reverse_map = {
            'newest': True,
            'oldest': False,
            'longest-name': True,
            'shortest-name': False,
            'longest-path': True,
            'shortest-path': False,
            'name-asc': False,
            'name-desc': True,
            'path-asc': False,
            'path-desc': True,
            'deepest': True,
            'shallowest': False
        }
        return reverse_map.get(self.sort_strategy, True)
    
    def get_groups(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT dg.ID, dg.Size, dg.Extension, dg.Hash, COUNT(*) as file_count
        FROM duplicate_groups dg
        INNER JOIN duplicate_files df ON dg.ID = df.Group_ID
        WHERE dg.Hash IS NOT NULL AND dg.Hash != ''
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
        
        if self.extension:
            query += " AND dg.Extension = ?"
            params.append(self.extension)
        
        if self.disk:
            query += " AND EXISTS (SELECT 1 FROM duplicate_files df2 INNER JOIN files f ON df2.Filepath = f.Filename WHERE df2.Group_ID = dg.ID AND UPPER(SUBSTR(f.Filename, 1, 2)) = ?)"
            params.append(self.disk.upper())
        
        query += ' GROUP BY dg.ID HAVING COUNT(*) > 1 ORDER BY dg.Size DESC'
        
        cursor.execute(query, params)
        groups = cursor.fetchall()
        conn.close()
        
        return groups
    
    def get_group_files(self, group_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT f.Filename, f.Size, f.Modified
        FROM duplicate_files df
        INNER JOIN files f ON df.Filepath = f.Filename
        WHERE df.Group_ID = ?
        ''', (group_id,))
        
        files = []
        for filepath, size, modified in cursor.fetchall():
            if isinstance(modified, str):
                try:
                    dt = datetime.fromisoformat(modified)
                    modified = dt.timestamp()
                except:
                    modified = 0
            
            files.append({
                'filepath': filepath,
                'filename': os.path.basename(filepath),
                'size': size,
                'modified': modified,
                'depth': len(filepath.split(os.sep))
            })
        
        conn.close()
        return files
    
    def select_keep_file(self, files, group_id=None):
        if self.auto_select:
            files.sort(key=self.get_sort_key(), reverse=self.get_sort_reverse())
            return files[0]
        
        files.sort(key=self.get_sort_key(), reverse=self.get_sort_reverse())
        
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("序号", width=6, justify="center")
        table.add_column("文件路径", width=60)
        table.add_column("修改时间", width=20)
        table.add_column("状态", width=10)
        
        for i, f in enumerate(files, 1):
            status = "[green]保留[/green]" if i == 1 else "[red]删除[/red]"
            mtime = datetime.fromtimestamp(f['modified']).strftime('%Y-%m-%d %H:%M:%S')
            table.add_row(str(i), f['filepath'], mtime, status)
        
        console.print(table)
        
        while True:
            choice = Prompt.ask(
                f"选择保留文件 (1-{len(files)})，回车保留第一个，输入 's' 跳过，'q' 退出",
                default="1"
            )
            
            if choice.lower() == 'q':
                return None
            if choice.lower() == 's':
                return 'skip'
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(files):
                    return files[idx]
                console.print("[red]无效的选择[/red]")
            except ValueError:
                console.print("[red]请输入数字[/red]")
    
    def delete_file(self, filepath):
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True, None
            else:
                return False, "文件不存在"
        except Exception as e:
            return False, str(e)
    
    def create_symlink(self, target, link_path):
        try:
            if os.path.exists(link_path):
                os.remove(link_path)
            os.symlink(target, link_path)
            return True, None
        except Exception as e:
            return False, str(e)
    
    def init_script_file(self, script_path):
        self.script_path = script_path
        self.script_type = self._detect_script_type(script_path)
        
        self.script_file = open(self.script_path, 'w', encoding='utf-8')
        self._write_script_header()
        return True
    
    def _detect_script_type(self, script_path):
        ext = os.path.splitext(script_path)[1].lower()
        if ext in ['.cmd', '.bat']:
            return 'cmd'
        elif ext in ['.ps1']:
            return 'powershell'
        else:
            return 'cmd' if os.name == 'nt' else 'bash'
    
    def _write_script_header(self):
        if self.script_type == 'cmd':
            self.script_file.write('@echo off\n')
            self.script_file.write('REM 重复文件清理脚本\n')
            self.script_file.write(f'REM 生成时间: {datetime.now().isoformat()}\n\n')
        elif self.script_type == 'powershell':
            self.script_file.write('# 重复文件清理脚本\n')
            self.script_file.write(f'# 生成时间: {datetime.now().isoformat()}\n\n')
    
    def _write_delete_command(self, filepath):
        if self.script_type == 'cmd':
            self.script_file.write(f'if exist "{filepath}" del /f "{filepath}"\n')
        elif self.script_type == 'powershell':
            self.script_file.write(f'if (Test-Path "{filepath}") {{ Remove-Item -Force "{filepath}" }}\n')
    
    def _write_symlink_command(self, target, link_path):
        if self.script_type == 'cmd':
            self.script_file.write(f'if exist "{link_path}" del /f "{link_path}"\n')
            self.script_file.write(f'mklink "{link_path}" "{target}"\n')
        elif self.script_type == 'powershell':
            self.script_file.write(f'if (Test-Path "{link_path}") {{ Remove-Item -Force "{link_path}" }}\n')
            self.script_file.write(f'New-Item -ItemType SymbolicLink -Path "{link_path}" -Target "{target}"\n')
    
    def close_script_file(self):
        if self.script_file:
            self.script_file.close()
            self.script_file = None
    
    def run(self, action: str):
        groups = self.get_groups()
        
        if not groups:
            console.print("[yellow]没有找到符合条件的重复文件组[/yellow]")
            return
        
        console.print(Panel(
            f"[bold]操作类型:[/bold] {'删除' if action == 'delete' else '创建软链接'}\n"
            f"[bold]排序策略:[/bold] {self.get_strategy_name()}\n"
            f"[bold]执行模式:[/bold] {self.mode}\n"
            f"[bold]找到组数:[/bold] {len(groups)}",
            title="[bold blue]清理配置[/bold blue]"
        ))
        
        if self.mode == 'script' and not self.script_path:
            console.print("[red]错误: script 模式需要指定 --script 参数[/red]")
            return
        
        if self.mode == 'script':
            self.init_script_file(self.script_path)
        
        self.selections = {}
        total_size = 0
        skipped_groups = []
        
        for group_id, size, extension, hash_val, file_count in groups:
            files = self.get_group_files(group_id)
            
            if self.auto_select:
                files.sort(key=self.get_sort_key(), reverse=self.get_sort_reverse())
                self.selections[group_id] = {
                    'keep': files[0],
                    'remove': files[1:],
                    'size': size
                }
                total_size += size * (len(files) - 1)
            else:
                console.print(f"\n[bold]组 #{group_id}[/bold] ({self.format_size(size)}, {file_count} 文件, {extension or '无扩展名'})")
                keep_file = self.select_keep_file(files, group_id)
                
                if keep_file is None:
                    console.print("[yellow]用户取消操作[/yellow]")
                    if self.mode == 'script':
                        self.close_script_file()
                    return
                
                if keep_file == 'skip':
                    skipped_groups.append(group_id)
                    continue
                
                remove_files = [f for f in files if f['filepath'] != keep_file['filepath']]
                self.selections[group_id] = {
                    'keep': keep_file,
                    'remove': remove_files,
                    'size': size
                }
                total_size += size * len(remove_files)
        
        if self.mode == 'summary':
            self._handle_summary_mode(action, total_size)
        elif self.mode == 'script':
            self._handle_script_mode(action)
        else:
            self._handle_immediate_mode(action, total_size)
    
    def _handle_summary_mode(self, action: str, total_size: int):
        console.print(Panel(
            f"[bold]已选择组数:[/bold] {len(self.selections)}\n"
            f"[bold]将处理文件:[/bold] {sum(len(s['remove']) for s in self.selections.values())} 个\n"
            f"[bold]可释放空间:[/bold] {self.format_size(total_size)}",
            title="[bold green]选择汇总[/bold green]"
        ))
        
        console.print("\n[bold]请选择操作:[/bold]")
        console.print("  [D] 立即执行删除")
        console.print("  [L] 立即执行软链接")
        console.print("  [S] 生成脚本")
        console.print("  [C] 取消")
        
        choice = Prompt.ask("选择", choices=['D', 'L', 'S', 'C'], default='C')
        
        if choice == 'C':
            console.print("[yellow]已取消[/yellow]")
            return
        
        if choice == 'S':
            script_path = Prompt.ask("脚本输出路径", default="cleanup.bat")
            self.init_script_file(script_path)
            self._execute_script('delete' if action == 'delete' else 'link')
            self.close_script_file()
            console.print(f"[green]✅ 脚本已生成: {script_path}[/green]")
        else:
            actual_action = 'delete' if choice == 'D' else 'link'
            self._execute_immediate(actual_action, total_size)
    
    def _handle_script_mode(self, action: str):
        self._execute_script(action)
        self.close_script_file()
        console.print(f"[green]✅ 脚本已生成: {self.script_path}[/green]")
    
    def _handle_immediate_mode(self, action: str, total_size: int):
        if not self.auto_select:
            if not Confirm.ask(f"\n确认执行{'删除' if action == 'delete' else '软链接'}操作？"):
                console.print("[yellow]已取消[/yellow]")
                return
        
        self._execute_immediate(action, total_size)
    
    def _execute_immediate(self, action: str, total_size: int):
        success_count = 0
        fail_count = 0
        released_size = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            for group_id, selection in self.selections.items():
                keep_file = selection['keep']
                remove_files = selection['remove']
                size = selection['size']
                
                for remove_file in remove_files:
                    filepath = remove_file['filepath']
                    task = progress.add_task(f"处理: {filepath[:50]}...", total=None)
                    
                    if action == 'delete':
                        success, error = self.delete_file(filepath)
                    else:
                        success, error = self.create_symlink(keep_file['filepath'], filepath)
                    
                    progress.remove_task(task)
                    
                    if success:
                        success_count += 1
                        released_size += size
                    else:
                        fail_count += 1
                        console.print(f"[red]  失败: {filepath} - {error}[/red]")
        
        console.print(Panel(
            f"[bold]处理成功:[/bold] {success_count} 个文件\n"
            f"[bold]处理失败:[/bold] {fail_count} 个文件\n"
            f"[bold]释放空间:[/bold] {self.format_size(released_size)}",
            title="[bold green]执行完成[/bold green]"
        ))
    
    def _execute_script(self, action: str):
        for group_id, selection in self.selections.items():
            keep_file = selection['keep']
            remove_files = selection['remove']
            
            for remove_file in remove_files:
                filepath = remove_file['filepath']
                
                if action == 'delete':
                    self._write_delete_command(filepath)
                else:
                    self._write_symlink_command(keep_file['filepath'], filepath)


def parse_size(size_str: str) -> int:
    if not size_str:
        return None
    size_str = size_str.upper()
    if size_str.endswith('K'):
        return int(size_str[:-1]) * 1024
    elif size_str.endswith('M'):
        return int(size_str[:-1]) * 1024 * 1024
    elif size_str.endswith('G'):
        return int(size_str[:-1]) * 1024 * 1024 * 1024
    else:
        return int(size_str)


@app.command(name="delete")
def delete_cmd(
    yes: bool = typer.Option(False, "--yes", "-y", help="自动选择保留文件"),
    mode: str = typer.Option("immediate", "--mode", "-m", help="执行模式: immediate/script/summary"),
    strategy: str = typer.Option("newest", "--strategy", "-s", help="排序策略"),
    script: Optional[str] = typer.Option(None, "--script", help="脚本输出路径"),
    group: Optional[str] = typer.Option(None, "--group", "-g", help="指定组ID"),
    min_size: Optional[str] = typer.Option(None, "--min-size", help="最小文件大小"),
    max_size: Optional[str] = typer.Option(None, "--max-size", help="最大文件大小"),
    extension: Optional[str] = typer.Option(None, "--extension", "-e", help="扩展名过滤"),
    disk: Optional[str] = typer.Option(None, "--disk", "-d", help="磁盘过滤")
):
    """删除重复文件
    
    删除重复文件，只保留每组中的一个文件
    """
    if strategy not in SORT_STRATEGIES:
        console.print(f"[red]错误: 无效的排序策略 '{strategy}'[/red]")
        console.print(f"[dim]支持的策略: {', '.join(SORT_STRATEGIES)}[/dim]")
        raise typer.Exit(1)
    
    if mode not in MODE_CHOICES:
        console.print(f"[red]错误: 无效的执行模式 '{mode}'[/red]")
        console.print(f"[dim]支持的模式: {', '.join(MODE_CHOICES)}[/dim]")
        raise typer.Exit(1)
    
    cleaner = FileCleaner()
    cleaner.auto_select = yes
    cleaner.mode = mode
    cleaner.sort_strategy = strategy
    cleaner.script_path = script
    
    if group:
        cleaner.group_ids = [int(g.strip()) for g in group.split(',')]
    if min_size:
        cleaner.min_size = parse_size(min_size)
    if max_size:
        cleaner.max_size = parse_size(max_size)
    if extension:
        cleaner.extension = extension if extension.startswith('.') else f'.{extension}'
    if disk:
        cleaner.disk = disk
    
    cleaner.run('delete')


@app.command(name="link")
def link_cmd(
    yes: bool = typer.Option(False, "--yes", "-y", help="自动选择保留文件"),
    mode: str = typer.Option("immediate", "--mode", "-m", help="执行模式: immediate/script/summary"),
    strategy: str = typer.Option("newest", "--strategy", "-s", help="排序策略"),
    script: Optional[str] = typer.Option(None, "--script", help="脚本输出路径"),
    group: Optional[str] = typer.Option(None, "--group", "-g", help="指定组ID"),
    min_size: Optional[str] = typer.Option(None, "--min-size", help="最小文件大小"),
    max_size: Optional[str] = typer.Option(None, "--max-size", help="最大文件大小"),
    extension: Optional[str] = typer.Option(None, "--extension", "-e", help="扩展名过滤"),
    disk: Optional[str] = typer.Option(None, "--disk", "-d", help="磁盘过滤")
):
    """创建软链接替换重复文件
    
    删除重复文件并创建软链接指向保留文件
    """
    if strategy not in SORT_STRATEGIES:
        console.print(f"[red]错误: 无效的排序策略 '{strategy}'[/red]")
        console.print(f"[dim]支持的策略: {', '.join(SORT_STRATEGIES)}[/dim]")
        raise typer.Exit(1)
    
    if mode not in MODE_CHOICES:
        console.print(f"[red]错误: 无效的执行模式 '{mode}'[/red]")
        console.print(f"[dim]支持的模式: {', '.join(MODE_CHOICES)}[/dim]")
        raise typer.Exit(1)
    
    cleaner = FileCleaner()
    cleaner.auto_select = yes
    cleaner.mode = mode
    cleaner.sort_strategy = strategy
    cleaner.script_path = script
    
    if group:
        cleaner.group_ids = [int(g.strip()) for g in group.split(',')]
    if min_size:
        cleaner.min_size = parse_size(min_size)
    if max_size:
        cleaner.max_size = parse_size(max_size)
    if extension:
        cleaner.extension = extension if extension.startswith('.') else f'.{extension}'
    if disk:
        cleaner.disk = disk
    
    cleaner.run('link')


if __name__ == "__main__":
    app()
