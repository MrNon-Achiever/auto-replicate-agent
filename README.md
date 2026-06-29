<div align="center">

# 🤖 全自动复刻项目Agent

**GitHub Trending 热点项目 → AI 自动复刻 → 推送到你的仓库 → 通知到手机**

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![GitHub Actions](https://img.shields.io/badge/GitHub-Actions-2088FF?logo=github-actions&logoColor=white)](.github/workflows/clone-repo.yml)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](CONTRIBUTING.md)

**最终形态：用户只需在手机上点一个按钮，智能体自动完成代码复刻全流程。**

</div>

---

## 📋 目录

- [项目概述](#-项目概述)
- [功能特性](#-功能特性)
- [快速开始](#-快速开始)
- [配置说明](#-配置说明)
- [命令行用法](#-命令行用法)
- [多仓库支持](#-多仓库支持)
- [高性能模式](#-高性能模式)
- [复刻流程](#-复刻流程)
- [技术方案](#-技术方案)
- [项目结构](#-项目结构)
- [测试结果](#-测试结果)
- [实现计划](#-实现计划)
- [风险与应对](#-风险与应对)
- [贡献指南](#-贡献指南)
- [许可证](#-许可证)

---

## 📖 项目概述

构建一个全自动/半自动系统，实现：

```
GitHub Trending 热点项目获取
  → AI 智能体自动复刻简化版
  → 推送到自己的 GitHub 仓库
  → 通过聊天机器人通知用户
```

---

## ✨ 功能特性

### ✅ 已实现功能

| 功能 | 状态 | 说明 |
|------|------|------|
| **Agent Loop 核心框架** | ✅ | 工具调用循环、上下文管理、检查点机制 |
| **7个核心工具函数** | ✅ | `read_file` · `write_file` · `edit_file` · `delete_file` · `run_command` · `list_files` · `git_push` |
| **代码验证机制** | ✅ | Python/JS 语法检查、JSON 验证、依赖检查 |
| **自动修复循环** | ✅ | 最多 10 轮修复尝试，自动提取分析错误 |
| **LLM 集成** | ✅ | OpenAI 兼容 API、工具调用支持、上下文压缩 |
| **GitHub Actions 集成** | ✅ | 手动触发 workflow、自动上传结果、超时保护 |
| **多仓库支持** | ✅ | 自动按数字排序克隆多个仓库，保持对应关系 |

---

## 🚀 快速开始

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 文件填入配置

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行复刻
python main.py https://github.com/username/repo
```

---

## ⚙️ 配置说明

所有配置在 `.env` 文件中，复制 `.env.example` 后修改：

```env
# ── LLM 配置（必需） ──
OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# ── Agent 配置（可选） ──
MAX_ITERATIONS=20
MAX_FIX_ATTEMPTS=10
WORK_DIR=./work

# ── GitHub 配置（可选，用于推送） ──
GITHUB_TOKEN=your_github_token
GITHUB_USER=your_username

# ── 代理配置（可选） ──
# PROXY=http://127.0.0.1:7890
```

---

## 💻 命令行用法

### 复刻项目

```bash
python main.py <repo_url> [options]

参数:
  repo_url              要复刻的仓库 URL

选项:
  --work-dir WORK_DIR   工作目录 (默认: ./work)
```

### 清理工作目录

```bash
python cleanup.py                          # 清理 work 目录
python cleanup.py --force                  # 强制清理（不询问）
python cleanup.py --work-dir ./my_work     # 清理指定目录
python cleanup.py --list                   # 列出所有已克隆仓库
python cleanup.py --index 1                # 清理特定序号的仓库
python cleanup.py --index 1 --force        # 强制清理特定序号
```

### 推送到 GitHub

```bash
python push_to_github.py work/output_1        # 推送指定目录
python push_to_github.py --index 1            # 按序号推送（推荐）
python push_to_github.py --index 1 \          # 自定义仓库名
  --repo my-project --private --desc "我的项目"
python push_to_github.py --index 1 \          # 使用代理
  --proxy http://127.0.0.1:7890
```

### 多仓库示例

```bash
python main.py https://github.com/username/repo1  # 创建 target_repo_1 + output_1
python main.py https://github.com/username/repo2  # 创建 target_repo_2 + output_2
python main.py https://github.com/username/repo3  # 创建 target_repo_3 + output_3
```

---

## 📂 多仓库支持

本程序支持自动按数字排序克隆多个仓库，每次运行会自动分配新的序号：

<pre>
work/
├── target_repo_1/        # 第一个克隆的仓库
│   └── ...               # 原始项目文件
├── output_1/             # 第一个复刻的代码
│   ├── app.py
│   ├── requirements.txt
│   └── README.md
├── target_repo_2/        # 第二个克隆的仓库
│   └── ...
├── output_2/             # 第二个复刻的代码
│   ├── app.py
│   ├── requirements.txt
│   └── README.md
└── ...                   # 继续按数字排序
</pre>

**序号对应关系：**

| 目录 | 用途 |
|------|------|
| `target_repo_N` | 克隆的原始仓库 |
| `output_N` | LLM 生成的复刻代码 |
| 序号 N | 自动递增，保证对应关系 |

### 全栈应用结构

<pre>
work/
├── target_repo_1/
├── output_1/
│   ├── backend/
│   │   ├── app.py
│   │   ├── models.py
│   │   ├── routes.py
│   │   └── requirements.txt
│   ├── frontend/
│   │   ├── app.py              # Streamlit 入口
│   │   └── pages/
│   ├── README.md
│   └── start.sh
</pre>

---

## ⚡ 高性能模式

本项目采用**高性能模式**，使用真正的工具调用机制生成生产级别代码。

### 核心特性

| 特性 | 说明 |
|------|------|
| **深度分析** | 最多 30 轮工具调用，深入理解项目架构 |
| **高质量生成** | 最多 50 轮工具调用，生成生产级代码 |
| **严格验证** | 最多 20 轮修复尝试，确保代码质量 |
| **集成测试** | 自动执行集成测试，验证功能完整性 |

### 工具调用机制

1. **工具定义** — 7个核心工具：`read_file`, `write_file`, `edit_file`, `delete_file`, `run_command`, `list_files`, `git_push`
2. **工具调用循环**：
   - LLM 接收工具定义和上下文
   - LLM 决定调用哪个工具
   - 本地执行工具，返回结果
   - 循环直到任务完成

### 优势

- 🎯 **更准确** — LLM 主动获取需要的信息
- 🔄 **更灵活** — 按需调用不同工具
- ✅ **更可靠** — 工具执行结果真实可靠
- 🏆 **高质量** — 生产级代码，非演示版本

### 前端处理策略

| 原项目前端 | 复刻方案 |
|-----------|----------|
| Vue / React / Angular | 用 Streamlit 替代 |
| 纯 HTML / CSS / JS | 保留原样 |
| 无前端 | 根据需要添加 Streamlit |

---

## 📋 复刻流程

```
步骤 1: 克隆目标仓库 ── 自动分配序号 N
  └─ 克隆到 work/target_repo_N

步骤 2: 深度分析项目 ── 最多 30 轮工具调用
  └─ 识别技术栈 / 项目类型 / 核心功能

步骤 3: 规划复刻方案 ── 最多 30 轮工具调用
  └─ 确定技术栈 / 文件结构 / 启动方式

步骤 4: 生成完整代码 ── 最多 50 轮工具调用
  └─ 配置文件 / 后端 / 前端 / 启动脚本

步骤 5: 严格验证和修复 ── 最多 20 轮
  └─ 语法检查 / 依赖检查 / 运行测试

步骤 6: 集成测试
  └─ 测试后端启动 / 前端访问 / 核心功能

步骤 7: 清理无用文件
  └─ 删除 .md(除README) / .log / 规划文档

步骤 8: 推送到 GitHub
  └─ 自动创建仓库 / 推送代码 / 返回地址

步骤 9: 打包结果
  └─ 返回 output_N / target_repo_N / 序号 N
```

---

## 🧠 技术方案

### ✅ 方案优点

1. **架构清晰** — 分阶段实现，降低复杂度
2. **工具设计简洁** — 7个核心工具覆盖所有需求
3. **生成策略正确** — 逐文件生成 + 每步验证
4. **修复机制完善** — 自动修复循环确保成功率
5. **筛选标准明确** — 项目大小、语言、复杂度合理限制

### 🔧 补充技术细节

| 技术点 | 问题 | 解决方案 |
|--------|------|----------|
| **LLM 上下文管理** | 长对话上下文溢出 | 压缩/摘要机制 · 最大消息数限制 |
| **工具调用协议** | 工具调用格式不明确 | OpenAI Function Calling 格式 |
| **安全性设计** | 执行 LLM 生成命令有风险 | 命令白名单 · 路径越界检查 · 危险命令拒绝 |
| **代码验证深度** | 验证过于简单 | Python/JS/JSON 语法检查 · 依赖检查 |
| **检查点恢复** | 6小时超时导致进度丢失 | `.checkpoint.json` 保存状态 · 恢复执行 |
| **错误处理策略** | 错误信息利用不足 | 错误提取分析 · 自动修复循环 |
| **许可证处理** | 合规风险 | 注明来源 · 保留原作者信息和许可证 |

---

## 📁 项目结构

```
全自动复刻项目Agent/
├── README.md                  # 本文件
├── PROJECT_SUMMARY.md         # 项目总结
├── main.py                    # 主入口
├── cleanup.py                 # 清理脚本（支持多仓库）
├── push_to_github.py          # 手动推送到 GitHub
├── requirements.txt           # 依赖列表
├── .env.example               # 环境变量示例
├── test_agent.py              # 测试脚本
├── agent/
│   ├── __init__.py
│   ├── core.py                # Agent Loop 核心（支持多仓库）
│   ├── tools.py               # 5个工具函数
│   ├── context.py             # 上下文管理
│   ├── verifier.py            # 代码验证
│   └── llm.py                 # LLM 调用封装
├── .github/
│   └── workflows/
│       └── clone-repo.yml     # GitHub Actions workflow
└── work/                      # 工作目录
    ├── target_repo_1/         # 克隆的仓库
    ├── output_1/              # 复刻的代码
    ├── target_repo_2/
    ├── output_2/
    └── ...
```

---

## 📊 测试结果

所有核心功能测试通过 ✅

<details>
<summary>📈 查看详细测试输出</summary>

```
开始测试全自动复刻项目Agent...

=== 测试工具函数 ===
1. 测试写入文件...    ✓ 写入成功
2. 测试读取文件...    ✓ 读取成功
3. 测试列出文件...    ✓ 列出成功
4. 测试执行命令...    ✓ 执行成功
✅ 所有工具测试通过！

=== 测试代码验证器 ===
1. 测试Python文件验证...    ✓ Python验证成功
2. 测试JSON文件验证...      ✓ JSON验证成功
3. 测试语法错误检测...      ✓ 语法错误检测成功
✅ 所有验证器测试通过！

=== 测试上下文管理器 ===
1. 测试添加消息...          ✓ 添加成功
2. 测试获取API消息...       ✓ 获取成功
3. 测试上下文压缩...        ✓ 压缩成功
✅ 所有上下文管理器测试通过！

=== 测试复刻智能体 ===
1. 测试初始化...            ✓ 初始化成功
2. 测试项目类型检测...      ✓ 类型检测成功
✅ 所有智能体测试通过！

==================================================
✅ 所有测试通过！
==================================================
```

</details>

---

## 🗺️ 实现计划

| 阶段 | 状态 | 验证项 |
|------|------|--------|
| **第1步：Agent Loop 核心框架** | ✅ | 成功复刻一个简单 Python 项目 |
| **第2步：验证与修复机制** | ✅ | 故意引入错误，测试自动修复能力 |
| **第3步：GitHub Actions 集成** | ✅ | 通过 Actions 成功复刻并推送项目 |
| **第4步：安全与合规** | ⚠️ 许可证检测待完成 | 安全测试，确保无危险操作 |
| **第5步：Telegram Bot 交互** | ⏳ 待实现 | 端到端测试，从点击按钮到收到通知 |

---

## ⚠️ 风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| LLM 生成质量不稳定 | 复刻失败 | 多轮修复 + 失败重试 |
| Token 消耗过大 | 费用超支 | 设置上限 + 上下文压缩 |
| 6 小时超时 | 进度丢失 | 检查点机制 |
| 安全漏洞 | 系统受损 | 沙箱隔离 + 命令白名单 |
| 许可证违规 | 法律风险 | 自动检测 + 保留声明 |

### 预期成果

- **成功率**：简单项目（<500KB，纯 Python/JS）预期 **60-80%**
- **耗时**：单项目复刻预计 **10-30 分钟**
- **成本**：单项目预计消耗 **$0.5-2.0**（取决于修复轮数）

---

## 👥 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. **Fork** 本仓库
2. 创建功能分支：`git checkout -b feature/xxx`
3. 提交更改：`git commit -m 'Add feature xxx'`
4. 推送到分支：`git push origin feature/xxx`
5. 创建 **Pull Request**

---

## 📄 许可证

本项目基于 **MIT License** 开源。

---

<div align="center">

**如有问题或建议，请提交 [Issue](https://github.com/auto-replicate-agent/issues) 或 Pull Request。**

</div>
