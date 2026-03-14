# 重复文件分析工具测试方案

本文件夹包含重复文件分析工具的所有测试用例和测试配置。

## 文件夹结构

```
tests/
├── README.md                      # 本文档
├── conftest.py                    # 测试配置和fixtures
├── test_autocomplete/             # 自动补全测试
│   ├── README.md
│   ├── test_autocomplete.py
│   ├── test_path_completion.py
│   └── debug/
├── test_commands/                 # 命令行指令测试
│   ├── README.md
│   ├── test_index.py
│   ├── test_show.py
│   ├── test_hash.py
│   ├── test_export.py
│   ├── test_config.py
│   ├── test_db.py
│   ├── test_clean.py
│   └── test_main.py
├── test_core/                     # 核心模块测试
│   ├── README.md
│   ├── test_file_scanner.py
│   ├── test_hash_calculator.py
│   ├── test_index_manager.py
│   └── test_config_manager.py
└── utils/                         # 测试辅助工具
    └── test_helpers.py
```

## 测试目标

### 1. 功能完整性
- 确保所有命令行指令功能正确
- 确保所有核心模块功能正确
- 确保自动补全功能正确

### 2. 用户体验
- 确保命令行交互流畅
- 确保输出信息清晰准确
- 确保错误提示友好

### 3. 稳定性
- 确保边界情况处理正确
- 确保异常情况处理正确
- 确保长时间运行稳定

### 4. 性能
- 确保文件扫描性能良好
- 确保哈希计算性能良好
- 确保数据库操作性能良好

## 测试框架

**使用 pytest 作为测试框架**，原因如下：
- **强大的 fixture 系统**：适合管理测试环境，如临时文件、数据库连接等
- **丰富的插件生态**：支持测试覆盖率报告、参数化测试等
- **灵活的断言语法**：易于编写清晰的测试用例
- **良好的错误报告**：便于调试测试失败
- **支持测试发现**：自动找到测试文件和测试函数

## 测试依赖

```bash
pip install pytest pytest-cov pytest-mock
```

| 依赖 | 版本 | 描述 |
|------|------|------|
| pytest | 9.0+ | 测试框架 |
| pytest-cov | 7.0+ | 测试覆盖率 |
| pytest-mock | 3.15+ | Mock和Patch |

## 测试统计

| 测试类别 | 测试文件数 | 测试用例数 | 覆盖率目标 |
|---------|-----------|-----------|-----------|
| 自动补全测试 | 2 | 32 | 100% |
| 命令行指令测试 | 8 | 24 | 90% |
| 核心模块测试 | 4 | 20 | 95% |
| **总计** | **14** | **76** | **90%** |

## 快速开始

### 运行所有测试
```bash
# 运行所有测试
pytest

# 运行所有测试并显示详细输出
pytest -v

# 运行所有测试并生成覆盖率报告
pytest --cov=commands --cov-report=html
```

### 分类测试执行

#### 运行自动补全测试
```bash
pytest tests/test_autocomplete/ -v
```

#### 运行命令行指令测试
```bash
pytest tests/test_commands/ -v
```

#### 运行核心模块测试
```bash
pytest tests/test_core/ -v
```

## 测试策略

### 1. 测试金字塔

```
        /\
       /  \
      / E2E \        端到端测试 (少量)
     /--------\
    /  集成测试  \      集成测试 (适量)
   /--------------\
  /    单元测试      \    单元测试 (大量)
 /------------------\
```

- **单元测试**：测试单个函数和类的方法
- **集成测试**：测试模块间的交互
- **端到端测试**：测试完整的用户流程

### 2. 测试优先级

| 优先级 | 描述 | 示例 |
|-------|------|------|
| P0 | 核心功能 | 文件扫描、哈希计算 |
| P1 | 重要功能 | 命令行指令、配置管理 |
| P2 | 辅助功能 | 自动补全、帮助信息 |
| P3 | 边界情况 | 大文件、特殊字符 |

### 3. 测试环境隔离
- 使用临时目录和文件
- 使用内存数据库
- 模拟文件系统操作
- 模拟用户输入

## 测试工具

### 1. pytest框架
- **功能**：测试框架
- **特性**：fixture系统、参数化测试、插件生态
- **文档**：https://docs.pytest.org/

### 2. pytest-cov
- **功能**：测试覆盖率
- **特性**：HTML报告、终端报告、XML报告
- **文档**：https://pytest-cov.readthedocs.io/

### 3. pytest-mock
- **功能**：Mock和Patch
- **特性**：简洁的Mock API、自动unpatch
- **文档**：https://pytest-mock.readthedocs.io/

### 4. tempfile
- **功能**：临时文件和目录
- **特性**：自动清理、跨平台支持
- **文档**：https://docs.python.org/3/library/tempfile.html

## 测试最佳实践

### 1. 测试命名
- 使用描述性的测试名称
- 使用 `test_` 前缀
- 使用 `test_<功能>_<场景>` 格式

### 2. 测试结构
- 使用 AAA 模式（Arrange-Act-Assert）
- 保持测试简单明了
- 每个测试只验证一个功能

### 3. 测试隔离
- 每个测试独立运行
- 使用fixture管理测试环境
- 避免测试间的依赖

### 4. 测试数据
- 使用有意义的测试数据
- 覆盖边界情况
- 避免硬编码

### 5. 测试断言
- 使用清晰的断言消息
- 验证所有重要的结果
- 避免过度断言

## 测试覆盖率

### 生成覆盖率报告
```bash
# 生成HTML覆盖率报告
pytest --cov=commands --cov-report=html

# 生成终端覆盖率报告
pytest --cov=commands --cov-report=term

# 生成XML覆盖率报告（用于CI/CD）
pytest --cov=commands --cov-report=xml
```

### 查看覆盖率报告
```bash
# 在浏览器中打开HTML报告
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
xdg-open htmlcov/index.html  # Linux
```

## 测试维护

### 1. 测试更新
- 当添加新功能时，添加对应测试
- 当修改功能时，更新对应测试
- 当发现Bug时，添加回归测试

### 2. 测试审查
- 定期审查测试覆盖率
- 定期审查测试质量
- 定期清理冗余测试

### 3. 测试监控
- 在CI/CD中运行测试
- 监控测试通过率
- 监控测试执行时间

## 子文件夹文档

- [test_autocomplete/README.md](test_autocomplete/README.md) - 自动补全测试详情
- [test_commands/README.md](test_commands/README.md) - 命令行指令测试详情
- [test_core/README.md](test_core/README.md) - 核心模块测试详情

## 相关资源

- [pytest官方文档](https://docs.pytest.org/)
- [pytest最佳实践](https://docs.pytest.org/en/stable/best-practices.html)
- [pytest-cov文档](https://pytest-cov.readthedocs.io/)
- [Typer文档](https://typer.tiangolo.com/)
- [prompt_toolkit文档](https://python-prompt-toolkit.readthedocs.io/)

---

**最后更新**：2026-03-15
**版本**：3.0
**维护者**：重复文件分析工具团队
