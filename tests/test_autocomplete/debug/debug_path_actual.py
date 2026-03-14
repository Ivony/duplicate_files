#!/usr/bin/env python3
"""测试实际路径补全功能"""

from prompt_toolkit.document import Document
from main import TyperCompleter, app

def test_path_completion():
    """测试路径补全是否返回实际的文件/目录"""
    completer = TyperCompleter(app)
    
    # 测试 index scan 命令的路径补全
    document = Document('index scan C:\\', 13)
    completions = list(completer.get_completions(document, None))
    
    print(f"输入: 'index scan C:\\'")
    print(f"补全数量: {len(completions)}")
    print(f"补全列表:")
    for i, completion in enumerate(completions[:10]):  # 只显示前10个
        print(f"  {i+1}. text='{completion.text}', start_position={completion.start_position}")
        if hasattr(completion, 'display'):
            print(f"     display={completion.display}")
    
    if len(completions) > 10:
        print(f"  ... 还有 {len(completions) - 10} 个")
    
    # 测试带部分路径的补全
    document = Document('index scan C:\\U', 14)
    completions = list(completer.get_completions(document, None))
    
    print(f"\n输入: 'index scan C:\\U'")
    print(f"补全数量: {len(completions)}")
    print(f"补全列表:")
    for i, completion in enumerate(completions[:10]):
        print(f"  {i+1}. text='{completion.text}', start_position={completion.start_position}")
        if hasattr(completion, 'display'):
            print(f"     display={completion.display}")

if __name__ == "__main__":
    test_path_completion()
