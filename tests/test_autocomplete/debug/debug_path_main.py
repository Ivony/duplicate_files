#!/usr/bin/env python3
"""调试路径补全功能"""

from prompt_toolkit.document import Document
from main import TyperCompleter, app

def debug_path_completion():
    """调试路径补全"""
    completer = TyperCompleter(app)
    
    print("=== 调试信息 ===")
    print(f"path_completion_commands: {completer.path_completion_commands}")
    print(f"root_commands: {completer.root_commands}")
    print()
    
    # 测试 index scan 命令
    text = 'index scan C:\\'
    document = Document(text, len(text))
    
    print(f"输入: '{text}'")
    print(f"光标位置: {document.cursor_position}")
    print(f"文本分割: {text.split()}")
    
    # 检查是否匹配路径补全命令
    words = text.split()
    if len(words) >= 2:
        root_cmd = words[0]
        sub_cmd = words[1]
        print(f"root_cmd: {root_cmd}, sub_cmd: {sub_cmd}")
        print(f"是否在 path_completion_commands 中: {(root_cmd, sub_cmd) in completer.path_completion_commands}")
    
    # 获取补全
    completions = list(completer.get_completions(document, None))
    print(f"\n补全数量: {len(completions)}")
    for i, completion in enumerate(completions[:5]):
        print(f"  {i+1}. text='{completion.text}', start_position={completion.start_position}")

if __name__ == "__main__":
    debug_path_completion()
