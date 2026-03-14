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

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        # 没有命令行参数，启动交互式模式
        from prompt_toolkit import PromptSession
        from prompt_toolkit.styles import Style
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.contrib.typer import TyperCompleter
        import io
        
        # 创建 Typer 补全器
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
        
        while True:
            try:
                # 获取用户输入
                command = session.prompt('> ')
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
