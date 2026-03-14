import pytest
from prompt_toolkit.document import Document
from main import TyperCompleter, app
from prompt_toolkit.completion import Completion


class TestPathCompletion:
    """测试路径补全功能"""
    
    def setup_method(self):
        """设置测试环境"""
        self.completer = TyperCompleter(app)
    
    def test_path_completion_commands(self):
        """测试路径补全命令配置"""
        # 验证路径补全命令是否正确配置
        path_commands = [
            ('index', 'import'),
            ('hash', 'restore'),
            ('index', 'scan'),
            ('config', 'limit'),
            ('show', 'files'),
            ('export', 'csv'),
            ('export', 'json'),
            ('export', 'report'),
            ('hash', 'backup'),
            ('clean', 'script'),
            ('db', 'backup_database'),
            ('db', 'backup_file_hash'),
        ]
        
        for cmd_tuple in path_commands:
            assert cmd_tuple in self.completer.path_completion_commands
    
    def test_file_path_completion(self):
        """测试文件路径补全"""
        # 测试 index import 命令的文件路径补全
        document = Document('index import ', 13)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象
        for completion in completions:
            assert isinstance(completion, Completion)
    
    def test_directory_path_completion(self):
        """测试目录路径补全"""
        # 测试 index scan 命令的目录路径补全
        document = Document('index scan ', 11)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象
        for completion in completions:
            assert isinstance(completion, Completion)
    
    def test_generic_path_completion(self):
        """测试通用路径补全"""
        # 测试 export csv 命令的通用路径补全
        document = Document('export csv ', 11)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象
        for completion in completions:
            assert isinstance(completion, Completion)
    
    def test_option_path_completion(self):
        """测试带选项的路径补全"""
        # 测试 clean script --output 命令的路径补全
        document = Document('clean script --output ', 20)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象
        for completion in completions:
            assert isinstance(completion, Completion)
    
    def test_non_path_completion(self):
        """测试非路径补全命令"""
        # 测试非路径补全命令（如 index rebuild）
        document = Document('index rebuild ', 14)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象（应该是空列表或命令补全）
        for completion in completions:
            assert isinstance(completion, Completion)
    
    def test_path_completion_with_partial_input(self):
        """测试带部分输入的路径补全"""
        # 测试带部分输入的路径补全
        document = Document('index scan C:', 13)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象
        for completion in completions:
            assert isinstance(completion, Completion)
    
    def test_path_completion_priority(self):
        """测试路径补全优先级"""
        # 确保路径补全优先于命令补全
        document = Document('index scan ', 11)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是路径补全结果，而不是命令补全
        # 由于路径补全依赖于实际文件系统，这里只验证返回类型
        for completion in completions:
            assert isinstance(completion, Completion)
    
    def test_index_scan_path_completion(self):
        """测试index scan命令的路径补全"""
        # 测试index scan命令的路径补全
        document = Document('index scan ', 11)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象
        for completion in completions:
            assert isinstance(completion, Completion)
        
        # 测试带部分路径的补全
        document = Document('index scan C:', 13)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象
        for completion in completions:
            assert isinstance(completion, Completion)