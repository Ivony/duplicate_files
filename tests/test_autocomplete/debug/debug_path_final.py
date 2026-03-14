from prompt_toolkit.document import Document

# 模拟完整的路径补全逻辑
def test_path_completion_logic():
    """测试路径补全逻辑"""
    # 测试用例
    test_cases = [
        # 测试用例1：输入 'index scan C:\T'
        {
            'text': r'index scan C\T',
            'cursor_position': 15,
            'command_prefix': 'index scan ',
            'expected_prefix': 'C\\',
            'expected_completion': 'Temp',
            'expected_result': r'index scan C\Temp'
        },
        # 测试用例2：输入 'index scan C:/T'
        {
            'text': 'index scan C:/T',
            'cursor_position': 15,
            'command_prefix': 'index scan ',
            'expected_prefix': 'C:/',
            'expected_completion': 'Temp',
            'expected_result': 'index scan C:/Temp'
        },
        # 测试用例3：输入 'index scan .\T'
        {
            'text': r'index scan .\T',
            'cursor_position': 15,
            'command_prefix': 'index scan ',
            'expected_prefix': '.\\',
            'expected_completion': 'Temp',
            'expected_result': r'index scan .\Temp'
        },
    ]
    
    for i, test_case in enumerate(test_cases):
        text = test_case['text']
        cursor_position = test_case['cursor_position']
        command_prefix = test_case['command_prefix']
        expected_prefix = test_case['expected_prefix']
        expected_completion = test_case['expected_completion']
        expected_result = test_case['expected_result']
        
        # 提取路径部分
        path_part = text[len(command_prefix):]
        
        # 计算 start_position
        start_position = -(cursor_position - len(command_prefix))
        
        # 处理路径前缀
        complete_text = expected_completion
        if '\\' in path_part or '/' in path_part:
            if '\\' in path_part:
                if path_part.count('\\') > 0:
                    prefix = path_part.rsplit('\\', 1)[0]
                    if prefix:
                        prefix += '\\'
                else:
                    prefix = path_part
            else:
                if path_part.count('/') > 0:
                    prefix = path_part.rsplit('/', 1)[0]
                    if prefix:
                        prefix += '/'
                else:
                    prefix = path_part
            complete_text = prefix + complete_text
        
        # 计算替换后的结果
        start_pos = cursor_position + start_position
        end_pos = cursor_position
        result = text[:start_pos] + complete_text + text[end_pos:]
        
        print(f"测试用例 {i+1}:")
        print(f"  输入: '{text}'")
        print(f"  路径部分: '{path_part}'")
        print(f"  start_position: {start_position}")
        print(f"  替换范围: {start_pos} - {end_pos}")
        print(f"  补全文本: '{complete_text}'")
        print(f"  期望结果: '{expected_result}'")
        print(f"  实际结果: '{result}'")
        print(f"  结果: {'通过' if result == expected_result else '失败'}")
        print()

if __name__ == "__main__":
    test_path_completion_logic()
