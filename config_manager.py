import re
import json
import os

class ConfigManager:
    def __init__(self, config_path='config.json'):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return self.get_default_config()
        else:
            return self.get_default_config()
    
    def get_default_config(self):
        """获取默认配置"""
        return {
            'limit_path': None,
            'excluded_patterns': []
        }
    
    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            print(f"配置已保存到: {self.config_path}")
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
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

if __name__ == '__main__':
    import sys
    
    manager = ConfigManager()
    
    if len(sys.argv) < 2:
        print("用法: python config_manager.py <command> [args]")
        print("\n可用命令:")
        print("  limit <path>         - 设置检索范围限制")
        print("  limit clear           - 解除检索范围限制")
        print("  exclude add <pattern>  - 添加路径排除模式")
        print("  exclude list          - 查看当前排除模式")
        print("  exclude remove <pattern> - 移除路径排除模式")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'limit':
        if len(sys.argv) < 3:
            print("错误: 请指定路径或使用clear清除限制")
            sys.exit(1)
        
        if sys.argv[2] == 'clear':
            manager.clear_limit()
        else:
            manager.set_limit(sys.argv[2])
    elif command == 'exclude':
        if len(sys.argv) < 3:
            print("错误: 请指定子命令（add/list/remove）")
            sys.exit(1)
        
        subcommand = sys.argv[2]
        
        if subcommand == 'add':
            if len(sys.argv) < 4:
                print("错误: 请指定排除模式")
                sys.exit(1)
            manager.add_exclude_pattern(sys.argv[3])
        elif subcommand == 'list':
            manager.list_exclude_patterns()
        elif subcommand == 'remove':
            if len(sys.argv) < 4:
                print("错误: 请指定排除模式")
                sys.exit(1)
            manager.remove_exclude_pattern(sys.argv[3])
        else:
            print(f"未知的子命令: {subcommand}")
            sys.exit(1)
    else:
        print(f"未知命令: {command}")
        sys.exit(1)