# 自动补全测试

本文件夹包含所有与自动补全功能相关的测试用例。

## 文件夹结构

```
test_autocomplete/
├── README.md                      # 本文档
├── test_autocomplete.py           # 命令自动补全测试（17个测试用例）
├── test_path_completion.py        # 路径自动补全测试（15个测试用例）
└── debug/                         # 调试脚本（非正式测试）
    ├── debug_typer_commands.py    # Typer 命令结构调试
    ├── debug_path_main.py         # 路径补全主调试脚本
    ├── debug_path_actual.py       # 实际路径补全调试
    ├── debug_path_completer.py    # PathCompleter 组件调试
    ├── debug_path_behavior.py     # 路径补全行为分析
    ├── debug_path_final.py        # 路径补全最终验证
    └── debug_path_fix.py          # 路径补全修复验证
```

## 测试目标

- 验证根命令补全功能的正确性
- 验证子命令补全功能的完整性
- 验证参数补全功能的准确性
- 验证补全功能的边界情况处理
- 验证补全功能的性能和响应速度

## 测试范围

- 根命令自动补全
- 子命令自动补全
- 参数自动补全
- 空输入补全
- 部分输入补全
- 无效输入补全
- 大小写不敏感补全

## 测试文件说明

### 命令自动补全测试 (`test_autocomplete.py`)

测试 Typer 命令的自动补全功能：

| 用例名 | 描述 |
|--------|------|
| `test_empty_input_shows_all_commands` | 空输入显示所有命令 |
| `test_root_command_prefix_completion` | 根命令前缀补全 |
| `test_subcommand_completion` | 子命令补全 |
| `test_case_insensitive_completion` | 大小写不敏感补全 |
| `test_no_duplicate_completions` | 无重复补全项 |
| ... | 更多测试用例 |

### 路径自动补全测试 (`test_path_completion.py`)

测试文件/目录路径的自动补全功能：

#### 命令配置测试
| 用例名 | 描述 |
|--------|------|
| `test_path_completion_commands` | 验证路径补全命令配置 |

#### 路径类型测试
| 用例名 | 描述 |
|--------|------|
| `test_file_path_completion` | 测试文件路径补全 |
| `test_directory_path_completion` | 测试目录路径补全 |
| `test_generic_path_completion` | 测试通用路径补全 |

#### 选项处理测试
| 用例名 | 描述 |
|--------|------|
| `test_option_path_completion` | 测试带选项的路径补全 |
| `test_non_path_completion` | 测试非路径补全命令 |
| `test_option_vs_path_distinction` | 测试选项和路径的区分 |

#### 路径格式测试
| 用例名 | 描述 |
|--------|------|
| `test_path_completion_with_partial_input` | 测试带部分输入的路径补全 |
| `test_path_completion_with_different_separators` | 测试不同路径分隔符 |
| `test_path_completion_with_backslash` | 测试带反斜杠的路径补全 |

#### 特殊场景测试
| 用例名 | 描述 |
|--------|------|
| `test_path_completion_priority` | 测试路径补全优先级 |
| `test_path_completion_preserves_prefix` | 测试路径补全保留路径前缀 |
| `test_path_completion_handles_empty_path` | 测试空路径处理 |
| `test_path_completion_handles_special_characters` | 测试特殊字符处理 |

### 调试脚本 (`debug/`)

`debug/` 文件夹中的脚本用于调试和分析，不是正式的单元测试。这些脚本使用 `print` 输出结果，而不是断言。

| 文件名 | 描述 | 用途 |
|--------|------|------|
| `debug_typer_commands.py` | Typer 命令结构调试 | 分析 Typer 应用的命令注册结构 |
| `debug_path_main.py` | 路径补全主调试脚本 | 调试 TyperCompleter 的路径补全功能 |
| `debug_path_actual.py` | 实际路径补全调试 | 测试实际文件/目录的补全结果 |
| `debug_path_completer.py` | PathCompleter 组件调试 | 测试 prompt_toolkit 的 PathCompleter 组件 |
| `debug_path_behavior.py` | 路径补全行为分析 | 分析路径补全的核心逻辑和行为 |
| `debug_path_final.py` | 路径补全最终验证 | 验证修复后的路径补全逻辑 |
| `debug_path_fix.py` | 路径补全修复验证 | 模拟和验证路径补全修复方案 |

#### 运行调试脚本

```bash
# 调试 Typer 命令结构
python tests/test_autocomplete/debug/debug_typer_commands.py

# 调试路径补全主功能
python tests/test_autocomplete/debug/debug_path_main.py

# 调试实际路径补全
python tests/test_autocomplete/debug/debug_path_actual.py

# 调试 PathCompleter 组件
python tests/test_autocomplete/debug/debug_path_completer.py

# 分析路径补全行为
python tests/test_autocomplete/debug/debug_path_behavior.py

# 验证路径补全修复（最终）
python tests/test_autocomplete/debug/debug_path_final.py

# 验证路径补全修复（模拟）
python tests/test_autocomplete/debug/debug_path_fix.py
```

## 已修复的问题

### 问题：路径补全不显示
**描述**：当输入 `index scan C:\` 时，路径补全不显示任何候选项。

**原因**：代码错误地将路径部分（`C:\`）识别为选项，进入了错误的补全逻辑分支。

**解决方案**：添加辅助函数 `is_option()` 来区分选项（以 `--` 或 `-` 开头）和路径部分（包含 `\`、`/` 或 `:`）。

**相关测试**：
- `test_path_completion_with_backslash` - 测试带反斜杠的路径补全
- `test_option_vs_path_distinction` - 测试选项和路径的区分

### 问题：路径补全触发时机过早
**描述**：当输入 `E:` 时，就会显示 E:\ 下面的所有文件夹作为候选列表，选择时会覆盖掉 `E:` 字符，导致路径错误。

**原因**：PathCompleter 在输入驱动器字母（如 `E:`）时就触发补全，但此时用户可能还在输入。

**解决方案**：添加检查，只有当路径部分包含路径分隔符（`\` 或 `/`）时才触发补全。用户需要输入 `E:\` 才会触发补全。

**相关测试**：
- `test_path_completion_requires_separator` - 测试路径补全需要路径分隔符
- `test_path_completion_with_partial_input` - 测试不带分隔符时不触发补全

## 测试数据

### 根命令列表
- `index` - 扫描与索引指令
- `show` - 显示数据指令
- `hash` - 哈希计算指令
- `export` - 导出指令
- `config` - 配置指令
- `db` - 数据库指令
- `clean` - 清理指令

### 子命令列表

#### index 子命令
- `scan` - 扫描路径并建立索引
- `import` - 从CSV导入文件列表
- `rebuild` - 重建重复文件组
- `clear` - 清除文件索引

#### show 子命令
- `groups` - 显示重复文件组
- `files` - 显示指定路径的文件
- `hash` - 显示指定哈希值的文件
- `stats` - 显示数据汇总报告

#### hash 子命令
- `calc` - 计算哈希值
- `verify` - 验证哈希值
- `status` - 查看哈希计算状态
- `clear` - 清除哈希值
- `backup` - 备份哈希值
- `restore` - 恢复哈希值

#### export 子命令
- `csv` - 导出为CSV格式
- `json` - 导出为JSON格式
- `report` - 生成详细报告

#### config 子命令
- `limit` - 设置扫描范围限制
- `exclude` - 管理排除模式

#### db 子命令
- `check` - 检查数据库结构和数据
- `optimize` - 优化数据库性能
- `init` - 重建数据库结构

#### clean 子命令
- `run` - 执行清理操作
- `script` - 生成清理脚本

## 运行测试

运行所有自动补全测试：
```bash
python -m pytest tests/test_autocomplete/ -v
```

只运行命令自动补全测试：
```bash
python -m pytest tests/test_autocomplete/test_autocomplete.py -v
```

只运行路径自动补全测试：
```bash
python -m pytest tests/test_autocomplete/test_path_completion.py -v
```

## 测试验收标准

### 功能验收
- [x] 所有根命令都能被正确补全
- [x] 所有子命令都能被正确补全
- [x] 空输入时显示所有命令
- [x] 部分输入时显示匹配的命令
- [x] 无效输入时不显示任何建议
- [x] 补全功能不区分大小写

### 性能验收
- [ ] 补全响应时间 < 100ms
- [ ] 补全建议数量合理（不超过20个）
- [ ] 补全结果准确率 > 95%

## 测试统计

- 总测试用例数：32
- 命令补全测试：17
- 路径补全测试：15
- 调试脚本数：5

## 相关文档

- [../README.md](../README.md) - 测试总览
- [../../main.py](../../main.py) - 自动补全实现代码
