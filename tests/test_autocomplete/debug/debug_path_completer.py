#!/usr/bin/env python3
"""测试 PathCompleter 本身"""

from prompt_toolkit.completion import PathCompleter
from prompt_toolkit.document import Document

def test_path_completer():
    """测试 PathCompleter 是否能正常工作"""
    
    # 创建 PathCompleter
    completer = PathCompleter()
    
    # 测试空路径
    document = Document('', 0)
    completions = list(completer.get_completions(document, None))
    print(f"空路径补全数量: {len(completions)}")
    for i, completion in enumerate(completions[:5]):
        print(f"  {i+1}. text='{completion.text}', display={completion.display}")
    
    # 测试 C:\
    document = Document('C:\\', 3)
    completions = list(completer.get_completions(document, None))
    print(f"\nC:\\ 补全数量: {len(completions)}")
    for i, completion in enumerate(completions[:5]):
        print(f"  {i+1}. text='{completion.text}', display={completion.display}")
    
    # 测试 C:\U
    document = Document('C:\\U', 4)
    completions = list(completer.get_completions(document, None))
    print(f"\nC:\\U 补全数量: {len(completions)}")
    for i, completion in enumerate(completions[:5]):
        print(f"  {i+1}. text='{completion.text}', display={completion.display}")

if __name__ == "__main__":
    test_path_completer()
