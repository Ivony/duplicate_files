# 核心功能模块测试

本文件夹包含核心功能模块的测试用例。

## 文件夹结构

```
test_core/
├── README.md                  # 本文档
├── test_file_scanner.py       # FileScanner 模块测试
├── test_hash_calculator.py    # HashCalculator 模块测试
├── test_index_manager.py      # IndexManager 模块测试
└── test_config_manager.py     # ConfigManager 模块测试
```

## 测试目标

- 验证核心功能模块的功能正确性
- 验证模块间的交互正确性
- 验证边界情况的处理
- 验证错误处理的完整性

## 测试范围

- FileScanner - 文件扫描模块
- HashCalculator - 哈希计算模块
- IndexManager - 索引管理模块
- ConfigManager - 配置管理模块

## 测试用例说明

### FileScanner 模块测试 (`test_file_scanner.py`)

| 测试用例 | 描述 |
|---------|------|
| `test_scan_file` | 测试单个文件扫描功能 |
| `test_scan_directory` | 测试目录扫描功能 |
| `test_scan_from_csv` | 测试从CSV导入文件列表功能 |
| `test_is_path_excluded` | 测试路径排除功能 |

### HashCalculator 模块测试 (`test_hash_calculator.py`)

| 测试用例 | 描述 |
|---------|------|
| `test_calculate_file_hash` | 测试文件哈希计算功能 |
| `test_same_content_same_hash` | 测试相同内容文件哈希相同 |
| `test_different_content_different_hash` | 测试不同内容文件哈希不同 |
| `test_empty_file_hash` | 测试空文件哈希计算功能 |

### IndexManager 模块测试 (`test_index_manager.py`)

| 测试用例 | 描述 |
|---------|------|
| `test_clean_files` | 测试清除文件索引功能 |
| `test_rebuild_duplicate_groups` | 测试重建重复文件组功能 |
| `test_clean_index` | 测试清理索引功能 |
| `test_clean_files_by_pattern` | 测试按模式清除文件索引功能 |

### ConfigManager 模块测试 (`test_config_manager.py`)

| 测试用例 | 描述 |
|---------|------|
| `test_load_config` | 测试获取配置功能 |
| `test_set_limit` | 测试设置扫描范围限制功能 |
| `test_clear_limit` | 测试清除扫描范围限制功能 |
| `test_add_exclude_pattern` | 测试添加排除模式功能 |
| `test_remove_exclude_pattern` | 测试移除排除模式功能 |
| `test_get_excluded_patterns` | 测试获取排除模式功能 |

## 模块间交互测试

### 扫描和索引流程
1. 使用 FileScanner 扫描文件
2. 使用 IndexManager 建立索引
3. 验证索引正确建立
4. 验证数据一致性

### 哈希计算和索引更新
1. 建立文件索引
2. 使用 HashCalculator 计算哈希
3. 验证索引中的哈希值已更新
4. 验证重复文件组已重建

### 配置和扫描集成
1. 使用 ConfigManager 设置扫描范围限制
2. 使用 FileScanner 扫描文件
3. 验证扫描范围符合限制
4. 验证排除模式生效

## 运行测试

运行所有核心模块测试：
```bash
python -m pytest tests/test_core/ -v
```

运行特定模块测试：
```bash
python -m pytest tests/test_core/test_file_scanner.py -v
python -m pytest tests/test_core/test_hash_calculator.py -v
python -m pytest tests/test_core/test_index_manager.py -v
python -m pytest tests/test_core/test_config_manager.py -v
```

## 测试验收标准

### 功能验收
- [x] 所有模块功能正确
- [x] 所有边界情况处理正确
- [x] 所有错误处理完整
- [x] 模块间交互正确

### 性能验收
- [ ] 文件扫描性能良好
- [ ] 哈希计算性能良好
- [ ] 索引操作性能良好
- [ ] 内存使用合理

### 稳定性验收
- [ ] 长时间运行稳定
- [ ] 大数据量处理稳定
- [ ] 异常情况处理稳定

## 相关文档

- [../README.md](../README.md) - 测试总览
- [../test_commands/README.md](../test_commands/README.md) - 命令行指令测试
