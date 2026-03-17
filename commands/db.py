import typer
from core.database import DatabaseManager

app = typer.Typer()


@app.command()
def check():
    """检查数据库结构和数据"""
    db_manager = DatabaseManager()
    db_manager.check_database()


@app.command()
def optimize():
    """优化数据库性能"""
    db_manager = DatabaseManager()
    db_manager.optimize_database()


@app.command()
def init(
    force: bool = False
):
    """重建数据库结构，--force 强制重建，不询问"""
    db_manager = DatabaseManager()
    db_manager.init_database(force)
