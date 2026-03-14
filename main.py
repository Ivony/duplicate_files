import typer
from typing import Optional
from commands import index, show, export, config, db, clean, hash as hash_cmd

app = typer.Typer()

# 注册子命令
app.add_typer(index.app, name="index", help="扫描与索引指令")
app.add_typer(show.app, name="show", help="显示数据指令")
app.add_typer(hash_cmd.app, name="hash", help="哈希计算指令")
app.add_typer(export.app, name="export", help="导出指令")
app.add_typer(config.app, name="config", help="配置指令")
app.add_typer(db.app, name="db", help="数据库指令")
app.add_typer(clean.app, name="clean", help="清理指令")

@app.command()
def version():
    """显示版本信息"""
    typer.echo("重复文件分析工具 v2.0")
    typer.echo("重构版本 - 支持新的指令系统和模块化架构")

@app.command()
def help(command: Optional[str] = None):
    """显示帮助信息"""
    if command:
        # 显示特定命令的帮助
        # 这里可以添加特定命令的帮助信息
        typer.echo(f"命令: {command}")
        # 执行命令的帮助
        import subprocess
        import sys
        result = subprocess.run([sys.executable, 'main.py', command, '--help'], 
                              capture_output=True, text=True)
        if result.stdout:
            typer.echo(result.stdout)
        if result.stderr:
            typer.echo(result.stderr, file=sys.stderr)
    else:
        # 显示所有命令的帮助
        typer.echo("重复文件分析工具")
        typer.echo("=" * 60)
        typer.echo("可用命令:")
        typer.echo("=" * 60)
        typer.echo("")
        
        # 手动列出所有命令，确保能显示所有命令
        commands = {
            'version': '显示版本信息',
            'index': '扫描与索引指令',
            'show': '显示数据指令',
            'export': '导出指令',
            'config': '配置指令',
            'db': '数据库指令',
            'clean': '清理指令',
            'exit': '退出程序',
            'quit': '退出程序',
            'q': '退出程序'
        }
        
        for cmd_name, cmd_help in commands.items():
            typer.echo(f"  {cmd_name:<10} - {cmd_help}")
        
        typer.echo("")
        typer.echo("使用 'help <命令>' 查看特定命令的详细帮助")
        typer.echo("=" * 60)

from prompt_toolkit.completion import Completer, Completion


class TyperCompleter(Completer):
    """基于Typer应用元数据的上下文感知补全器"""
    
    def __init__(self, app):
        self.app = app
        # 从Typer应用提取命令结构
        self.root_commands = {}  # 根命令 -> 子命令列表
        self.standalone_commands = []  # 独立命令（如version, help）
        
        # 提取所有命令结构
        self._extract_commands()
    
    def _extract_commands(self):
        """从Typer应用提取命令元数据"""
        # 提取分组命令（如 index, show, hash等）
        for group_info in self.app.registered_groups:
            group_name = group_info.name
            sub_app = group_info.typer_instance
            
            subcommands = []
            for cmd_info in sub_app.registered_commands:
                if cmd_info.callback:
                    cmd_name = cmd_info.name or getattr(cmd_info.callback, '__name__', 'unknown')
                    subcommands.append(cmd_name)
            
            self.root_commands[group_name] = subcommands
        
        # 提取独立命令（如version, help）
        for cmd_info in self.app.registered_commands:
            if cmd_info.callback:
                cmd_name = cmd_info.name or getattr(cmd_info.callback, '__name__', 'unknown')
                self.standalone_commands.append(cmd_name)
    
    def get_completions(self, document, complete_event):
        """根据当前输入上下文提供补全建议"""
        
        text = document.text_before_cursor
        stripped_text = text.strip()
        words = stripped_text.split()
        
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
            
            # 匹配根命令
            for cmd in self.root_commands.keys():
                if cmd.lower().startswith(current_word):
                    yield Completion(cmd, start_position=-len(words[0]))
            
            # 匹配独立命令
            for cmd in self.standalone_commands:
                if cmd.lower().startswith(current_word):
                    yield Completion(cmd, start_position=-len(words[0]))
        
        elif len(words) == 1 and ends_with_space:
            # 输入一个词且以空格结尾：正在输入该命令的子命令
            root_cmd = words[0].lower()
            
            # 检查是否是已知的根命令
            matched_root = None
            for cmd in self.root_commands.keys():
                if cmd.lower() == root_cmd:
                    matched_root = cmd
                    break
            
            if matched_root:
                # 显示该根命令下的所有子命令
                subcommands = self.root_commands[matched_root]
                for subcmd in subcommands:
                    yield Completion(subcmd, start_position=0)
        
        else:
            # 输入多个词：第一个词是根命令，后续是子命令
            root_cmd = words[0].lower()
            current_word = words[-1].lower()
            
            # 检查是否是已知的根命令
            matched_root = None
            for cmd in self.root_commands.keys():
                if cmd.lower() == root_cmd:
                    matched_root = cmd
                    break
            
            if matched_root:
                # 提供该根命令下的子命令补全
                subcommands = self.root_commands[matched_root]
                for subcmd in subcommands:
                    # 只显示前缀匹配且不是完全匹配的子命令
                    if subcmd.lower().startswith(current_word) and subcmd.lower() != current_word:
                        yield Completion(subcmd, start_position=-len(words[-1]))
            else:
                # 不是已知的根命令，回退到根命令补全
                for cmd in self.root_commands.keys():
                    if cmd.lower().startswith(root_cmd):
                        yield Completion(cmd, start_position=-len(words[0]))


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        # 没有命令行参数，启动交互式模式
        from prompt_toolkit import PromptSession
        from prompt_toolkit.styles import Style
        from prompt_toolkit.history import FileHistory
        import io
        
        # 创建上下文感知的补全器
        completer = TyperCompleter(app)
        
        # 定义样式
        style = Style.from_dict({
            'prompt': '#ff0066 bold',
            'command': '#00ff00',
            'arg': '#00ffff',
        })
        
        # 交互式命令行界面
        session = PromptSession(
            history=FileHistory('.duplicate_finder_history'),
            style=style,
            completer=completer
        )
        
        print("重复文件分析工具")
        print("=" * 60)
        print("数据库路径: file_index.db")
        print("=" * 60)
        print("输入 help 查看帮助信息")
        print()
        
        def execute_command(command_parts):
            """直接在当前进程中执行命令，避免subprocess"""
            import sys
            from contextlib import redirect_stdout, redirect_stderr
            
            # 保存原始的sys.argv
            original_argv = sys.argv.copy()
            
            try:
                # 重定向输出
                stdout_buffer = io.StringIO()
                stderr_buffer = io.StringIO()
                
                with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                    # 设置新的argv，让Typer认为是直接调用的
                    # 使用空字符串作为程序名，让帮助信息更简洁
                    sys.argv = [''] + command_parts
                    try:
                        app()
                    except SystemExit:
                        # Typer会调用sys.exit，我们捕获它
                        pass
                
                # 获取输出
                stdout_output = stdout_buffer.getvalue()
                stderr_output = stderr_buffer.getvalue()
                
                return stdout_output, stderr_output
            finally:
                # 恢复原始的sys.argv
                sys.argv = original_argv
        
        def fix_help_text(text):
            """修复帮助文本，移除 'main.py ' 前缀"""
            if not text:
                return text
            # 替换所有的 'main.py ' 为 ''
            text = text.replace('Usage: main.py ', 'Usage: ')
            text = text.replace('Usage:  ', 'Usage: ')
            text = text.replace("Try 'main.py ", "Try '")
            text = text.replace("Try ' --help", "Try 'help'")
            return text
        
        def extract_typer_metadata():
            """从Typer应用中提取元数据"""
            metadata = {}
            
            for group_info in app.registered_groups:
                group_name = group_info.name
                group_help = group_info.help or ''
                
                metadata[group_name] = {
                    'name': group_name,
                    'help': group_help,
                    'subcommands': {}
                }
                
                sub_app = group_info.typer_instance
                for cmd_info in sub_app.registered_commands:
                    if cmd_info.callback:
                        cmd_name = cmd_info.name or getattr(cmd_info.callback, '__name__', 'unknown')
                        cmd_doc = cmd_info.callback.__doc__ or ''
                        
                        metadata[group_name]['subcommands'][cmd_name] = {
                            'name': cmd_name,
                            'help': cmd_doc.strip()
                        }
            
            return metadata
        
        def show_interactive_help(command_name=None):
            """显示交互式模式的帮助信息（从Typer元数据动态生成）"""
            metadata = extract_typer_metadata()
            
            if command_name is None:
                print("\n重复文件分析工具 - 交互式帮助")
                print("=" * 80)
                print("\n可用命令:")
                print("-" * 80)
                
                for group_name, group_data in sorted(metadata.items()):
                    print(f"\n  {group_name:<12} - {group_data['help']}")
                    for cmd_name, cmd_data in sorted(group_data['subcommands'].items()):
                        print(f"    {cmd_name}")
                
                for cmd_info in app.registered_commands:
                    if cmd_info.callback:
                        cmd_name = cmd_info.name or getattr(cmd_info.callback, '__name__', 'unknown')
                        cmd_doc = cmd_info.callback.__doc__ or ''
                        print(f"\n  {cmd_name:<12} - {cmd_doc.strip()}")
                
                print("\n" + "-" * 80)
                print("使用 'help <命令>' 查看特定命令的详细帮助")
                print("使用 Tab 键自动补全命令和参数")
                print("使用 ↑ ↓ 键浏览历史命令")
                print("=" * 80 + "\n")
            else:
                command_name = command_name.lower()
                
                if command_name in metadata:
                    group_data = metadata[command_name]
                    print(f"\n命令: {command_name}")
                    print("=" * 80)
                    print(f"描述: {group_data['help']}")
                    print(f"用法: {command_name} <子命令> [参数]")
                    print("\n子命令:")
                    print("-" * 80)
                    for cmd_name, cmd_data in sorted(group_data['subcommands'].items()):
                        print(f"  {cmd_name:<30} - {cmd_data['help']}")
                    
                    examples = []
                    for cmd_name in sorted(group_data['subcommands'].keys()):
                        examples.append(f"{command_name} {cmd_name}")
                    
                    print("\n示例:")
                    print("-" * 80)
                    for example in examples[:5]:
                        print(f"  {example}")
                    if len(examples) > 5:
                        print(f"  ... 还有 {len(examples) - 5} 个子命令")
                    print("=" * 80 + "\n")
                else:
                    found = False
                    for cmd_info in app.registered_commands:
                        if cmd_info.callback:
                            cmd_name = cmd_info.name or getattr(cmd_info.callback, '__name__', 'unknown')
                            if cmd_name == command_name:
                                found = True
                                cmd_doc = cmd_info.callback.__doc__ or ''
                                print(f"\n命令: {command_name}")
                                print("=" * 80)
                                print(f"描述: {cmd_doc.strip()}")
                                print(f"用法: {command_name}")
                                print("=" * 80 + "\n")
                                break
                    
                    if not found:
                        print(f"\n错误: 未找到命令 '{command_name}'")
                        print("使用 'help' 查看所有可用命令\n")
        
        while True:
            try:
                command = session.prompt('> ')
                command = command.strip()
                
                if not command:
                    continue
                
                if command in ('exit', 'quit', 'q'):
                    print("感谢使用重复文件分析工具！")
                    break
                
                if command == 'help':
                    show_interactive_help()
                elif command.startswith('help '):
                    cmd_parts = command.split(maxsplit=1)
                    if len(cmd_parts) > 1:
                        show_interactive_help(cmd_parts[1])
                    else:
                        show_interactive_help()
                else:
                    stdout, stderr = execute_command(command.split())
                    
                    if stdout:
                        print(fix_help_text(stdout))
                    if stderr:
                        print(fix_help_text(stderr), file=sys.stderr)
                    
            except KeyboardInterrupt:
                print("\n感谢使用重复文件分析工具！")
                break
            except Exception as e:
                print(f"错误: {e}")
    else:
        # 有命令行参数，执行命令行模式
        app()
