#!/usr/bin/env python3
"""调试 Typer 命令结构"""

import typer
from commands import index, show, hash, export, clean, config, db

# 初始化 Typer 应用
app = typer.Typer()

# 注册命令
app.add_typer(index.app, name="index")
app.add_typer(show.app, name="show")
app.add_typer(hash.app, name="hash")
app.add_typer(export.app, name="export")
app.add_typer(clean.app, name="clean")
app.add_typer(config.app, name="config")
app.add_typer(db.app, name="db")

@app.command()
def version():
    """显示版本信息"""
    pass

# 调试 registered_commands
print("=== 调试 Typer 命令结构 ===")
print(f"app.registered_commands: {app.registered_commands}")
print(f"类型: {type(app.registered_commands)}")

# 尝试不同的方式获取命令
print("\n=== 尝试不同的属性 ===")

# 打印所有属性
try:
    print("=== 所有属性 ===")
    for attr in dir(app):
        if not attr.startswith('_'):
            try:
                value = getattr(app, attr)
                print(f"app.{attr}: {value}")
            except Exception as e:
                print(f"app.{attr}: 错误 - {e}")
except Exception as e:
    print(f"错误: {e}")

# 查看私有属性
try:
    print("\n=== 私有属性 ===")
    for attr in dir(app):
        if attr.startswith('_'):
            try:
                value = getattr(app, attr)
                print(f"app.{attr}: {value}")
            except Exception as e:
                pass
except Exception as e:
    print(f"错误: {e}")

# 尝试获取子命令
try:
    print("\n=== 子命令 ===")
    if hasattr(app, 'registered_groups'):
        for i, typer_info in enumerate(app.registered_groups):
            print(f"  组 {i} - 名称: {typer_info.name}")
            print(f"  类型: {type(typer_info)}")
            print(f"  属性: {typer_info.__dict__}")
            
            # 查看子命令
            if hasattr(typer_info, 'typer_instance'):
                typer_instance = typer_info.typer_instance
                print(f"  子命令: {typer_instance.registered_commands}")
                for j, subcommand_info in enumerate(typer_instance.registered_commands):
                    print(f"    子命令 {j}: {subcommand_info.name}")

except Exception as e:
    print(f"错误: {e}")
