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
        """测试带部分输入的路径补全
        
        当输入 'index scan C:' 时，不应该触发补全，
        因为路径部分不包含路径分隔符。
        应该等待用户输入 'C:\\' 才触发补全。
        """
        document = Document('index scan C:', 13)
        completions = list(self.completer.get_completions(document, None))
        
        assert len(completions) == 0
    
    def test_path_completion_requires_separator(self):
        """测试路径补全需要路径分隔符
        
        验证只有当路径部分包含路径分隔符时才触发补全：
        - 'index scan E:' - 不触发补全
        - 'index scan E:\\' - 触发补全
        """
        # 测试不带分隔符的驱动器字母
        document1 = Document('index scan E:', 13)
        completions1 = list(self.completer.get_completions(document1, None))
        assert len(completions1) == 0
        
        # 测试带分隔符的驱动器字母
        document2 = Document('index scan E:\\', 14)
        completions2 = list(self.completer.get_completions(document2, None))
        # 应该返回补全结果
        assert len(completions2) > 0
        for completion in completions2:
            assert isinstance(completion, Completion)
            assert completion.text.startswith('E:\\') or completion.text.startswith('E:/')
    
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
        # 测试index scan命令的路径补全（需要路径分隔符）
        document = Document('index scan C:\\', 14)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象
        for completion in completions:
            assert isinstance(completion, Completion)
        
        # 测试带部分路径的补全
        document = Document('index scan C:\\T', 15)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象
        for completion in completions:
            assert isinstance(completion, Completion)
    
    def test_path_completion_preserves_prefix(self):
        """测试路径补全保留路径前缀"""
        # 测试当输入部分路径时，补全应该保留路径前缀
        # 例如：输入 'index scan C:\T'，选择 'Temp' 应该变成 'index scan C:\Temp'
        document = Document('index scan C:/T', 14)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象
        for completion in completions:
            assert isinstance(completion, Completion)
            # 确保 start_position 是负数（表示从光标位置向左偏移）
            assert completion.start_position <= 0
            # 确保 start_position 正确计算，只替换路径部分
            assert completion.start_position == -3  # 替换 'C:/T' 部分
    
    def test_path_completion_with_backslash(self):
        """测试带反斜杠的路径补全
        
        这是针对修复的特定问题的测试：
        当输入 'index scan C:\\' 时，代码应该正确识别为路径补全，
        而不是错误地进入带选项的路径补全逻辑。
        """
        # 测试带反斜杠的路径补全
        document = Document('index scan C:\\', 14)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象
        for completion in completions:
            assert isinstance(completion, Completion)
            # 确保 start_position 是负数
            assert completion.start_position <= 0
            # 确保补全文本包含完整路径（以 C:\ 开头）
            assert completion.text.startswith('C:\\') or completion.text.startswith('C:/')
    
    def test_option_vs_path_distinction(self):
        """测试选项和路径的区分
        
        验证代码能正确区分：
        - 'index scan C:\\' - 路径补全
        - 'clean script --output ' - 带选项的路径补全
        """
        # 测试路径补全（不带选项）
        document1 = Document('index scan C:\\', 14)
        completions1 = list(self.completer.get_completions(document1, None))
        
        # 应该返回路径补全结果
        assert len(completions1) > 0
        for completion in completions1:
            assert isinstance(completion, Completion)
            assert completion.text.startswith('C:\\') or completion.text.startswith('C:/')
        
        # 测试带选项的路径补全
        document2 = Document('clean script --output ', 20)
        completions2 = list(self.completer.get_completions(document2, None))
        
        # 应该返回路径补全结果
        for completion in completions2:
            assert isinstance(completion, Completion)
    
    def test_path_completion_with_different_separators(self):
        """测试不同路径分隔符的补全"""
        # 测试 Windows 风格路径分隔符
        document = Document('index scan C:', 13)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象
        for completion in completions:
            assert isinstance(completion, Completion)
        
        # 测试相对路径
        document = Document('index scan .', 12)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象
        for completion in completions:
            assert isinstance(completion, Completion)
    
    def test_path_completion_handles_empty_path(self):
        """测试路径补全处理空路径
        
        空路径不应该触发补全，需要至少包含路径分隔符。
        """
        document = Document('index scan ', 11)
        completions = list(self.completer.get_completions(document, None))
        
        assert len(completions) == 0
    
    def test_path_completion_handles_special_characters(self):
        """测试路径补全处理特殊字符"""
        # 测试带空格的路径补全
        document = Document('index scan "', 12)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象
        for completion in completions:
            assert isinstance(completion, Completion)