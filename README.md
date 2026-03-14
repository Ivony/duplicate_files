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
pip install prompt-toolkit typer
```

## 使用方法

### 交互式模式（推荐）

启动交互式命令行界面，支持自动补全：

```bash
python main.py
```

在交互式界面中：
- 输入命令时按 `Tab` 键查看补全建议
- 使用 `↑` `↓` 键浏览历史命令
- 输入 `help` 查看帮助信息
- 输入 `exit` 退出程序

### 命令行模式

直接执行命令：

```bash
# 查看帮助
python main.py --help

# 查看具体命令帮助
python main.py index --help

# 扫描目录
python main.py index scan D:\Downloads

# 查看重复文件组
python main.py show groups --top 10

# 导出分析结果
python main.py export csv analysis.csv
```

## 命令列表

### 📁 index - 扫描与索引
- `scan <path>` - 扫描指定路径
- `import <csv>` - 从 CSV 文件导入文件列表
- `rebuild` - 重建重复文件组
- `clear <pattern>` - 清除索引数据（支持通配符和路径）

### 📊 show - 显示数据
- `groups` - 显示重复文件组列表
- `files <pattern|path>` - 查询文件（支持路径或模式）
- `hash <hash>` - 显示指定哈希值的所有文件
- `stats` - 显示统计分析

### 🔐 hash - 哈希计算
- `calc` - 计算文件哈希值
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
- `clean` - 清理重复文件
- `script <path>` - 生成清理脚本

## 使用示例

### 1. 扫描目录并分析重复文件

```bash
# 交互式模式
python main.py
> index scan D:\Downloads

# 命令行模式
python main.py index scan D:\Downloads
```

### 2. 查看重复文件组

```bash
# 查看占用空间最大的前 10 组
python main.py show groups --top 10

# 查看文件数量最多的前 10 组
python main.py show groups --top 10 --by-count
```

### 3. 查询特定路径的文件

```bash
# 查询特定目录下的文件
python main.py show files D:\Downloads

# 使用通配符查询
python main.py show files "*.pdf"
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

### 5. 安全清理重复文件

```bash
# 模拟运行（不实际删除）
python main.py clean clean --dryrun --keep-newest

# 生成清理脚本
python main.py clean script cleanup.bat

# 执行清理
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
├── src/                # 核心模块
│   ├── file_scanner.py # 文件扫描器
│   ├── hash_calculator.py # 哈希计算器
│   ├── duplicate_finder.py # 重复文件查找器
│   └── database.py    # 数据库操作
└── README.md           # 项目文档
```

## 技术栈

- **Python 3.13+** - 主要编程语言
- **Typer** - 命令行界面框架
- **Prompt Toolkit** - 交互式命令行和补全
- **SQLite** - 数据库存储
- **Standard Library** - 标准库（os, hashlib, sqlite3 等）

## 贡献

本项目是一个 AI 编码的示例项目，主要用于展示 AI 在软件开发中的能力。欢迎提出建议和反馈！

## 许可证

MIT License

## 致谢

感谢所有参与本项目开发和测试的 AI 助手！

---

**🤖 Made with 100% AI Code**
