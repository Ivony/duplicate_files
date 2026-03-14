import pytest
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.document import Document
from main import app

class TestAutocomplete:
    """测试命令行自动补全功能"""
    
    def test_root_command_completion(self):
        """测试根命令补全功能"""
        # 从Typer应用中提取所有命令
        all_commands = []
        for group_info in app.registered_groups:
            all_commands.append(group_info.name)
        
        for cmd_info in app.registered_commands:
            if cmd_info.callback:
                cmd_name = cmd_info.name or getattr(cmd_info.callback, '__name__', 'unknown')
                all_commands.append(cmd_name)
        
        # 创建补全器
        completer = WordCompleter(all_commands, ignore_case=True)
        
        # 测试根命令补全
        document = Document('i', 1)
        result = list(completer.get_completions(document, None))
        assert len(result) > 0
        assert any('index' in c.text for c in result)
        
        document = Document('s', 1)
        result = list(completer.get_completions(document, None))
        assert len(result) > 0
        assert any('show' in c.text for c in result)
        
        document = Document('h', 1)
        result = list(completer.get_completions(document, None))
        assert len(result) > 0
        assert any('hash' in c.text for c in result)
    
    def test_subcommand_completion(self):
        """测试子命令补全功能"""
        # 从Typer应用中提取所有命令和子命令
        all_commands = []
        for group_info in app.registered_groups:
            sub_app = group_info.typer_instance
            for cmd_info in sub_app.registered_commands:
                if cmd_info.callback:
                    cmd_name = cmd_info.name or getattr(cmd_info.callback, '__name__', 'unknown')
                    all_commands.append(f"{group_info.name} {cmd_name}")
        
        # 创建补全器（启用句子模式以支持空格）
        completer = WordCompleter(all_commands, ignore_case=True, sentence=True)
        
        # 测试index子命令补全
        document = Document('index s', 6)
        result = list(completer.get_completions(document, None))
        assert len(result) > 0
        assert any('scan' in c.text for c in result)
        
        document = Document('index r', 6)
        result = list(completer.get_completions(document, None))
        assert len(result) > 0
        assert any('rebuild' in c.text for c in result)
        
        # 测试show子命令补全
        document = Document('show g', 5)
        result = list(completer.get_completions(document, None))
        assert len(result) > 0
        assert any('groups' in c.text for c in result)
        
        document = Document('show f', 5)
        result = list(completer.get_completions(document, None))
        assert len(result) > 0
        assert any('files' in c.text for c in result)
    
    def test_empty_input_completion(self):
        """测试空输入时的补全行为"""
        # 从Typer应用中提取所有命令
        all_commands = []
        for group_info in app.registered_groups:
            all_commands.append(group_info.name)
        
        for cmd_info in app.registered_commands:
            if cmd_info.callback:
                cmd_name = cmd_info.name or getattr(cmd_info.callback, '__name__', 'unknown')
                all_commands.append(cmd_name)
        
        # 创建补全器
        completer = WordCompleter(all_commands, ignore_case=True)
        
        # 测试空输入补全
        document = Document('', 0)
        result = list(completer.get_completions(document, None))
        assert len(result) > 0
        # 应该返回所有命令
        assert len(result) == len(all_commands)
    
    def test_partial_input_completion(self):
        """测试部分输入时的补全行为"""
        # 从Typer应用中提取所有命令
        all_commands = []
        for group_info in app.registered_groups:
            all_commands.append(group_info.name)
        
        for cmd_info in app.registered_commands:
            if cmd_info.callback:
                cmd_name = cmd_info.name or getattr(cmd_info.callback, '__name__', 'unknown')
                all_commands.append(cmd_name)
        
        # 创建补全器
        completer = WordCompleter(all_commands, ignore_case=True)
        
        # 测试部分输入补全
        document = Document('ind', 3)
        result = list(completer.get_completions(document, None))
        assert len(result) > 0
        assert any('index' in c.text for c in result)
        
        document = Document('sh', 2)
        result = list(completer.get_completions(document, None))
        assert len(result) > 0
        assert any('show' in c.text for c in result)
        
        document = Document('exp', 3)
        result = list(completer.get_completions(document, None))
        assert len(result) > 0
        assert any('export' in c.text for c in result)
    
    def test_invalid_input_completion(self):
        """测试无效输入时的补全行为"""
        # 从Typer应用中提取所有命令
        all_commands = []
        for group_info in app.registered_groups:
            all_commands.append(group_info.name)
        
        for cmd_info in app.registered_commands:
            if cmd_info.callback:
                cmd_name = cmd_info.name or getattr(cmd_info.callback, '__name__', 'unknown')
                all_commands.append(cmd_name)
        
        # 创建补全器
        completer = WordCompleter(all_commands, ignore_case=True)
        
        # 测试无效输入补全
        document = Document('xyz', 3)
        result = list(completer.get_completions(document, None))
        assert len(result) == 0
        
        document = Document('123', 3)
        result = list(completer.get_completions(document, None))
        assert len(result) == 0
    
    def test_case_insensitive_completion(self):
        """测试不区分大小写的补全功能"""
        # 从Typer应用中提取所有命令
        all_commands = []
        for group_info in app.registered_groups:
            all_commands.append(group_info.name)
        
        for cmd_info in app.registered_commands:
            if cmd_info.callback:
                cmd_name = cmd_info.name or getattr(cmd_info.callback, '__name__', 'unknown')
                all_commands.append(cmd_name)
        
        # 创建补全器
        completer = WordCompleter(all_commands, ignore_case=True)
        
        # 测试不区分大小写
        document = Document('index', 5)
        result_lower = list(completer.get_completions(document, None))
        
        document = Document('INDEX', 5)
        result_upper = list(completer.get_completions(document, None))
        
        document = Document('InDeX', 5)
        result_mixed = list(completer.get_completions(document, None))
        
        assert len(result_lower) > 0
        assert len(result_upper) > 0
        assert len(result_mixed) > 0
        # 所有结果应该相同
        assert len(result_lower) == len(result_upper) == len(result_mixed)
    
    def test_all_available_commands(self):
        """测试所有可用命令都能被补全"""
        # 从Typer应用中提取所有命令
        all_commands = []
        for group_info in app.registered_groups:
            all_commands.append(group_info.name)
        
        for cmd_info in app.registered_commands:
            if cmd_info.callback:
                cmd_name = cmd_info.name or getattr(cmd_info.callback, '__name__', 'unknown')
                all_commands.append(cmd_name)
        
        # 创建补全器
        completer = WordCompleter(all_commands, ignore_case=True)
        
        # 验证所有根命令都能被补全
        expected_root_commands = ['index', 'show', 'hash', 'export', 'config', 'db', 'clean']
        for cmd in expected_root_commands:
            document = Document(cmd, len(cmd))
            result = list(completer.get_completions(document, None))
            assert len(result) > 0
            assert any(cmd in c.text for c in result)
    
    def test_subcommand_structure(self):
        """测试子命令结构的完整性"""
        # 验证每个根命令都有对应的子命令
        for group_info in app.registered_groups:
            group_name = group_info.name
            sub_app = group_info.typer_instance
            
            # 获取子命令
            subcommands = []
            for cmd_info in sub_app.registered_commands:
                if cmd_info.callback:
                    cmd_name = cmd_info.name or getattr(cmd_info.callback, '__name__', 'unknown')
                    subcommands.append(cmd_name)
            
            # 验证子命令存在
            assert len(subcommands) > 0, f"命令 {group_name} 没有子命令"
            
            # 验证子命令补全（启用句子模式以支持空格）
            all_commands = [f"{group_name} {cmd}" for cmd in subcommands]
            completer = WordCompleter(all_commands, ignore_case=True, sentence=True)
            
            for subcmd in subcommands:
                full_cmd = f"{group_name} {subcmd}"
                document = Document(full_cmd, len(full_cmd))
                result = list(completer.get_completions(document, None))
                assert len(result) > 0, f"子命令 {full_cmd} 无法被补全"
