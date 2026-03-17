import typer
import os
from typing import Optional, List
from rich.console import Console
from core.dataloader import DataLoader
from core.ui import BlockPager

app = typer.Typer(
    name="show",
    help="📊 显示信息"
)
analyzer = DataLoader()


def _parse_size(size_str: str) -> int:
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


def _show_group_detail(group_id: int):
    """显示指定组的详细信息"""
    console = Console(emoji=True)
    group = analyzer.get_group_details(group_id)

    if not group:
        console.print(f"[red]错误: 找不到组ID: {group_id}[/red]")
        return

    def format_size(size):
        if size >= 1073741824:
            return f"{size/1073741824:.2f} GB"
        elif size >= 1048576:
            return f"{size/1048576:.2f} MB"
        elif size >= 1024:
            return f"{size/1024:.2f} KB"
        else:
            return f"{size} B"
    
    def format_size_colored(size):
        if size >= 1073741824:
            return f"[bold red]{size/1073741824:.2f} GB[/bold red]"
        elif size >= 1048576:
            return f"[bold yellow]{size/1048576:.2f} MB[/bold yellow]"
        elif size >= 1024:
            return f"[bold green]{size/1024:.2f} KB[/bold green]"
        else:
            return f"[bold]{size} B[/bold]"

    console.print()
    console.print(f"[bold blue]📁 组 #{group_id} 详细信息[/bold blue]")
    console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
    console.print()
    console.print(f"  文件大小      {format_size_colored(group['size'])}")
    console.print(f"  文件扩展名    [bold]{group['extension'] or '无'}[/bold]")
    console.print(f"  文件数量      [bold]{group['file_count']}[/bold] 个")
    console.print(f"  可释放空间    {format_size_colored(group['savable_space'])}")
    
    if group['hash']:
        console.print(f"  哈希值        [dim]{group['hash'][:16]}...[/dim]")
    else:
        console.print(f"  哈希值        [yellow]未确认[/yellow]")
    
    console.print()
    console.print("  [dim]───────────────────────────────────────────────[/dim]")
    console.print("  📄 包含的文件")
    console.print()
    
    for i, file_info in enumerate(group['files'], 1):
        console.print(f"    [dim]{i}.[/dim] {file_info['filepath']}")
    
    console.print()
    console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
    console.print()


@app.command()
def groups(
    unconfirmed: bool = False,
    min_size: Optional[str] = None,
    max_size: Optional[str] = None,
    extension: Optional[str] = None,
    sort: str = "size",
    detail: Optional[int] = None,
    disk: Optional[str] = None,
    hash: Optional[str] = None,
    pager: bool = True
):
    """[bold]显示重复文件组列表[/bold]
    
    [dim]显示已确认的重复文件组，按大小排序[/dim]
    
    [dim]排序选项: size (大小), count (数量), path (路径), ext (扩展名), hash (哈希值)[/dim]
    """
    console = Console(emoji=True)
    hash_only = not unconfirmed
    hash_value = hash
    
    def format_size(size):
        if size >= 1073741824:
            return f"{size/1073741824:.2f} GB"
        elif size >= 1048576:
            return f"{size/1048576:.2f} MB"
        elif size >= 1024:
            return f"{size/1024:.2f} KB"
        else:
            return f"{size} B"
    
    def format_size_colored(size):
        if size >= 1073741824:
            return f"[bold red]{size/1073741824:.2f} GB[/bold red]"
        elif size >= 1048576:
            return f"[bold yellow]{size/1048576:.2f} MB[/bold yellow]"
        elif size >= 1024:
            return f"[bold green]{size/1024:.2f} KB[/bold green]"
        else:
            return f"[bold]{size} B[/bold]"
    
    parsed_min_size = _parse_size(min_size) if min_size else None
    parsed_max_size = _parse_size(max_size) if max_size else None
    
    if detail is not None:
        _show_group_detail(detail)
        return
    
    if hash_value:
        title = f"哈希值 {hash_value[:16]}... 的重复文件组"
    else:
        title = "重复文件组列表"
    
    total_count = analyzer.get_groups_count(
        hash_only=hash_only,
        min_size=parsed_min_size,
        max_size=parsed_max_size,
        extension=extension,
        disk=disk,
        hash_value=hash_value
    )
    
    if total_count == 0:
        console.print()
        console.print(f"[bold blue]📁 {title}[/bold blue]")
        console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
        console.print()
        console.print("  [dim]没有找到符合条件的重复文件组[/dim]")
        console.print()
        return
    
    def block_provider(start_idx: int, count: int) -> List[str]:
        """数据提供函数，按需获取数据块"""
        groups_batch = analyzer.get_groups_batch(
            start_idx=start_idx,
            count=count,
            hash_only=hash_only,
            min_size=parsed_min_size,
            max_size=parsed_max_size,
            extension=extension,
            sort_by=sort,
            disk=disk,
            hash_value=hash_value
        )
        
        blocks = []
        for group in groups_batch:
            if group['hash']:
                hash_status = "✅"
            else:
                hash_status = "⏳"
            
            ext_display = group['extension'] or "(无)"
            
            block_lines = [
                f"  📁 [bold cyan]组 #{group['group_id']}[/bold cyan] | {format_size_colored(group['size'])} | [dim]{ext_display}[/dim] | [bold]{group['file_count']}[/bold] 文件 | 可释放 {format_size_colored(group['savable_space'])} | {hash_status}"
            ]
            
            for filepath in group['files'][:3]:
                block_lines.append(f"     [dim]{filepath}[/dim]")
            
            if len(group['files']) > 3:
                block_lines.append(f"     [dim]... 还有 {len(group['files']) - 3} 个文件[/dim]")
            
            blocks.append("\n".join(block_lines))
        
        return blocks
    
    sort_names = {
        "size": "大小",
        "count": "数量",
        "path": "路径",
        "ext": "扩展名",
        "hash": "哈希值"
    }
    sort_display = sort_names.get(sort, sort)
    
    if pager:
        block_pager = BlockPager(
            total_count=total_count,
            block_provider=block_provider,
            console=console,
            title=title,
            page_size=20,
            sort_mode=sort_display
        )
        block_pager.run()
    else:
        console.print()
        console.print(f"[bold blue]📁 {title}[/bold blue]")
        console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
        console.print()
        console.print(f"  [bold]统计信息:[/bold] 共 [green]{total_count:,}[/green] 个组")
        console.print()
        
        blocks = block_provider(0, min(100, total_count))
        for block in blocks:
            console.print(block)
        
        console.print("[dim]─────────────────────────────────────────────────────────────────────────────────────────────────[/dim]")
        console.print()
        console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
        console.print()


@app.command()
def files(
    pattern: str,
    all: bool = False,
    hash: bool = False,
    pager: bool = True
):
    """[bold]查询文件，支持路径或模式[/bold]
    
    [dim]搜索重复文件组或已索引的文件[/dim]
    """
    console = Console(emoji=True)
    show_all = all
    show_hash = hash
    
    def format_size(size):
        if size >= 1073741824:
            return f"{size/1073741824:.2f} GB"
        elif size >= 1048576:
            return f"{size/1048576:.2f} MB"
        elif size >= 1024:
            return f"{size/1024:.2f} KB"
        else:
            return f"{size} B"
    
    def format_size_colored(size):
        if size >= 1073741824:
            return f"[bold red]{size/1073741824:.2f} GB[/bold red]"
        elif size >= 1048576:
            return f"[bold yellow]{size/1048576:.2f} MB[/bold yellow]"
        elif size >= 1024:
            return f"[bold green]{size/1024:.2f} KB[/bold green]"
        else:
            return f"[bold]{size} B[/bold]"
    
    has_wildcard = '*' in pattern or '?' in pattern
    
    is_full_path = False
    if not has_wildcard:
        if len(pattern) >= 2 and pattern[1] == ':' and (pattern[0].isalpha()):
            is_full_path = True
        elif pattern.startswith('\\') or pattern.startswith('/'):
            is_full_path = True
    
    def render_output():
        if has_wildcard or not is_full_path:
            hash_only = not show_all
            groups = analyzer.filter_by_pattern(pattern, hash_only=hash_only)
            
            unhashed_count = 0
            if not show_all:
                all_groups = analyzer.filter_by_pattern(pattern, hash_only=False)
                unhashed_count = len(all_groups) - len(groups)
            
            console.print()
            console.print(f"[bold blue]🔍 文件搜索结果（模式: {pattern}）[/bold blue]")
            console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
            console.print()
            
            if not groups:
                console.print("  [dim]没有找到匹配的文件[/dim]")
                if unhashed_count > 0:
                    console.print()
                    console.print(f"  [yellow]提示: 有 {unhashed_count} 个组因未计算哈希值而被隐藏[/yellow]")
                    console.print("  [dim]使用 --all 选项显示所有组（包括未计算哈希的）[/dim]")
            else:
                console.print(f"  找到 [bold green]{len(groups)}[/bold green] 个匹配的重复文件组")
                console.print()
                for i, group in enumerate(groups, 1):
                    console.print(f"  [cyan]{i}. 组ID: {group['group_id']}[/cyan]")
                    console.print(f"    文件大小      {format_size_colored(group['size'])}")
                    console.print(f"    文件扩展名    [bold]{group['extension']}[/bold]")
                    console.print(f"    文件数量      [bold]{group['file_count']}[/bold] 个")
                    console.print("    匹配的文件:")
                    for j, filepath in enumerate(group['matched_files'][:5], 1):
                        console.print(f"      [dim]{j}.[/dim] {filepath}")
                    if len(group['matched_files']) > 5:
                        console.print(f"      [dim]... 还有 {len(group['matched_files']) - 5} 个匹配文件[/dim]")
                    console.print()
                
                if unhashed_count > 0:
                    console.print(f"  [yellow]提示: 还有 {unhashed_count} 个组因未计算哈希值而被隐藏[/yellow]")
                    console.print("  [dim]使用 --all 选项显示所有组（包括未计算哈希的）[/dim]")
            
            console.print()
            console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
            console.print()
        else:
            if show_all:
                conn = analyzer.get_connection()
                cursor = conn.cursor()
                
                normalized_pattern = pattern.replace('\\', '/').lower()
                
                query = '''
                    SELECT f.Filename, f.Size, f.Modified, fh.Hash, fh.created_at
                    FROM files f
                    LEFT JOIN file_hash fh ON f.Filename = fh.Filepath
                    WHERE LOWER(REPLACE(f.Filename, '\\\\', '/')) LIKE ?
                    ORDER BY f.Filename
                '''
                cursor.execute(query, (f"{normalized_pattern}%",))
                files = cursor.fetchall()
                conn.close()
                
                console.print()
                console.print(f"[bold blue]📂 路径 {pattern} 下已索引的文件[/bold blue]")
                console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
                console.print()
                
                if not files:
                    console.print("  [dim]没有找到已索引的文件[/dim]")
                else:
                    for i, (filename, size, modified, hash_val, created_at) in enumerate(files, 1):
                        hash_status = "[green]已计算[/green]" if hash_val else "[yellow]未计算[/yellow]"
                        console.print(f"  [dim]{i}.[/dim] {filename}")
                        console.print(f"    大小: {format_size_colored(size)}    修改时间: [dim]{modified}[/dim]    哈希状态: {hash_status}")
                        if show_hash and hash_val:
                            console.print(f"    哈希值: [dim]{hash_val[:16]}...[/dim]")
                            if created_at:
                                console.print(f"    计算时间: [dim]{created_at}[/dim]")
                        console.print()
                
                console.print()
                console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
                console.print()
            else:
                hash_only = not show_all
                groups = analyzer.get_groups_by_path(pattern, hash_only=hash_only)
                
                unhashed_count = 0
                if not show_all:
                    all_groups = analyzer.get_groups_by_path(pattern, hash_only=False)
                    unhashed_count = len(all_groups) - len(groups)
                
                console.print()
                console.print(f"[bold blue]📂 路径 {pattern} 下的重复文件[/bold blue]")
                console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
                console.print()
                
                if not groups:
                    console.print("  [dim]没有找到重复文件[/dim]")
                    if unhashed_count > 0:
                        console.print()
                        console.print(f"  [yellow]提示: 有 {unhashed_count} 个组因未计算哈希值而被隐藏[/yellow]")
                        console.print("  [dim]使用 --all 选项显示所有组（包括未计算哈希的）[/dim]")
                else:
                    console.print(f"  找到 [bold green]{len(groups)}[/bold green] 个重复文件组")
                    console.print()
                    for i, group in enumerate(groups, 1):
                        console.print(f"  [cyan]{i}. 组ID: {group['group_id']}[/cyan]")
                        console.print(f"    文件大小      {format_size_colored(group['size'])}")
                        console.print(f"    文件扩展名    [bold]{group['extension']}[/bold]")
                        console.print(f"    文件数量      [bold]{group['file_count']}[/bold] 个")
                        console.print("    包含的文件:")
                        for j, filepath in enumerate(group['files'][:5], 1):
                            console.print(f"      [dim]{j}.[/dim] {filepath}")
                        if len(group['files']) > 5:
                            console.print(f"      [dim]... 还有 {len(group['files']) - 5} 个文件[/dim]")
                        console.print()
                    
                    if unhashed_count > 0:
                        console.print(f"  [yellow]提示: 还有 {unhashed_count} 个组因未计算哈希值而被隐藏[/yellow]")
                        console.print("  [dim]使用 --all 选项显示所有组（包括未计算哈希的）[/dim]")
                
                console.print()
                console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
                console.print()
    
    if pager:
        with console.pager(styles=True):
            render_output()
    else:
        render_output()


@app.command()
def stats(
    by_extension: bool = False,
    by_size_range: bool = False,
    by_date: bool = False
):
    """[bold]显示统计分析[/bold]
    
    [dim]显示文件、重复组和类型分析的统计信息[/dim]
    """
    console = Console(emoji=True)
    
    def format_size(size):
        if size >= 1073741824:
            return f"{size/1073741824:.2f} GB"
        elif size >= 1048576:
            return f"{size/1048576:.2f} MB"
        elif size >= 1024:
            return f"{size/1024:.2f} KB"
        else:
            return f"{size} B"
    
    def format_size_colored(size):
        if size >= 1073741824:
            return f"[bold red]{size/1073741824:.2f} GB[/bold red]"
        elif size >= 1048576:
            return f"[bold yellow]{size/1048576:.2f} MB[/bold yellow]"
        elif size >= 1024:
            return f"[bold green]{size/1024:.2f} KB[/bold green]"
        else:
            return f"[bold]{size} B[/bold]"
    
    def print_progress_bar(progress, width=30):
        filled = int(progress / 100 * width)
        return f"[green]{'█' * filled}[/green][dim]{'░' * (width - filled)}[/dim]"
    
    if by_extension:
        stats = analyzer.get_stats_by_extension()
        console.print()
        console.print("[bold blue]📊 按扩展名统计[/bold blue]")
        console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
        console.print()
        for ext, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            console.print(f"  {ext or '(无扩展名)':<15} [bold green]{count:,}[/bold green] 个组")
        console.print()
    elif by_size_range:
        stats = analyzer.get_stats_by_size_range()
        console.print()
        console.print("[bold blue]📊 按大小范围统计[/bold blue]")
        console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
        console.print()
        size_order = ['< 1MB', '1MB - 10MB', '10MB - 100MB', '100MB - 1GB', '> 1GB']
        for range_name in size_order:
            if range_name in stats:
                console.print(f"  {range_name:<15} [bold green]{stats[range_name]:,}[/bold green] 个组")
        console.print()
    elif by_date:
        stats = analyzer.get_stats_by_date()
        console.print()
        console.print("[bold blue]📊 按日期统计[/bold blue]")
        console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
        console.print()
        for date, count in stats.items():
            console.print(f"  {date:<15} [bold green]{count:,}[/bold green] 个组")
        console.print()
    else:
        stats = analyzer.get_statistics()
        
        console.print()
        
        console.print("[bold blue]📄 文件统计信息[/bold blue]")
        console.print("[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")
        console.print()
        console.print(f"  扫描文件数          [bold]{stats['total_files']:,}[/bold]")
        console.print(f"  文件总大小          {format_size_colored(stats['total_size'])}")
        console.print(f"  已计算哈希文件      [bold green]{stats['hashed_files']:,}[/bold green]")
        console.print(f"  待计算哈希文件      [bold yellow]{stats['unhashed_files']:,}[/bold yellow]")
        console.print()
        
        console.print("  [dim]───────────────────────────────────────────────[/dim]")
        console.print("  💿 磁盘分布")
        if stats['disk_distribution']:
            for disk, info in stats['disk_distribution'].items():
                console.print(f"    {disk}    {info['file_count']:,} 个文件")
        else:
            console.print("    暂无数据")
        console.print()
        
        if stats['duplicate_files_total_size'] > 0:
            hash_progress = stats['hashed_size'] / stats['duplicate_files_total_size'] * 100
        else:
            hash_progress = 0
        
        console.print("  [dim]───────────────────────────────────────────────[/dim]")
        console.print("  ⏳ 哈希计算进度")
        console.print(f"  已计算 {format_size(stats['hashed_size'])} / {format_size(stats['duplicate_files_total_size'])}")
        console.print(f"  {print_progress_bar(hash_progress)} [bold]{hash_progress:.1f}%[/bold]")
        console.print()
        
        console.print("  [dim]───────────────────────────────────────────────[/dim]")
        console.print("  📊 重复文件统计")
        console.print()
        console.print(f"  重复文件组          [bold]{stats['total_groups']:,}[/bold]")
        console.print(f"  已确认哈希组        [bold green]{stats['hashed_groups']:,}[/bold green]")
        console.print(f"  未确认哈希组        [bold yellow]{stats['unhashed_groups']:,}[/bold yellow]")
        console.print(f"  重复文件关联        [bold]{stats['total_duplicate_files']:,}[/bold]")
        console.print(f"  已确认重复文件      [bold green]{stats['confirmed_duplicate_files']:,}[/bold green]")
        console.print()
        
        console.print("  [dim]───────────────────────────────────────────────[/dim]")
        console.print("  💾 空间统计")
        console.print()
        console.print(f"  可释放空间          {format_size_colored(stats['savable_size'])}")
        console.print(f"  平均每组文件数      [bold]{stats['avg_duplication']:.1f}[/bold]")
        console.print(f"  平均组大小          {format_size_colored(stats['avg_group_size'])}")
        console.print()
        
        console.print("  [dim]───────────────────────────────────────────────[/dim]")
        console.print("  📈 TOP 10 扩展名（按可释放空间）")
        console.print()
        for ext_info in stats['top_extensions']:
            console.print(f"    {ext_info['extension']:<15} {ext_info['group_count']:>5} 个组    可释放 {format_size_colored(ext_info['savable_space'])}")
        console.print()
        
        console.print("  [dim]───────────────────────────────────────────────[/dim]")
        console.print("  📏 大小分布")
        console.print()
        size_order = ['< 1MB', '1MB - 10MB', '10MB - 100MB', '100MB - 1GB', '> 1GB']
        for range_name in size_order:
            if range_name in stats['size_distribution']:
                info = stats['size_distribution'][range_name]
                console.print(f"    {range_name:<15} {info['group_count']:>5} 个组    可释放 {format_size_colored(info['savable_space'])}")
        console.print()
        console.print(f"  数据库大小: {format_size_colored(stats['db_size'])}      跨磁盘重复组: [bold]{stats['cross_disk_groups']:,}[/bold] 个")
        console.print()
