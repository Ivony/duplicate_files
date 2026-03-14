from prompt_toolkit.document import Document

# 模拟我们的补全逻辑
def simulate_completion(text, cursor_position):
    """模拟路径补全逻辑"""
    # 提取命令前缀和路径部分
    if text.startswith('index scan '):
        command_prefix = 'index scan '
        path_part = text[len(command_prefix):]
        
        # 模拟补全结果（这里假设我们有一个名为Temp的目录）
        # 模拟PathCompleter的行为
        completion_text = 'emp'  # 这是PathCompleter返回的text
        display_text = 'Temp/'  # 这是PathCompleter返回的display
        
        # 提取完整的补全文本
        complete_text = display_text.rstrip('/').rstrip('\\')
        
        # 处理路径前缀：如果输入包含路径前缀（如C:\），确保补全结果包含完整路径
        if '\\' in path_part or '/' in path_part:
            # 提取路径前缀
            if '\\' in path_part:
                # 对于 Windows 路径，处理反斜杠
                if path_part.count('\\') > 0:
                    prefix = path_part.rsplit('\\', 1)[0]
                    # 如果前缀不是空的，添加反斜杠
                    if prefix:
                        prefix += '\\'
                else:
                    prefix = ''
            else:
                # 对于 Unix 风格路径
                if path_part.count('/') > 0:
                    prefix = path_part.rsplit('/', 1)[0]
                    # 如果前缀不是空的，添加斜杠
                    if prefix:
                        prefix += '/'
                else:
                    prefix = ''
            
            # 组合完整路径
            complete_text = prefix + complete_text
        
        # 计算start_position
        start_position = -len(path_part)
        
        # 计算替换后的结果
        start_pos = cursor_position + start_position
        end_pos = cursor_position
        new_text = text[:start_pos] + complete_text + text[end_pos:]
        
        return new_text
    return text

# 测试场景
def test_path_completion():
    """测试路径补全"""
    test_cases = [
        # 测试用例1：输入 'index scan C:\T'
        {
            'input': r'index scan C\T',
            'cursor_position': 15,
            'expected': r'index scan C\Temp'
        },
        # 测试用例2：输入 'index scan C:/T'
        {
            'input': 'index scan C:/T',
            'cursor_position': 15,
            'expected': 'index scan C:/Temp'
        },
        # 测试用例3：输入 'index scan .\T'
        {
            'input': r'index scan .\T',
            'cursor_position': 15,
            'expected': r'index scan .\Temp'
        },
    ]
    
    for i, test_case in enumerate(test_cases):
        input_text = test_case['input']
        cursor_position = test_case['cursor_position']
        expected = test_case['expected']
        
        result = simulate_completion(input_text, cursor_position)
        
        print(f"测试用例 {i+1}:")
        print(f"  输入: '{input_text}'")
        print(f"  期望: '{expected}'")
        print(f"  实际: '{result}'")
        print(f"  结果: {'通过' if result == expected else '失败'}")
        print()

if __name__ == "__main__":
    test_path_completion()
