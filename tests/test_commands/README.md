# 命令行指令测试

本文件夹包含所有命令行指令的测试用例。

## 文件夹结构

```
test_commands/
├── README.md              # 本文档
├── test_index.py          # index 命令测试
├── test_show.py           # show 命令测试
├── test_hash.py           # hash 命令测试
├── test_export.py         # export 命令测试
├── test_config.py         # config 命令测试
├── test_db.py             # db 命令测试
├── test_clean.py          # clean 命令测试
└── test_main.py           # 主程序测试
```

## 测试目标

- 验证所有命令行指令的功能正确性
- 验证命令参数的有效性
- 验证命令输出的准确性
- 验证错误处理的完整性

## 测试范围

- index 命令及其子命令
- show 命令及其子命令
- hash 命令及其子命令
- export 命令及其子命令
- config 命令及其子命令
- db 命令及其子命令
- clean 命令及其子命令

## 测试用例说明

### index 命令测试 (`test_index.py`)

| 测试用例 | 描述 |
|---------|------|
| `test_index_scan` | 测试扫描路径并建立索引功能 |
| `test_index_rebuild` | 测试重建重复文件组功能 |
| `test_index_clear` | 测试清除文件索引功能 |

### show 命令测试 (`test_show.py`)

| 测试用例 | 描述 |
|---------|------|
| `test_show_groups` | 测试显示重复文件组功能 |
| `test_show_files` | 测试显示指定路径的文件功能 |
| `test_show_hash` | 测试显示指定哈希值的文件功能 |
| `test_show_stats` | 测试显示数据汇总报告功能 |

### hash 命令测试 (`test_hash.py`)

| 测试用例 | 描述 |
|---------|------|
| `test_hash_calc` | 测试计算哈希值功能 |
| `test_hash_verify` | 测试哈希值验证功能 |
| `test_hash_status` | 测试查看哈希计算状态功能 |
| `test_hash_clear` | 测试清除哈希值功能 |

### export 命令测试 (`test_export.py`)

| 测试用例 | 描述 |
|---------|------|
| `test_export_csv` | 测试导出为CSV格式功能 |
| `test_export_json` | 测试导出为JSON格式功能 |
| `test_export_report` | 测试生成详细报告功能 |

### config 命令测试 (`test_config.py`)

| 测试用例 | 描述 |
|---------|------|
| `test_config_limit` | 测试设置扫描范围限制功能 |
| `test_config_limit_clear` | 测试清除扫描范围限制功能 |
| `test_config_exclude` | 测试管理排除模式功能 |

### db 命令测试 (`test_db.py`)

| 测试用例 | 描述 |
|---------|------|
| `test_db_check` | 测试检查数据库结构和数据功能 |
| `test_db_optimize` | 测试优化数据库性能功能 |
| `test_db_init` | 测试重建数据库结构功能 |

### clean 命令测试 (`test_clean.py`)

| 测试用例 | 描述 |
|---------|------|
| `test_clean_run` | 测试执行清理操作功能 |
| `test_clean_script` | 测试生成清理脚本功能 |

## 运行测试

运行所有命令测试：
```bash
python -m pytest tests/test_commands/ -v
```

运行特定命令测试：
```bash
python -m pytest tests/test_commands/test_index.py -v
python -m pytest tests/test_commands/test_show.py -v
python -m pytest tests/test_commands/test_hash.py -v
python -m pytest tests/test_commands/test_export.py -v
python -m pytest tests/test_commands/test_config.py -v
python -m pytest tests/test_commands/test_db.py -v
python -m pytest tests/test_commands/test_clean.py -v
```

## 测试验收标准

### 功能验收
- [x] 所有命令都能正确执行
- [x] 所有参数都能正确处理
- [x] 所有输出都能正确显示
- [x] 所有错误都能正确处理

### 性能验收
- [ ] 命令执行时间在合理范围内
- [ ] 大数据量处理性能良好
- [ ] 内存使用合理

### 用户体验验收
- [ ] 命令输出清晰易读
- [ ] 错误信息准确有用
- [ ] 帮助信息完整清晰

## 相关文档

- [../README.md](../README.md) - 测试总览
- [../test_autocomplete/README.md](../test_autocomplete/README.md) - 自动补全测试
