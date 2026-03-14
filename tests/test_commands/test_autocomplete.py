import pytest
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.document import Document
from main import app, TyperCompleter


class TestTyperCompleter:
    """测试上下文感知的Typer补全器"""
    
    def test_empty_input_shows_root_commands(self):
        """测试空输入时显示所有根命令"""
        completer = TyperCompleter(app)
        
        document = Document('', 0)
        result = list(completer.get_completions(document, None))
        
        # 应该包含所有根命令
        result_texts = [c.text for c in result]
        assert 'index' in result_texts
        assert 'show' in result_texts
        assert 'hash' in result_texts
        assert 'export' in result_texts
        assert 'config' in result_texts
        assert 'db' in result_texts
        assert 'clean' in result_texts
        # 也应该包含独立命令
        assert 'version' in result_texts
        assert 'help' in result_texts
    
    def test_root_command_prefix_completion(self):
        """测试根命令前缀补全"""
        completer = TyperCompleter(app)
        
        # 输入 'i' 应该补全为 'index'
        document = Document('i', 1)
        result = list(completer.get_completions(document, None))
        result_texts = [c.text for c in result]
        assert 'index' in result_texts
        assert 'show' not in result_texts  # 不应该显示不匹配的命令
    
    def test_subcommand_completion_after_root(self):
        """测试在根命令后补全子命令 - 关键测试用例"""
        completer = TyperCompleter(app)
        
        # 输入 'index s' 应该补全为 'scan' 而不是 'show'
        document = Document('index s', 7)
        result = list(completer.get_completions(document, None))
        result_texts = [c.text for c in result]
        
        # 应该包含匹配 's' 的 index 子命令
        assert 'scan' in result_texts
        # 不应该包含其他根命令的子命令
        assert 'groups' not in result_texts  # show的子命令
        assert 'files' not in result_texts   # show的子命令
    
    def test_subcommand_completion_show_group(self):
        """测试show命令组的子命令补全"""
        completer = TyperCompleter(app)
        
        # 输入 'show g' 应该补全为 'groups'
        document = Document('show g', 6)
        result = list(completer.get_completions(document, None))
        result_texts = [c.text for c in result]
        
        # 应该包含匹配 'g' 的 show 子命令
        assert 'groups' in result_texts
        # 不应该包含 index 的子命令
        assert 'scan' not in result_texts
    
    def test_subcommand_completion_hash_group(self):
        """测试hash命令组的子命令补全"""
        completer = TyperCompleter(app)
        
        # 输入 'hash c' 应该补全为 'calc'
        document = Document('hash c', 6)
        result = list(completer.get_completions(document, None))
        result_texts = [c.text for c in result]
        
        assert 'calc' in result_texts
        assert 'clear' in result_texts
        # 不应该包含其他命令
        assert 'scan' not in result_texts
        assert 'groups' not in result_texts
    
    def test_unknown_root_command_fallback(self):
        """测试未知根命令时的回退行为"""
        completer = TyperCompleter(app)
        
        # 输入 'unknown s' - 未知根命令，没有匹配的补全
        document = Document('unknown s', 9)
        result = list(completer.get_completions(document, None))
        
        # 未知命令没有匹配的补全，返回空列表
        assert len(result) == 0
    
    def test_case_insensitive_subcommand(self):
        """测试子命令大小写不敏感"""
        completer = TyperCompleter(app)
        
        # 输入 'INDEX S' 应该也能补全
        document = Document('INDEX S', 7)
        result = list(completer.get_completions(document, None))
        result_texts = [c.text for c in result]
        
        assert 'scan' in result_texts
    
    def test_complete_subcommand_no_duplicates(self):
        """测试完整子命令不产生重复"""
        completer = TyperCompleter(app)
        
        # 输入完整的 'index scan'
        document = Document('index scan', 10)
        result = list(completer.get_completions(document, None))
        
        # 完全匹配时不应该显示该子命令作为候选项
        assert len(result) == 0
        
        # 输入完整的 'show groups'
        document = Document('show groups', 11)
        result = list(completer.get_completions(document, None))
        assert len(result) == 0
        
        # 输入完整的 'hash calc'
        document = Document('hash calc', 9)
        result = list(completer.get_completions(document, None))
        assert len(result) == 0
    
    def test_multiple_subcommands_suggestions(self):
        """测试多个子命令建议"""
        completer = TyperCompleter(app)
        
        # 输入 'index ' (注意空格，当前词为空)
        document = Document('index ', 6)
        result = list(completer.get_completions(document, None))
        result_texts = [c.text for c in result]
        
        # 应该显示所有 index 的子命令（空字符串匹配所有）
        assert 'scan' in result_texts
        assert 'rebuild' in result_texts
        assert 'clear' in result_texts


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
