#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重复文件查找工具 - 主入口
"""

import sys
from pathlib import Path

import typer
from rich.console import Console
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion, PathCompleter

from commands.config import ConfigManager
from commands.index import IndexManager
from commands.index import FileScanner
from commands.hash import HashCalculator
from commands import index, show, hash, export, clean, config, db

app = typer.Typer(
    name="duplicate",
    help="🔍 重复文件查找工具"
)

app.add_typer(index.app, name="index")
app.add_typer(show.app, name="show")
app.add_typer(hash.app, name="hash")
app.add_typer(export.app, name="export")
app.add_typer(clean.app, name="clean")
app.add_typer(config.app, name="config")
app.add_typer(db.app, name="db")

# 初始化控制台
console = Console()


class TyperCompleter(Completer):
    """基于Typer应用元数据的上下文感知补全器"""
    
    def __init__(self, app):
        self.app = app
        self.root_commands = {}  # 根命令 -> 子命令列表
        self.standalone_commands = []  # 独立命令（如version, help）
        self.path_completion_commands = {
            # 必须是现有文件
            ('index', 'import'): PathCompleter(file_filter=lambda path: path.endswith('.csv')),
            ('hash', 'restore'): PathCompleter(),
            
            # 必须是现有文件或文件夹
            ('index', 'scan'): PathCompleter(only_directories=True),
            ('config', 'limit'): PathCompleter(only_directories=True),
            ('show', 'files'): PathCompleter(),
            
            # 有效的文件路径不一定要存在
            ('export', 'csv'): PathCompleter(),
            ('export', 'json'): PathCompleter(),
            ('export', 'report'): PathCompleter(),
            ('hash', 'backup'): PathCompleter(),
            ('clean', 'script'): PathCompleter(),
            ('db', 'backup_database'): PathCompleter(),
            ('db', 'backup_file_hash'): PathCompleter(),
        }
        self._extract_commands()
    
    def _extract_commands(self):
        """从Typer应用中提取命令信息"""
        # 从 registered_groups 中提取通过 add_typer 添加的命令
        for typer_info in self.app.registered_groups:
            # 从 TyperInfo 对象中获取命令名称和命令对象
            command_name = typer_info.name
            command = typer_info.typer_instance
            
            # 过滤掉 None 值
            if command_name is None:
                continue
            
            if hasattr(command, 'registered_commands'):
                # 有子命令的根命令
                sub_commands = []
                for subcommand_info in command.registered_commands:
                    subcommand_name = subcommand_info.name
                    # 如果 name 为 None，尝试从 callback.__name__ 获取
                    if subcommand_name is None and hasattr(subcommand_info, 'callback'):
                        subcommand_name = subcommand_info.callback.__name__
                    if subcommand_name is not None:
                        sub_commands.append(subcommand_name)
                self.root_commands[command_name] = sub_commands
            else:
                # 独立命令
                self.standalone_commands.append(command_name)
        
        # 从 registered_commands 中提取通过 @app.command() 添加的命令
        for command_info in self.app.registered_commands:
            # 从 CommandInfo 对象中获取命令名称和命令对象
            command_name = command_info.name
            # 如果 name 为 None，尝试从 callback.__name__ 获取
            if command_name is None and hasattr(command_info, 'callback'):
                command_name = command_info.callback.__name__
            
            # 过滤掉 None 值
            if command_name is None:
                continue
            
            # 这些是独立命令
            self.standalone_commands.append(command_name)
        
        # 添加 'help' 命令（Typer 自动添加的）
        if 'help' not in self.standalone_commands:
            self.standalone_commands.append('help')
    
    def get_completions(self, document, complete_event):
        """生成补全建议"""
        text = document.text
        words = text.split()
        
        # 辅助函数：检查字符串是否是选项（以 -- 或 - 开头）
        def is_option(s):
            return s.startswith('--') or (s.startswith('-') and len(s) > 1 and s[1] != '\\' and s[1] != '/')
        
        # 辅助函数：检查字符串是否是路径的一部分
        def is_path_part(s):
            return '\\' in s or '/' in s or ':' in s
        
        # 检查是否需要路径补全（带选项的命令，如 'clean script --output '）
        if len(words) >= 3:
            root_cmd = words[0]
            sub_cmd = words[1]
            third_word = words[2]
            
            # 只有当第三个词是选项时，才进入带选项的路径补全逻辑
            if is_option(third_word) and (root_cmd, sub_cmd) in self.path_completion_commands:
                # 提取路径补全器
                path_completer = self.path_completion_commands[(root_cmd, sub_cmd)]
                
                # 提取路径部分
                command_prefix = f"{root_cmd} {sub_cmd} {third_word} "
                path_part = text[len(command_prefix):] if text.startswith(command_prefix) else text
                
                # 只有当路径部分包含路径分隔符（\ 或 /）时才触发补全
                if '\\' not in path_part and '/' not in path_part:
                    return
                
                # 创建只包含路径部分的临时文档
                from prompt_toolkit.document import Document
                path_document = Document(path_part, len(path_part))
                
                # 使用路径补全器生成补全
                for completion in path_completer.get_completions(path_document, complete_event):
                    # 计算正确的 start_position：从当前光标位置向左偏移到路径部分的开始
                    # 注意：start_position 是负数，表示从当前光标位置向左的偏移量
                    # 我们只希望替换路径部分，而不是整个命令
                    # 当用户输入部分路径时，应该从路径部分的开始位置替换
                    start_position = -(document.cursor_position - len(command_prefix))
                    # 确保 start_position 是负数
                    start_position = min(start_position, 0)
                    
                    # 提取完整的补全文本
                    # 从 display 中提取完整路径，因为 display 通常包含完整的路径信息
                    if hasattr(completion.display, 'text'):
                        complete_text = completion.display.text
                    elif hasattr(completion.display, '__iter__'):
                        # 处理 FormattedText
                        complete_text = ''.join([part[1] for part in completion.display if isinstance(part, tuple)])
                    else:
                        complete_text = completion.text
                    
                    # 移除末尾的斜杠
                    complete_text = complete_text.rstrip('/').rstrip('\\')
                    
                    # 处理路径前缀：如果输入包含路径前缀（如C:\），确保补全结果包含完整路径
                    if '\\' in path_part or '/' in path_part:
                        # 找到最后一个路径分隔符的位置（无论是 \ 还是 /）
                        last_backslash = path_part.rfind('\\')
                        last_slash = path_part.rfind('/')
                        last_sep_pos = max(last_backslash, last_slash)
                        
                        if last_sep_pos > 0:
                            # 提取最后一个分隔符之前的部分作为前缀
                            prefix = path_part[:last_sep_pos]
                            # 使用原始分隔符
                            separator = path_part[last_sep_pos]
                            prefix += separator
                        elif last_sep_pos == 0:
                            # 分隔符在开头（如 \ 或 /）
                            prefix = path_part[0]
                        else:
                            prefix = ''
                        
                        # 组合完整路径
                        complete_text = prefix + complete_text
                    
                    # 创建新的 Completion 对象
                    yield Completion(
                        text=complete_text,
                        start_position=start_position,
                        display=completion.display,
                        display_meta=completion.display_meta,
                        style=completion.style,
                        selected_style=completion.selected_style
                    )
                return
        
        # 检查是否需要路径补全（普通命令，如 'index scan C:\'）
        if len(words) >= 2:
            root_cmd = words[0]
            sub_cmd = words[1]
            
            # 检查是否是需要路径补全的命令
            if (root_cmd, sub_cmd) in self.path_completion_commands:
                # 提取路径补全器
                path_completer = self.path_completion_commands[(root_cmd, sub_cmd)]
                
                # 提取路径部分
                command_prefix = f"{root_cmd} {sub_cmd} "
                path_part = text[len(command_prefix):] if text.startswith(command_prefix) else text
                
                # 只有当路径部分包含路径分隔符（\ 或 /）时才触发补全
                # 这样可以避免在输入 "E:" 时就触发补全，而是等待输入 "E:\" 才触发
                if '\\' not in path_part and '/' not in path_part:
                    return
                
                # 创建只包含路径部分的临时文档
                from prompt_toolkit.document import Document
                path_document = Document(path_part, len(path_part))
                
                # 使用路径补全器生成补全
                for completion in path_completer.get_completions(path_document, complete_event):
                    # 计算正确的 start_position：从当前光标位置向左偏移到路径部分的开始
                    # 注意：start_position 是负数，表示从当前光标位置向左的偏移量
                    # 我们只希望替换路径部分，而不是整个命令
                    # 当用户输入部分路径时，应该从路径部分的开始位置替换
                    start_position = -(document.cursor_position - len(command_prefix))
                    # 确保 start_position 是负数
                    start_position = min(start_position, 0)
                    
                    # 提取完整的补全文本
                    # 从 display 中提取完整路径，因为 display 通常包含完整的路径信息
                    if hasattr(completion.display, 'text'):
                        complete_text = completion.display.text
                    elif hasattr(completion.display, '__iter__'):
                        # 处理 FormattedText
                        complete_text = ''.join([part[1] for part in completion.display if isinstance(part, tuple)])
                    else:
                        complete_text = completion.text
                    
                    # 移除末尾的斜杠
                    complete_text = complete_text.rstrip('/').rstrip('\\')
                    
                    # 处理路径前缀：如果输入包含路径前缀（如C:\），确保补全结果包含完整路径
                    if '\\' in path_part or '/' in path_part:
                        # 找到最后一个路径分隔符的位置（无论是 \ 还是 /）
                        last_backslash = path_part.rfind('\\')
                        last_slash = path_part.rfind('/')
                        last_sep_pos = max(last_backslash, last_slash)
                        
                        if last_sep_pos > 0:
                            # 提取最后一个分隔符之前的部分作为前缀
                            prefix = path_part[:last_sep_pos]
                            # 使用原始分隔符
                            separator = path_part[last_sep_pos]
                            prefix += separator
                        elif last_sep_pos == 0:
                            # 分隔符在开头（如 \ 或 /）
                            prefix = path_part[0]
                        else:
                            prefix = ''
                        
                        # 组合完整路径
                        complete_text = prefix + complete_text
                    
                    # 创建新的 Completion 对象
                    yield Completion(
                        text=complete_text,
                        start_position=start_position,
                        display=completion.display,
                        display_meta=completion.display_meta,
                        style=completion.style,
                        selected_style=completion.selected_style
                    )
                return
        
        # 检查是否以空格结尾（表示正在输入子命令）
        ends_with_space = text.endswith(' ') or text.endswith('\t')
        
        if not words:
            # 空输入：显示所有根命令和独立命令
            for cmd in self.root_commands.keys():
                yield Completion(cmd, start_position=0)
            for cmd in self.standalone_commands:
                yield Completion(cmd, start_position=0)
        
        elif len(words) == 1 and not ends_with_space:
            # 输入一个词且不以空格结尾：可能是根命令或独立命令的一部分
            current_word = words[0].lower()
            
            # 检查根命令
            for cmd in self.root_commands.keys():
                if cmd.lower().startswith(current_word):
                    yield Completion(cmd, start_position=-len(words[-1]))
            
            # 检查独立命令
            for cmd in self.standalone_commands:
                if cmd.lower().startswith(current_word):
                    yield Completion(cmd, start_position=-len(words[-1]))
        
        elif len(words) == 1 and ends_with_space:
            # 输入一个词且以空格结尾：显示该根命令的子命令
            root_cmd = words[0]
            if root_cmd in self.root_commands:
                for subcmd in self.root_commands[root_cmd]:
                    yield Completion(subcmd, start_position=0)
        
        elif len(words) == 2:
            # 输入两个词：可能是根命令 + 子命令前缀
            root_cmd = words[0].lower()  # 大小写不敏感
            subcmd_prefix = words[1].lower()
            
            # 查找匹配的根命令（大小写不敏感）
            matched_root_cmd = None
            for cmd in self.root_commands:
                if cmd.lower() == root_cmd:
                    matched_root_cmd = cmd
                    break
            
            if matched_root_cmd:
                for subcmd in self.root_commands[matched_root_cmd]:
                    # 检查是否是完整匹配（完整匹配时不显示）
                    if subcmd.lower() == subcmd_prefix:
                        continue
                    # 大小写不敏感的前缀匹配
                    if subcmd.lower().startswith(subcmd_prefix):
                        yield Completion(subcmd, start_position=-len(words[-1]))


def interactive_mode():
    """交互式命令行模式"""
    console.print("[bold blue]重复文件查找工具[/bold blue]")
    console.print("[bold green]输入 'help' 查看可用命令，输入 'exit' 退出[/bold green]")
    
    # 创建补全器
    completer = TyperCompleter(app)
    
    # 创建会话
    session = PromptSession(
        "duplicate> ",
        completer=completer
    )
    
    while True:
        try:
            # 读取用户输入
            user_input = session.prompt()
            
            # 处理退出命令
            if user_input.strip().lower() == 'exit':
                console.print("[bold yellow]退出程序[/bold yellow]")
                break
            
            # 处理帮助命令
            user_input_lower = user_input.strip().lower()
            if user_input_lower == 'help':
                console.print("[bold blue]可用命令:[/bold blue]")
                console.print("  index    - 索引管理")
                console.print("  show     - 显示信息")
                console.print("  hash     - 哈希管理")
                console.print("  export   - 导出数据")
                console.print("  clean    - 清理工具")
                console.print("  config   - 配置管理")
                console.print("  db       - 数据库管理")
                console.print("  exit     - 退出程序")
                console.print("\n[dim]提示: 使用 'help <command>' 查看子命令帮助，如 'help clean'[/dim]")
                continue
            
            # 处理 help <command> 格式
            if user_input_lower.startswith('help '):
                command = user_input_lower[5:].strip()
                if command:
                    sys.argv = ['duplicate', command, '--help']
                    try:
                        app()
                    except SystemExit:
                        pass
                    continue
            
            # 处理空输入
            if not user_input.strip():
                continue
            
            # 执行命令
            sys.argv = ['duplicate'] + user_input.split()
            try:
                app()
            except SystemExit:
                # 忽略 Typer 的 SystemExit
                pass
            except Exception as e:
                console.print(f"[bold red]错误: {e}[/bold red]")
                
        except KeyboardInterrupt:
            # 处理 Ctrl+C
            console.print("\n[bold yellow]退出程序[/bold yellow]")
            break


@app.command()
def version():
    """显示版本信息"""
    console.print("[bold blue]重复文件查找工具 v1.0.0[/bold blue]")
    console.print("[green]一个用于查找和管理重复文件的命令行工具[/green]")


if __name__ == "__main__":
    # 检查是否在交互式模式下运行
    if len(sys.argv) == 1:
        interactive_mode()
    else:
        # 命令行模式
        app()
