# 重复文件分析工具

## 项目简介

这是一个使用 Python 开发的重复文件分析工具，用于扫描、分析和清理重复文件。

## 重构说明

本项目已使用 Prompt Toolkit + Typer 进行重构，提供了更加现代化和易用的命令行界面。

## 安装依赖

```bash
pip install prompt-toolkit typer
```

## 使用方法

### 命令行模式

直接执行命令：

```bash
# 查看帮助信息
python main.py --help

# 查看具体命令的帮助
python main.py index --help

# 执行具体命令
python main.py index scan D:\Downloads
python main.py show groups
python main.py clean --dryrun
```

### 交互式模式

启动交互式命令行界面：

```bash
python interactive.py
```

在交互式界面中，可以直接输入命令，支持命令补全和历史记录。

## 命令列表

### index 指令 - 扫描与索引
- `scan <path>` - 扫描指定路径，将文件放入files表
- `import <csv>` - 从CSV文件导入文件列表
- `rebuild` - 检查并清理索引文件，然后重建重复文件组
- `hash [group_id]` - 计算指定组或所有组的hash值
- `clear <type>` - 清除索引数据（files/hash/full）

### show 指令 - 显示数据
- `groups` - 显示重复文件组列表
- `files <pattern|path>` - 查询文件（支持路径或模式）
- `hash <hash>` - 显示指定哈希值的所有文件
- `stats` - 显示统计分析

### export 指令 - 导出
- `csv <path>` - 导出分析结果为CSV格式
- `json <path>` - 导出分析结果为JSON格式
- `report <path>` - 生成详细的重复文件报告

### config 指令 - 配置
- `limit <path>` - 设置检索范围限制
- `limit clear` - 解除检索范围限制
- `exclude add <pattern>` - 添加路径排除模式
- `exclude list` - 查看当前排除模式
- `exclude remove <pattern>` - 移除路径排除模式

### db 指令 - 数据库
- `check` - 检查数据库结构和数据
- `optimize` - 优化数据库性能
- `backup <path> [--hash-only]` - 备份数据库
- `restore <path> [--hash-only] [--merge]` - 恢复数据库
- `init [--force]` - 重建数据库结构

### clean 指令 - 清理
- `clean [选项] [排序策略]` - 清理重复文件

## 示例

1. 扫描目录并重建索引：
   ```bash
   python main.py index scan D:\Downloads
   ```

2. 查看重复文件组：
   ```bash
   python main.py show groups --top 10
   ```

3. 导出分析结果：
   ```bash
   python main.py export csv analysis.csv
   ```

4. 清理重复文件（模拟执行）：
   ```bash
   python main.py clean clean --dryrun --keep-newest
   ```
