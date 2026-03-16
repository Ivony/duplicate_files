import sys
import shutil
from typing import Optional, List, Callable
from rich.console import Console
from rich.live import Live


def get_key_non_blocking(timeout: float = 0.1) -> Optional[str]:
    """非阻塞获取按键（跨平台）
    
    Args:
        timeout: 超时时间（秒）
    
    Returns:
        按键字符串，超时返回 None
    """
    if sys.platform == 'win32':
        import msvcrt
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            if ch == b'\x03':
                raise KeyboardInterrupt
            elif ch == b'\xe0':
                ch2 = msvcrt.getch()
                if ch2 == b'H':
                    return '\x1b[A'
                elif ch2 == b'P':
                    return '\x1b[B'
                elif ch2 == b'I':
                    return '\x1b[5~'
                elif ch2 == b'Q':
                    return '\x1b[6~'
                elif ch2 == b'G':
                    return '\x1b[H'
                elif ch2 == b'O':
                    return '\x1b[F'
            return ch.decode('utf-8', errors='ignore')
        return None
    else:
        import select
        import tty
        import termios
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())
            if select.select([sys.stdin], [], [], timeout)[0]:
                ch = sys.stdin.read(1)
                if ch == '\x03':
                    raise KeyboardInterrupt
                elif ch == '\x1b':
                    import time
                    time.sleep(0.01)
                    if select.select([sys.stdin], [], [], 0.01)[0]:
                        ch2 = sys.stdin.read(1)
                        if ch2 == '[':
                            if select.select([sys.stdin], [], [], 0.01)[0]:
                                ch3 = sys.stdin.read(1)
                                if ch3 == 'A':
                                    return '\x1b[A'
                                elif ch3 == 'B':
                                    return '\x1b[B'
                                elif ch3 == '5':
                                    sys.stdin.read(1)
                                    return '\x1b[5~'
                                elif ch3 == '6':
                                    sys.stdin.read(1)
                                    return '\x1b[6~'
                                elif ch3 == 'H':
                                    return '\x1b[H'
                                elif ch3 == 'F':
                                    return '\x1b[F'
                                elif ch3 == '1':
                                    sys.stdin.read(1)
                                    return '\x1b[1~'
                                elif ch3 == '4':
                                    sys.stdin.read(1)
                                    return '\x1b[4~'
                return ch
            return None
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


class BlockPager:
    """块级分页器 - 使用Rich Live实现多行文本块分页显示，支持增量加载
    
    功能特性：
    - 块级滚动：按完整文本块滚动，不是一行一行滚
    - 增量加载：按需加载数据，支持大数据量
    - 全屏显示：最大化利用终端空间
    - 跨平台按键：支持 Windows 和 Unix 系统的特殊按键
    
    操作方式：
    - ↑/↓：上一个/下一个完整文本块
    - PageUp/PageDown：整屏翻页
    - Home/End：跳转到开头/末尾
    - q：退出程序
    """
    
    def __init__(
        self,
        total_count: int,
        block_provider: Callable[[int, int], List[str]],
        console: Console = None,
        title: str = "数据列表",
        page_size: int = 20,
        sort_mode: str = None
    ):
        """
        初始化块级分页器
        
        Args:
            total_count: 总数据块数
            block_provider: 数据提供函数，参数为(start_idx, count)，返回文本块列表
            console: Rich Console实例
            title: 标题
            page_size: 每页预加载的块数
            sort_mode: 排序模式（可选，用于显示）
        """
        self.total_blocks = total_count
        self.block_provider = block_provider
        self.console = console or Console(emoji=True)
        self.title = title
        self.page_size = page_size
        self.sort_mode = sort_mode
        self.current_block_idx = 0
        self.blocks_per_screen = 1
        self.cached_blocks = {}
        self.current_page = -1
        self._calculate_screen_capacity()
    
    def _calculate_screen_capacity(self):
        """计算屏幕容量"""
        terminal_height = shutil.get_terminal_size().lines
        reserved_lines = 4
        available_height = terminal_height - reserved_lines
        estimated_block_height = 5
        self.blocks_per_screen = max(1, available_height // estimated_block_height)
    
    def _load_page(self, page: int):
        """加载指定页的数据"""
        if page == self.current_page:
            return
        
        start_idx = page * self.page_size
        if start_idx >= self.total_blocks:
            return
        
        end_idx = min(start_idx + self.page_size, self.total_blocks)
        
        try:
            blocks = self.block_provider(start_idx, end_idx - start_idx)
            for i, block in enumerate(blocks):
                self.cached_blocks[start_idx + i] = block
            self.current_page = page
        except Exception:
            pass
    
    def _get_block(self, idx: int) -> Optional[str]:
        """获取指定索引的块"""
        if idx < 0 or idx >= self.total_blocks:
            return None
        
        if idx not in self.cached_blocks:
            page = idx // self.page_size
            self._load_page(page)
        
        return self.cached_blocks.get(idx)
    
    def _get_visible_blocks(self) -> List[str]:
        """获取当前可见的文本块"""
        blocks = []
        for i in range(self.current_block_idx, min(self.current_block_idx + self.blocks_per_screen, self.total_blocks)):
            block = self._get_block(i)
            if block:
                blocks.append(block)
        return blocks
    
    def _get_header_line(self) -> str:
        """获取标题行"""
        start_idx = self.current_block_idx
        end_idx = start_idx + len(self._get_visible_blocks())
        
        parts = [f"[bold cyan]{self.title}[/bold cyan]"]
        parts.append(f"[bold]总数:[/bold] [green]{self.total_blocks:,}[/green]")
        parts.append(f"[bold]当前:[/bold] {start_idx + 1}-{end_idx}")
        
        if self.sort_mode:
            parts.append(f"[bold]排序:[/bold] {self.sort_mode}")
        
        return " | ".join(parts)
    
    def _render_content(self) -> str:
        """渲染当前内容（全屏显示，无外框）"""
        visible_blocks = self._get_visible_blocks()
        
        terminal_width = shutil.get_terminal_size().columns
        separator = "─" * (terminal_width - 2)
        
        lines = []
        
        lines.append(self._get_header_line())
        lines.append(f"[dim]{separator}[/dim]")
        
        for i, block in enumerate(visible_blocks):
            if i > 0:
                lines.append(f"[dim]{separator}[/dim]")
            lines.append(block)
        
        if not visible_blocks:
            lines.append("[dim]加载中...[/dim]")
        
        lines.append("")
        lines.append(f"[dim]{separator}[/dim]")
        lines.append("[dim]↑/↓ 上下翻块 | PageUp/PageDown 整屏翻页 | Home/End 首尾 | q 退出[/dim]")
        
        return "\n".join(lines)
    
    def run(self):
        """启动交互式分页显示"""
        if self.total_blocks == 0:
            self.console.print(f"\n[bold cyan]{self.title}[/bold cyan]")
            self.console.print("[dim]没有数据[/dim]\n")
            return
        
        self._load_page(0)
        
        with Live(self._render_content(), console=self.console, refresh_per_second=10, screen=True) as live:
            while True:
                try:
                    key = get_key_non_blocking(timeout=0.1)
                    
                    if key is None:
                        continue
                    
                    if key == "q" or key == "Q":
                        break
                    elif key == "\x1b[A" or key == "k":
                        self.current_block_idx = max(0, self.current_block_idx - 1)
                    elif key == "\x1b[B" or key == "j":
                        self.current_block_idx = min(self.total_blocks - self.blocks_per_screen, self.current_block_idx + 1)
                    elif key == "\x1b[5~":
                        self.current_block_idx = max(0, self.current_block_idx - self.blocks_per_screen)
                    elif key == "\x1b[6~":
                        self.current_block_idx = min(self.total_blocks - self.blocks_per_screen, self.current_block_idx + self.blocks_per_screen)
                    elif key == "\x1b[H" or key == "\x1b[1~":
                        self.current_block_idx = 0
                    elif key == "\x1b[F" or key == "\x1b[4~":
                        self.current_block_idx = max(0, self.total_blocks - self.blocks_per_screen)
                    
                    live.update(self._render_content())
                    
                except (KeyboardInterrupt, EOFError):
                    break
