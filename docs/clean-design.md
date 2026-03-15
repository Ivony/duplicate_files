# Clean 指令设计文档

## 概述

Clean 指令用于清理重复文件，支持删除和创建软链接两种操作方式，并提供灵活的选择和执行模式。

---

## 命令结构

```
clean <action> [options]
```

---

## Actions（子命令）

| Action | 说明 |
|--------|------|
| `delete` | 删除重复文件 |
| `link` | 创建软链接替换重复文件 |
| `interactive` | 进入交互式命令行界面（待实现） |

---

## 核心参数

### `--yes/-y`（自动选择开关）

控制是否需要人工选择保留文件。

| 情况 | 行为 |
|------|------|
| 无 `-y` | 需要人工选择保留哪个文件 |
| 有 `-y` | 自动按排序策略选择保留文件 |

### `--mode`（执行模式）

控制操作的执行时机。

| 模式 | 说明 |
|------|------|
| `immediate` | 选择后立即执行操作（默认） |
| `script` | 选择后生成脚本，由用户决定是否执行 |
| `summary` | 选择后不操作，最后汇总确认 |

---

## 排序策略（--strategy）

排序策略决定每组重复文件中保留哪个文件。

| 策略 | 说明 |
|------|------|
| `newest` | 保留最新修改的文件（默认） |
| `oldest` | 保留最旧修改的文件 |
| `longest-name` | 保留文件名最长的文件 |
| `shortest-name` | 保留文件名最短的文件 |
| `longest-path` | 保留路径最长的文件 |
| `shortest-path` | 保留路径最短的文件 |
| `deepest` | 保留目录层级最深的文件 |
| `shallowest` | 保留目录层级最浅的文件 |

---

## 通用选项

| 选项 | 说明 |
|------|------|
| `--yes, -y` | 自动选择保留文件 |
| `--mode <模式>` | 执行模式：immediate/script/summary |
| `--strategy <策略>` | 排序策略 |
| `--script <path>` | 脚本输出路径（--mode script 时使用） |
| `--group <IDs>` | 只处理指定组（逗号分隔） |
| `--min-size <size>` | 最小文件大小过滤 |
| `--max-size <size>` | 最大文件大小过滤 |
| `--extension <ext>` | 扩展名过滤 |
| `--disk <disk>` | 磁盘过滤 |

---

## delete 子命令

### 功能

删除重复文件，只保留每组中的一个文件。

### 命令示例

```bash
# 人工选择 + 立即执行
python main.py clean delete

# 人工选择 + 生成脚本
python main.py clean delete --mode script --script cleanup.bat

# 人工选择 + 汇总确认
python main.py clean delete --mode summary

# 自动选择 + 立即执行
python main.py clean delete --yes

# 自动选择 + 生成脚本
python main.py clean delete --yes --mode script --script cleanup.bat

# 自动选择 + 汇总确认
python main.py clean delete --yes --mode summary

# 带过滤条件
python main.py clean delete --yes --min-size 100MB --extension .mp4
```

### 执行流程

#### 模式 1: immediate（默认）

```
1. 获取符合条件的重复文件组
2. 对每个组：
   - 如果有 -y：自动按策略选择保留文件
   - 如果无 -y：显示组内文件，让用户选择保留哪个
3. 立即执行删除操作
4. 显示执行结果
```

#### 模式 2: script

```
1. 获取符合条件的重复文件组
2. 对每个组：
   - 如果有 -y：自动按策略选择保留文件
   - 如果无 -y：显示组内文件，让用户选择保留哪个
3. 生成脚本文件
4. 显示脚本路径
```

#### 模式 3: summary

```
1. 获取符合条件的重复文件组
2. 对每个组：
   - 如果有 -y：自动按策略选择保留文件
   - 如果无 -y：显示组内文件，让用户选择保留哪个
3. 显示汇总信息（组数、文件数、可释放空间）
4. 让用户选择：
   - [D] 立即删除
   - [S] 生成脚本
   - [C] 取消
```

---

## link 子命令

### 功能

删除重复文件并创建软链接指向保留的文件，释放空间的同时保持文件可访问。

### 命令示例

```bash
# 人工选择 + 立即执行
python main.py clean link

# 人工选择 + 生成脚本
python main.py clean link --mode script --script link.bat

# 人工选择 + 汇总确认
python main.py clean link --mode summary

# 自动选择 + 立即执行
python main.py clean link --yes

# 自动选择 + 生成脚本
python main.py clean link --yes --mode script --script link.bat

# 自动选择 + 汇总确认
python main.py clean link --yes --mode summary
```

### 执行流程

与 delete 子命令类似，但执行的是：
1. 删除重复文件
2. 创建软链接指向保留文件

### 软链接注意事项

- Windows 上创建软链接可能需要管理员权限
- 软链接使用绝对路径
- 如果源文件被移动或删除，软链接会失效

---

## interactive 子命令（待实现）

### 功能

进入专用的交互式命令行界面，提供更灵活的控制方式。

### 设计要点

- 独立的命令行界面
- 支持搜索、浏览、选择等操作
- 可以随时查看状态
- 可以随时执行或生成脚本

### 交互式命令（初步设计）

| 命令 | 说明 |
|------|------|
| `list [N]` | 列出前 N 组 |
| `search <条件>` | 搜索组 |
| `show <组ID>` | 显示组详情 |
| `keep <组ID> <序号>` | 选择保留文件 |
| `unkeep <组ID>` | 取消选择 |
| `strategy <策略>` | 批量选择 |
| `status` | 显示状态 |
| `execute delete` | 执行删除 |
| `execute link` | 执行软链接 |
| `script delete` | 生成删除脚本 |
| `script link` | 生成软链接脚本 |
| `clear` | 清除选择 |
| `exit` | 退出 |

---

## 模式对比表

| 命令 | 选择方式 | 执行方式 | 适用场景 |
|------|---------|---------|---------|
| `delete --yes` | 自动 | 立即执行 | 批量处理、确定策略 |
| `delete --yes --mode script` | 自动 | 生成脚本 | 需要检查脚本 |
| `delete --yes --mode summary` | 自动 | 汇总确认 | 需要最终确认 |
| `delete` | 人工 | 立即执行 | 边选边删 |
| `delete --mode script` | 人工 | 生成脚本 | 先选后检查 |
| `delete --mode summary` | 人工 | 汇总确认 | 先选后确认 |
| `link --yes` | 自动 | 立即执行 | 批量软链、确定策略 |
| `link --yes --mode script` | 自动 | 生成脚本 | 需要检查脚本 |
| `link --yes --mode summary` | 自动 | 汇总确认 | 需要最终确认 |
| `link` | 人工 | 立即执行 | 边选边链 |
| `link --mode script` | 人工 | 生成脚本 | 先选后检查 |
| `link --mode summary` | 人工 | 汇总确认 | 先选后确认 |
| `interactive` | 交互式 | 灵活控制 | 复杂场景、精细控制 |

---

## 安全机制

1. **哈希验证**：只处理已确认哈希值的重复文件组
2. **确认提示**：执行操作前需要用户确认（除非使用 --yes）
3. **脚本模式**：生成脚本供用户检查后再执行
4. **汇总模式**：选择完成后汇总显示，再次确认

---

## 实现计划

### 第一阶段
- [x] 设计文档
- [ ] 实现 delete 子命令
- [ ] 实现 link 子命令
- [ ] 测试验证

### 第二阶段
- [ ] 设计 interactive 模式详细界面
- [ ] 实现 interactive 子命令
- [ ] 测试验证

---

## 更新日志

- 2024-01-XX: 初版设计文档
