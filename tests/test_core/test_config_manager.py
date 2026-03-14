import pytest
import os
import tempfile
import json
from commands.config import ConfigManager

class TestConfigManager:
    def test_get_config(self):
        """测试获取配置"""
        # 初始化ConfigManager
        config_manager = ConfigManager()
        
        # 获取配置
        config = config_manager.load_config()
        
        # 验证配置
        assert isinstance(config, dict)
        assert 'limit_path' in config
        assert 'excluded_patterns' in config
    
    def test_set_limit_path(self, temp_dir):
        """测试设置扫描范围限制"""
        # 初始化ConfigManager
        config_manager = ConfigManager()
        
        # 设置扫描范围限制
        config_manager.set_limit(temp_dir)
        
        # 验证设置结果
        assert config_manager.get_limit_path() == temp_dir
    
    def test_clear_limit_path(self):
        """测试清除扫描范围限制"""
        # 初始化ConfigManager
        config_manager = ConfigManager()
        
        # 清除扫描范围限制
        config_manager.clear_limit()
        
        # 验证清除结果
        assert config_manager.get_limit_path() is None
    
    def test_add_excluded_pattern(self):
        """测试添加排除模式"""
        # 初始化ConfigManager
        config_manager = ConfigManager()
        
        # 添加排除模式
        test_pattern = '*.tmp'
        config_manager.add_exclude_pattern(test_pattern)
        
        # 验证添加结果
        patterns = config_manager.get_excluded_patterns()
        assert test_pattern in patterns
    
    def test_remove_excluded_pattern(self):
        """测试移除排除模式"""
        # 初始化ConfigManager
        config_manager = ConfigManager()
        
        # 添加排除模式
        test_pattern = '*.tmp'
        config_manager.add_exclude_pattern(test_pattern)
        
        # 移除排除模式
        config_manager.remove_exclude_pattern(test_pattern)
        
        # 验证移除结果
        patterns = config_manager.get_excluded_patterns()
        assert test_pattern not in patterns
    
    def test_get_excluded_patterns(self):
        """测试获取排除模式"""
        # 初始化ConfigManager
        config_manager = ConfigManager()
        
        # 获取排除模式
        patterns = config_manager.get_excluded_patterns()
        
        # 验证结果
        assert isinstance(patterns, list)
