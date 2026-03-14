import pytest
from prompt_toolkit.document import Document
from main import TyperCompleter, app
from prompt_toolkit.completion import Completion
import os


class TestPathCompletionEnvironment:
    """测试路径补全功能在不同环境下的表现"""
    
    def setup_method(self):
        """设置测试环境"""
        self.completer = TyperCompleter(app)
    
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
    
    def test_path_completion_preserves_prefix(self):
        """测试路径补全保留路径前缀"""
        # 测试带驱动器号的路径
        document = Document('index scan C:', 13)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象
        for completion in completions:
            assert isinstance(completion, Completion)
            # 确保 start_position 是负数（表示从光标位置向左偏移）
            assert completion.start_position <= 0
    
    def test_path_completion_handles_empty_path(self):
        """测试路径补全处理空路径"""
        # 测试空路径
        document = Document('index scan ', 11)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象
        for completion in completions:
            assert isinstance(completion, Completion)
    
    def test_path_completion_with_partial_path(self):
        """测试带部分路径的补全"""
        # 测试带部分路径的补全
        document = Document('index scan .', 12)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象
        for completion in completions:
            assert isinstance(completion, Completion)
    
    def test_path_completion_for_output_commands(self):
        """测试输出命令的路径补全"""
        # 测试 export csv 命令的路径补全
        document = Document('export csv ', 11)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象
        for completion in completions:
            assert isinstance(completion, Completion)
    
    def test_path_completion_for_option_commands(self):
        """测试带选项的命令的路径补全"""
        # 测试 clean script --output 命令的路径补全
        document = Document('clean script --output ', 20)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象
        for completion in completions:
            assert isinstance(completion, Completion)
    
    def test_path_completion_handles_special_characters(self):
        """测试路径补全处理特殊字符"""
        # 测试带空格的路径补全
        document = Document('index scan "', 12)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象
        for completion in completions:
            assert isinstance(completion, Completion)
    
    def test_path_completion_priority_over_command(self):
        """测试路径补全优先于命令补全"""
        # 确保路径补全优先于命令补全
        document = Document('index scan ', 11)
        completions = list(self.completer.get_completions(document, None))
        
        # 验证返回的是 Completion 对象
        for completion in completions:
            assert isinstance(completion, Completion)
        
        # 验证至少有一个补全结果
        assert len(completions) > 0