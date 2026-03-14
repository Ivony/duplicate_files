import os
import tempfile
import shutil

def create_test_file(content, directory=None):
    """创建测试文件"""
    if directory is None:
        directory = tempfile.gettempdir()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', dir=directory, delete=False) as f:
        f.write(content)
        return f.name

def create_test_directory():
    """创建测试目录"""
    return tempfile.mkdtemp()

def cleanup_test_directory(directory):
    """清理测试目录"""
    if os.path.exists(directory):
        shutil.rmtree(directory)

def create_duplicate_files(content, count=2, directory=None):
    """创建重复内容的文件"""
    if directory is None:
        directory = tempfile.gettempdir()
    
    files = []
    for i in range(count):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', dir=directory, delete=False) as f:
            f.write(content)
            files.append(f.name)
    return files
