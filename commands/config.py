import typer
import re
import json
import os
import sqlite3
from commands.db_config import get_db_path

class ConfigManager:
    def __init__(self, config_path='config.json', db_path=None):
        self.config_path = config_path
        self.db_path = db_path or get_db_path()
        # 先从JSON文件加载配置
        self.config = self._load_config_from_json()
        # 然后初始化数据库配置表（会同步JSON配置到数据库）
        self._init_db_config()
    
    def _get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path, timeout=60.0, isolation_level='IMMEDIATE')
    
    def _init_db_config(self):
        """初始化数据库配置表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 创建配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # 将JSON配置同步到数据库
        self._sync_config_to_db()
    
    def _sync_config_to_db(self):
        """将JSON配置同步到数据库"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 同步limit_path
        limit_path = self.config.get('limit_path')
        cursor.execute('''
            INSERT OR REPLACE INTO config (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', ('limit_path', json.dumps(limit_path)))
        
        # 同步excluded_patterns
        excluded_patterns = self.config.get('excluded_patterns', [])
        cursor.execute('''
            INSERT OR REPLACE INTO config (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', ('excluded_patterns', json.dumps(excluded_patterns)))
        
        conn.commit()
        conn.close()
    
    def _load_config_from_db(self):
        """从数据库加载配置"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        config = self.get_default_config()
        
        try:
            cursor.execute('SELECT key, value FROM config')
            rows = cursor.fetchall()
            
            for key, value in rows:
                if key == 'limit_path':
                    config['limit_path'] = json.loads(value)
                elif key == 'excluded_patterns':
                    config['excluded_patterns'] = json.loads(value)
        except Exception as e:
            print(f"从数据库加载配置失败: {e}")
        
        conn.close()
        return config
    
    def _save_config_to_db(self):
        """保存配置到数据库"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 保存limit_path
            limit_path = self.config.get('limit_path')
            cursor.execute('''
                INSERT OR REPLACE INTO config (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', ('limit_path', json.dumps(limit_path)))
            
            # 保存excluded_patterns
            excluded_patterns = self.config.get('excluded_patterns', [])
            cursor.execute('''
                INSERT OR REPLACE INTO config (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', ('excluded_patterns', json.dumps(excluded_patterns)))
            
            conn.commit()
        except Exception as e:
            print(f"保存配置到数据库失败: {e}")
        finally:
            conn.close()
    
    def _load_config_from_json(self):
        """从JSON文件加载配置"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return self.get_default_config()
        else:
            return self.get_default_config()
    
    def load_config(self):
        """加载配置文件（优先从数据库加载）"""
        # 首先尝试从数据库加载
        if os.path.exists(self.db_path):
            try:
                db_config = self._load_config_from_db()
                # 如果数据库中有配置，使用数据库的配置
                if db_config != self.get_default_config():
                    return db_config
            except Exception as e:
                print(f"从数据库加载配置失败，尝试从JSON文件加载: {e}")
        
        # 从JSON文件加载
        return self._load_config_from_json()
    
    def get_default_config(self):
        """获取默认配置"""
        return {
            'limit_path': None,
            'excluded_patterns': []
        }
    
    def save_config(self):
        """保存配置文件（同时保存到JSON和数据库）"""
        # 保存到JSON文件
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            print(f"配置已保存到: {self.config_path}")
        except Exception as e:
            print(f"保存配置文件失败: {e}")
        
        # 保存到数据库
        self._save_config_to_db()
    
    def set_limit(self, path):
        """设置检索范围限制"""
        if not os.path.exists(path) or not os.path.isdir(path):
            print(f"错误: 路径不存在或不是目录: {path}")
            return False
        
        self.config['limit_path'] = path
        self.save_config()
        print(f"已设置检索范围限制: {path}")
        return True
    
    def clear_limit(self):
        """解除检索范围限制"""
        self.config['limit_path'] = None
        self.save_config()
        print("已解除检索范围限制")
    
    def add_exclude_pattern(self, pattern):
        """添加排除模式"""
        if pattern not in self.config['excluded_patterns']:
            self.config['excluded_patterns'].append(pattern)
            self.save_config()
            print(f"已添加排除模式: {pattern}")
        else:
            print(f"排除模式已存在: {pattern}")
    
    def list_exclude_patterns(self):
        """查看排除模式"""
        print("\n当前排除模式:")
        if not self.config['excluded_patterns']:
            print("  没有设置排除模式")
        else:
            for i, pattern in enumerate(self.config['excluded_patterns'], 1):
                print(f"  {i}. {pattern}")
    
    def remove_exclude_pattern(self, pattern):
        """移除排除模式"""
        if pattern in self.config['excluded_patterns']:
            self.config['excluded_patterns'].remove(pattern)
            self.save_config()
            print(f"已移除排除模式: {pattern}")
        else:
            print(f"排除模式不存在: {pattern}")
    
    def get_limit_path(self):
        """获取当前限制路径"""
        return self.config.get('limit_path')
    
    def get_excluded_patterns(self):
        """获取排除模式列表"""
        return self.config.get('excluded_patterns', [])
    
    def is_path_excluded(self, file_path):
        """检查路径是否被排除"""
        for pattern in self.get_excluded_patterns():
            try:
                if re.match(pattern, file_path):
                    return True
            except re.error:
                print(f"无效的正则表达式: {pattern}")
        return False

app = typer.Typer()
config_manager = ConfigManager()

@app.command()
def limit(
    path: str = typer.Argument(None, help="设置检索范围限制，使用 clear 清除限制")
):
    """设置检索范围限制"""
    if path == "clear":
        config_manager.clear_limit()
        typer.echo("已解除检索范围限制")
    elif path:
        if config_manager.set_limit(path):
            typer.echo(f"已设置检索范围限制: {path}")
        else:
            typer.echo(f"设置检索范围限制失败: {path}")
    else:
        typer.echo("错误: 请指定路径或使用 clear 清除限制")

@app.command()
def exclude(
    action: str = typer.Argument(..., help="操作: add, list, remove"),
    pattern: str = typer.Argument(None, help="排除模式")
):
    """路径排除模式管理"""
    if action == "add":
        if pattern:
            config_manager.add_exclude_pattern(pattern)
        else:
            typer.echo("错误: 请指定排除模式")
    elif action == "list":
        config_manager.list_exclude_patterns()
    elif action == "remove":
        if pattern:
            config_manager.remove_exclude_pattern(pattern)
        else:
            typer.echo("错误: 请指定排除模式")
    else:
        typer.echo(f"错误: 未知的操作: {action}")
