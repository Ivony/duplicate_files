# 重复文件分析工具

[![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![AI Generated](https://img.shields.io/badge/AI%20Generated-100%25-brightgreen.svg)](https://github.com/Ivony/duplicate_files)

> 🤖 **本项目完全由 AI 编码实现** - 从架构设计到代码实现，全部由人工智能助手完成

## 项目简介

这是一个功能强大的重复文件分析工具，用于扫描、分析和清理重复文件。项目采用现代化的 Python 技术栈，提供了直观的命令行界面和丰富的功能特性。

### ✨ AI 编码亮点

本项目是一个完整的 AI 编码案例，展示了人工智能在软件开发中的能力：

- 🏗️ **架构设计**：AI 设计了模块化的项目结构
- 💻 **代码实现**：所有代码均由 AI 编写
- 🧪 **测试验证**：AI 进行了功能测试和调试
- 📝 **文档编写**：AI 生成了完整的项目文档
- 🔄 **持续优化**：AI 根据需求不断改进代码质量

## 核心特性

- 🚀 **现代化 CLI**：基于 Typer + Prompt Toolkit 的交互式命令行界面
- 🎯 **智能补全**：支持命令、参数和路径的自动补全
- 📊 **高效扫描**：快速扫描大目录，智能识别重复文件
- 🔍 **多种查询**：支持模式匹配、路径查询、哈希查询
- 📤 **灵活导出**：支持 CSV、JSON 和详细报告格式
- ⚙️ **配置管理**：可配置扫描范围和排除规则
- 💾 **数据库支持**：SQLite 数据库存储，支持备份和恢复
- 🧹 **安全清理**：支持模拟运行，避免误删文件

## 安装

### 环境要求

- Python 3.13+
- pip 包管理器

### 安装依赖

```bash
pip install prompt-toolkit typer rich
```

## 🚀 快速上手指南

### 第一步：扫描目录

首先，您需要扫描目标目录以建立文件索引：

```bash
# 扫描单个目录
python main.py index scan D:\Downloads

# 扫描多个目录
python main.py index scan D:\Downloads E:\Videos
```

扫描完成后，系统会自动识别大小相同的文件并创建重复文件组。

### 第二步：查看重复文件组

查看扫描结果，了解重复文件的情况：

```bash
# 查看占用空间最大的前 20 组
python main.py show groups

# 查看更多组
python main.py show groups --page 1 --page-size 30

# 按文件数量排序
python main.py show groups --sort count
```

### 第三步：计算哈希值（重要！）

⚠️ **关键步骤**：在清理重复文件之前，**必须**先计算文件哈希值！

**为什么需要计算哈希值？**

- 扫描阶段仅根据文件大小识别重复，可能存在误判
- 哈希值计算可以确认文件内容完全相同
- **只有计算了哈希值的组才能进行实质性的清理操作**
- 未计算哈希值的组只能查看，不能删除

```bash
# 计算所有重复文件组的哈希值
python main.py hash calc

# 仅计算新增文件的哈希值（更快）
python main.py hash calc --mode new

# 强制重新计算所有哈希值
python main.py hash calc --mode force
```

### 第四步：验证结果

计算完成后，再次查看重复文件组，确认哈希值状态：

```bash
# 查看已确认的重复文件组
python main.py show groups

# 查看详细信息
python main.py show groups --detail <组ID>
```

### 第五步：安全清理

确认无误后，可以进行清理操作：

```bash
# 模拟运行（推荐先执行）
python main.py clean clean --dryrun --keep-newest

# 生成清理脚本（安全方式）
python main.py clean script cleanup.bat

# 执行清理（谨慎操作）
python main.py clean clean --keep-newest
```

## ⚠️ 重要安全提示

### 哈希计算的重要性

**在清理重复文件之前，必须先计算哈希值！**

| 阶段 | 方法 | 准确性 | 是否可清理 |
|------|------|--------|-----------|
| 扫描阶段 | 文件大小 | 中等 | ❌ 不可清理 |
| 哈希计算 | 文件内容哈希 | 100% | ✅ 可以清理 |

**原因：**
1. **扫描阶段**：仅根据文件大小识别重复，可能将不同内容但大小相同的文件误判为重复
2. **哈希计算**：通过计算文件内容的哈希值，确保文件内容完全相同，避免误删
3. **安全机制**：系统只允许清理已确认哈希值的重复文件组

### 清理前的检查清单

- [ ] 已完成目录扫描
- [ ] 已查看重复文件组列表
- [ ] **已计算所有目标组的哈希值**
- [ ] 已验证哈希值状态为"已确认"
- [ ] 已使用 `--dryrun` 模拟运行
- [ ] 已备份重要数据

## 命令列表

### 📁 index - 扫描与索引
- `scan <path>` - 扫描指定路径
- `import <csv>` - 从 CSV 文件导入文件列表
- `rebuild` - 重建重复文件组
- `clear <pattern>` - 清除索引数据（支持通配符和路径）

### 📊 show - 显示数据
- `groups` - 显示重复文件组列表（支持分页、排序、过滤）
  - `--sort size/count/path/ext/hash` - 排序方式
  - `--page N` - 页码
  - `--page-size N` - 每页数量
  - `--disk C:` - 按磁盘过滤
  - `--min-size 100MB` - 最小文件大小
  - `--extension .mp4` - 按扩展名过滤
  - `--detail <ID>` - 查看详细信息
- `files <pattern|path>` - 查询文件（支持路径或模式）
- `hash <hash>` - 显示指定哈希值的所有文件
- `stats` - 显示统计分析

### 🔐 hash - 哈希计算
- `calc` - 计算文件哈希值
  - `--mode default` - 默认模式，计算未计算哈希的文件
  - `--mode new` - 仅计算从未计算过哈希的文件
  - `--mode force` - 强制重新计算所有文件
  - `--group-ids <IDs>` - 指定要计算的组ID
- `status` - 查看哈希计算状态
- `verify` - 验证哈希值完整性
- `clear` - 清除哈希数据
- `backup <path>` - 备份哈希数据
- `restore <path>` - 恢复哈希数据

### 📤 export - 导出
- `csv <path>` - 导出为 CSV 格式
- `json <path>` - 导出为 JSON 格式
- `report <path>` - 生成详细报告

### ⚙️ config - 配置
- `limit <path>` - 设置扫描范围限制
- `limit clear` - 解除范围限制
- `exclude add <pattern>` - 添加排除模式
- `exclude list` - 查看排除模式
- `exclude remove <pattern>` - 移除排除模式

### 💾 db - 数据库
- `check` - 检查数据库
- `optimize` - 优化数据库
- `backup <path>` - 备份数据库
- `restore <path>` - 恢复数据库
- `init` - 重建数据库

### 🧹 clean - 清理
- `clean` - 清理重复文件（仅限已确认哈希值的组）
  - `--dryrun` - 模拟运行，不实际删除
  - `--keep-newest` - 保留最新文件
  - `--keep-path <path>` - 保留指定路径的文件
- `script <path>` - 生成清理脚本

## 使用示例

### 1. 完整工作流程

```bash
# 步骤 1: 扫描目录
python main.py index scan D:\Downloads

# 步骤 2: 查看重复文件组
python main.py show groups --top 20

# 步骤 3: 计算哈希值（重要！）
python main.py hash calc

# 步骤 4: 验证结果
python main.py show groups

# 步骤 5: 模拟清理
python main.py clean clean --dryrun --keep-newest

# 步骤 6: 执行清理
python main.py clean clean --keep-newest
```

### 2. 高级查询

```bash
# 查看特定磁盘的重复文件
python main.py show groups --disk C:

# 查看大文件重复组
python main.py show groups --min-size 100MB

# 查看特定扩展名的重复文件
python main.py show groups --extension .mp4

# 分页查看
python main.py show groups --page 2 --page-size 10
```

### 3. 按需计算哈希

```bash
# 仅计算特定组的哈希值
python main.py hash calc --group-ids 123,456,789

# 仅计算新增文件
python main.py hash calc --mode new

# 强制重新计算
python main.py hash calc --mode force
```

### 4. 导出分析结果

```bash
# 导出为 CSV
python main.py export csv duplicates.csv

# 导出为 JSON
python main.py export json duplicates.json

# 生成详细报告
python main.py export report report.txt
```

### 5. 安全清理

```bash
# 模拟运行（推荐先执行）
python main.py clean clean --dryrun --keep-newest

# 生成清理脚本（安全方式）
python main.py clean script cleanup.bat

# 执行清理（谨慎操作）
python main.py clean clean --keep-newest
```

## AI 编码历程

本项目展示了 AI 在软件开发全流程中的应用：

### 第一阶段：需求分析与架构设计
- AI 分析了重复文件分析的核心需求
- 设计了模块化的项目结构
- 规划了数据库表结构

### 第二阶段：核心功能实现
- AI 实现了文件扫描、哈希计算等核心算法
- 编写了数据库操作和查询逻辑
- 实现了重复文件检测算法

### 第三阶段：CLI 界面开发
- AI 使用 Typer 构建了命令系统
- 集成了 Prompt Toolkit 实现交互式界面
- 实现了智能补全功能

### 第四阶段：优化与完善
- AI 优化了性能和内存使用
- 添加了错误处理和用户提示
- 完善了文档和示例

### 第五阶段：测试与发布
- AI 进行了功能测试和调试
- 准备了 GitHub 仓库
- 编写了完整的 README 文档

## 项目结构

```
duplicate_files/
├── main.py              # 主程序入口
├── commands/            # 命令模块
│   ├── index.py        # 扫描与索引命令
│   ├── show.py        # 显示数据命令
│   ├── hash.py        # 哈希计算命令
│   ├── export.py      # 导出命令
│   ├── config.py      # 配置命令
│   ├── db.py         # 数据库命令
│   └── clean.py      # 清理命令
├── core/               # 核心模块
│   ├── file_scanner.py # 文件扫描器
│   ├── hash_calculator.py # 哈希计算器
│   ├── index_manager.py # 索引管理器
│   └── config_manager.py # 配置管理器
├── tests/              # 测试模块
│   ├── test_commands/ # 命令测试
│   ├── test_core/     # 核心模块测试
│   └── test_autocomplete/ # 自动补全测试
└── README.md           # 项目文档
```

## 技术栈

- **Python 3.13+** - 主要编程语言
- **Typer** - 命令行界面框架
- **Prompt Toolkit** - 交互式命令行和补全
- **Rich** - 终端格式化输出
- **SQLite** - 数据库存储
- **Standard Library** - 标准库（os, hashlib, sqlite3 等）

## 最佳实践

### 1. 工作流程建议

1. **首次使用**：先扫描小目录测试功能
2. **大规模扫描**：分批扫描，避免一次性扫描过多文件
3. **哈希计算**：优先计算大文件组的哈希值
4. **清理操作**：始终先使用 `--dryrun` 模拟运行

### 2. 性能优化建议

- 使用 `--mode new` 仅计算新增文件哈希
- 定期使用 `db optimize` 优化数据库
- 使用 `config limit` 限制扫描范围
- 使用 `config exclude` 排除不需要的文件

### 3. 安全建议

- **始终先计算哈希值再清理**
- 定期备份数据库：`db backup backup.db`
- 使用 `--dryrun` 模拟清理操作
- 生成清理脚本而不是直接删除

## 常见问题

### Q: 为什么扫描后不能直接清理重复文件？
A: 扫描阶段仅根据文件大小识别重复，可能存在误判。必须先计算哈希值确认文件内容完全相同，才能安全清理。

### Q: 哈希计算需要多长时间？
A: 取决于文件大小和数量。大文件计算较慢，建议使用 `--mode new` 仅计算新增文件。

### Q: 如何查看哪些组已计算哈希值？
A: 使用 `show groups` 命令，哈希状态列会显示"✅ 已确认"或"⏳ 未确认"。

### Q: 清理操作是否可逆？
A: 文件删除是不可逆的！建议使用 `--dryrun` 模拟运行，或生成清理脚本手动执行。

## 贡献

本项目是一个 AI 编码的示例项目，主要用于展示 AI 在软件开发中的能力。欢迎提出建议和反馈！

## 许可证

MIT License

## 致谢

感谢所有参与本项目开发和测试的 AI 助手！

---

**🤖 Made with 100% AI Code**
