from prompt_toolkit.document import Document
from prompt_toolkit.completion import Completion, PathCompleter

# 模拟路径补全的核心逻辑
def test_path_completion_logic():
    """测试路径补全逻辑"""
    # 创建路径补全器
    path_completer = PathCompleter(only_directories=True)
    
    # 测试场景：输入 'C:\T' 应该补全为 'C:\Temp'
    path_part = 'C:\\T'
    document = Document(path_part, len(path_part))
    
    # 生成补全
    completions = list(path_completer.get_completions(document, None))
    
    print(f"输入路径: '{path_part}'")
    print(f"补全结果数量: {len(completions)}")
    
    for i, completion in enumerate(completions):
        print(f"\n补全 {i+1}:")
        print(f"  文本: '{completion.text}'")
        print(f"  开始位置: {completion.start_position}")
        print(f"  显示: {completion.display}")
        
        # 提取完整路径
        if hasattr(completion.display, 'text'):
            complete_text = completion.display.text
        elif hasattr(completion.display, '__iter__'):
            # 处理 FormattedText
            complete_text = ''.join([part[1] for part in completion.display if isinstance(part, tuple)])
        else:
            complete_text = completion.text
        
        # 移除末尾的斜杠
        complete_text = complete_text.rstrip('/').rstrip('\\')
        print(f"  提取的完整路径: '{complete_text}'")

if __name__ == "__main__":
    test_path_completion_logic()
