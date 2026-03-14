import typer
from typing import Optional
from commands import index, show, export, config, db, clean
import inspect
from typer.models import ArgumentInfo, OptionInfo

app = typer.Typer()

# 注册子命令
app.add_typer(index.app, name="index", help="扫描与索引指令")
app.add_typer(show.app, name="show", help="显示数据指令")
app.add_typer(export.app, name="export", help="导出指令")
app.add_typer(config.app, name="config", help="配置指令")
app.add_typer(db.app, name="db", help="数据库指令")
app.add_typer(clean.app, name="clean", help="清理指令")

def get_command_options(callback):
    """从回调函数自动获取可选参数列表"""
    if not callback:
        return []
    
    sig = inspect.signature(callback)
    options = []
    
    for param_name, param in sig.parameters.items():
        default = param.default
        
        if default is inspect.Parameter.empty:
            continue
        
        if isinstance(default, OptionInfo):
            if hasattr(default, 'names') and default.names:
                options.extend(default.names)
            else:
                options.append(f'--{param_name.replace("_", "-")}')
        elif isinstance(default, ArgumentInfo):
            pass
        elif isinstance(default, bool) and default is False:
            options.append(f'--{param_name.replace("_", "-")}')
        elif default is None or isinstance(default, (str, int, float, bool)):
            options.append(f'--{param_name.replace("_", "-")}')
    
    return options

def build_command_metadata():
    """自动构建命令元数据，包括子命令和参数"""
    subcommands_map = {}
    command_options = {}
    
    for group in app.registered_groups:
        group_name = group.name
        typer_instance = group.typer_instance
        
        if hasattr(typer_instance, 'registered_commands'):
            subcommands = []
            subcmd_options = {}
            
            for cmd_info in typer_instance.registered_commands:
                cmd_name = cmd_info.name or cmd_info.callback.__name__
                subcommands.append(cmd_name)
                options = get_command_options(cmd_info.callback)
                subcmd_options[cmd_name] = options
            
            subcommands_map[group_name] = subcommands
            command_options[group_name] = subcmd_options
    
    for cmd_info in app.registered_commands:
        cmd_name = cmd_info.name or cmd_info.callback.__name__
        command_options[cmd_name] = get_command_options(cmd_info.callback)
    
    return subcommands_map, command_options

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

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        # 没有命令行参数，启动交互式模式
        from prompt_toolkit import PromptSession
        from prompt_toolkit.completion import Completer, Completion
        from prompt_toolkit.styles import Style
        from prompt_toolkit.history import FileHistory
        import io
        
        # 自动构建命令元数据
        subcommands_map, command_options = build_command_metadata()
        
        # 定义命令补全
        commands = list(subcommands_map.keys()) + ['help', 'version', 'exit']
        
        class CustomCompleter(Completer):
            """自定义补全器，根据已输入的命令动态提供补全"""
            
            def get_completions(self, document, complete_event):
                text = document.text_before_cursor
                words = text.split()
                
                # 获取当前正在输入的词（可能不完整）
                current_word = ''
                if text and not text.endswith(' '):
                    current_word = words[-1] if words else ''
                
                if len(words) == 0 or (len(words) == 1 and not text.endswith(' ')):
                    # 没有输入或正在输入第一个词，提示一级命令
                    search_word = words[0] if words else ''
                    for cmd in commands:
                        if cmd.startswith(search_word):
                            yield Completion(cmd, start_position=-len(search_word))
                
                elif len(words) == 1 and text.endswith(' '):
                    # 输入了一个完整的词，后面有空格
                    first_word = words[0]
                    
                    if first_word == 'help':
                        # help 后面提示所有一级命令
                        for cmd in commands:
                            if cmd not in ('help', 'exit'):
                                yield Completion(cmd, start_position=0)
                    elif first_word in subcommands_map:
                        # 有子命令的一级命令，提示二级命令
                        for subcmd in subcommands_map[first_word]:
                            yield Completion(subcmd, start_position=0)
                    elif first_word in command_options:
                        # 没有子命令的一级命令，提示参数
                        options = command_options.get(first_word, [])
                        for opt in options:
                            yield Completion(opt, start_position=0)
                
                elif len(words) >= 2:
                    # 输入了两个或更多词
                    first_word = words[0]
                    
                    # 处理 help 命令
                    if first_word == 'help':
                        if len(words) == 2 and not text.endswith(' '):
                            # 正在输入第二个词
                            for cmd in commands:
                                if cmd not in ('help', 'exit') and cmd.startswith(words[1]):
                                    yield Completion(cmd, start_position=-len(words[1]))
                        return
                    
                    # 处理有子命令的一级命令
                    if first_word in subcommands_map:
                        second_word = words[1]
                        current_subcmds = subcommands_map[first_word]
                        
                        if len(words) == 2 and not text.endswith(' '):
                            # 正在输入第二个词（二级命令）
                            for subcmd in current_subcmds:
                                if subcmd.startswith(second_word):
                                    yield Completion(subcmd, start_position=-len(second_word))
                        
                        elif (len(words) == 2 and text.endswith(' ')) or (len(words) == 3 and not text.endswith(' ')):
                            # 二级命令已完整，提示参数
                            # 或者正在输入参数
                            if second_word in current_subcmds:
                                options = self._get_options(first_word, second_word)
                                if len(words) == 3 and not text.endswith(' '):
                                    # 正在输入参数，进行前缀匹配
                                    prefix = words[2]
                                    for opt in options:
                                        if opt.startswith(prefix):
                                            yield Completion(opt, start_position=-len(prefix))
                                else:
                                    # 提示所有参数
                                    for opt in options:
                                        yield Completion(opt, start_position=0)
                        
                        elif len(words) >= 3 and text.endswith(' '):
                            # 已经输入了参数，继续提示剩余参数
                            if second_word in current_subcmds:
                                options = self._get_options(first_word, second_word)
                                for opt in options:
                                    yield Completion(opt, start_position=0)
                    
                    # 处理没有子命令的一级命令
                    elif first_word in command_options and first_word not in subcommands_map:
                        options = command_options.get(first_word, [])
                        if len(words) >= 2 and not text.endswith(' '):
                            # 正在输入参数
                            prefix = words[-1]
                            for opt in options:
                                if opt.startswith(prefix):
                                    yield Completion(opt, start_position=-len(prefix))
                        elif text.endswith(' '):
                            # 提示所有参数
                            for opt in options:
                                yield Completion(opt, start_position=0)
            
            def _get_options(self, primary_cmd, subcmd):
                """获取命令的参数列表"""
                if primary_cmd in command_options:
                    cmd_opts = command_options[primary_cmd]
                    if isinstance(cmd_opts, dict) and subcmd in cmd_opts:
                        return cmd_opts[subcmd]
                return []
        
        # 定义样式
        style = Style.from_dict({
            'prompt': '#ff0066 bold',
            'command': '#00ff00',
            'arg': '#00ffff',
        })
        
        # 交互式命令行界面
        session = PromptSession(
            history=FileHistory('.duplicate_finder_history'),
            style=style
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
        
        while True:
            try:
                # 获取用户输入
                command = session.prompt('> ', completer=CustomCompleter())
                command = command.strip()
                
                if not command:
                    continue
                
                if command in ('exit', 'quit', 'q'):
                    print("感谢使用重复文件分析工具！")
                    break
                
                # 执行命令
                # 特殊处理 help 命令，避免递归调用
                if command == 'help':
                    # 直接显示帮助信息
                    print("重复文件分析工具")
                    print("=" * 60)
                    print("可用命令:")
                    print("=" * 60)
                    print()
                    
                    # 直接在当前进程中执行help命令
                    stdout, stderr = execute_command(['help'])
                    if stdout:
                        # 跳过前几行，只显示命令列表部分
                        lines = fix_help_text(stdout).split('\n')
                        start_printing = False
                        for line in lines:
                            if '可用命令:' in line:
                                start_printing = True
                            elif start_printing:
                                print(line)
                elif command.startswith('help '):
                    # 处理 help <命令> 格式
                    cmd_parts = command.split()
                    if len(cmd_parts) > 1:
                        cmd = cmd_parts[1]
                        stdout, stderr = execute_command([cmd, '--help'])
                        if stdout:
                            print(fix_help_text(stdout))
                        if stderr:
                            print(fix_help_text(stderr), file=sys.stderr)
                    else:
                        # 与上面相同的帮助信息
                        print("重复文件分析工具")
                        print("=" * 60)
                        print("可用命令:")
                        print("=" * 60)
                        print()
                        
                        stdout, stderr = execute_command(['help'])
                        if stdout:
                            # 跳过前几行，只显示命令列表部分
                            lines = fix_help_text(stdout).split('\n')
                            start_printing = False
                            for line in lines:
                                if '可用命令:' in line:
                                    start_printing = True
                                elif start_printing:
                                    print(line)
                else:
                    # 执行其他命令
                    stdout, stderr = execute_command(command.split())
                    
                    # 显示输出
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
