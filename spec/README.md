# OpenClaw Spec - Document Index

> 版本：2.0.0 | 最后更新：2026-02-03
>
> Project A: Secure Skill Lifecycle Manager

## 📁 文档结构

```
spec/
├── README.md              # 本文件 - 文档集入口
├── overview.md            # 项目目标、非目标、术语定义、分支策略
├── architecture.md        # 模块架构与数据流
├── security.md            # 威胁模型、AST Gate、沙盒策略
├── acceptance.md          # 验收标准与 DoD
├── gsd_tasks.md           # 8 步原子任务（执行计划）
├── iteration.md           # 迭代协议（开发中如何修改 spec）
├── roadmap_b.md           # Project B 方向性设计（不在 MVP 范围）
├── contracts/
│   └── skill_schema.json  # 技能契约 JSON Schema
├── eval/
│   ├── test_cases.md      # 评测用例设计
│   └── redteam.md         # 安全对抗测试详细设计
└── changes/               # 变更记录目录（开发中创建）
    └── TEMPLATE.md        # 变更模板
```

## 🚀 快速开始（给 Claude Code）

### 1. 阅读顺序

1. **overview.md** — 项目范围、Project A/B 分期、分支策略
2. **architecture.md** — 模块划分和数据流
3. **security.md** — 安全要求（**关键！**）
4. **gsd_tasks.md** — 按任务顺序实现

### 2. 执行流程

```
所有开发在 dev 分支上顺序进行：

git checkout -b dev

Task 1: 初始化工程骨架 → 验证 → git commit
Task 2: Day Logger → 验证 → git commit
Task 3: 数据模型 → 验证 → git commit
Task 4: AST Gate → 验证 → git commit
Task 5: Docker 沙盒 → 验证 → git commit
Task 6: Night Evolver → 验证 → git commit
Task 7: Promote Gate → 验证 → git commit
Task 8: Rollback & Audit → 验证 → git commit

全部通过后：
git checkout main && git merge dev
```

### 3. 每个 Task 的执行模式

```
1. 阅读 Task 描述
2. 创建/修改文件
3. 运行验证命令
4. 检查 DoD
5. git commit -m "task-N: <描述>"
```

### 4. ⭐ 遇到问题时的迭代模式

**重要**：Spec 不是一成不变的。当实现过程中发现问题时：

```
发现问题 → 暂停实现 → 创建 spec/changes/NNN-xxx.md → 更新 spec → 继续实现
```

详见 `iteration.md`。

## ⚠️ 关键约束（必须遵守）

### 安全约束（security.md）

- **AST Gate 必须拦截**：
  - 所有非白名单的导入
  - `__import__`, `eval`, `exec`, `compile`
  - `getattr`, `setattr`, `delattr`
  - `globals`, `locals`, `vars`
  - `__subclasses__`, `__globals__`, `__code__` 等属性

- **Sandbox Runner 必须**：
  - 捕获 `BaseException`（包括 `SystemExit`）
  - 严格检查 `verify() is True`
  - 超时后 kill + cleanup

- **Docker 必须使用**：
  - `--network none`
  - `--read-only`
  - `--cap-drop ALL`
  - 资源限制

## 📋 验收命令速查

```bash
# 代码质量
ruff check .
pytest -q

# Day Mode
python -m src.day_logger --log data/runtime.log --out data/nightly_queue.json

# Night Mode
python -m src.night_evolver --queue data/nightly_queue.json --staging skills_staging --registry data/registry.json --provider mock

# Promotion
python -m src.promote --staging skills_staging --prod skills_prod --registry data/registry.json --eval-dir data/eval

# Rollback
python -m src.rollback --skill <n> --to <version> --registry data/registry.json
```

## 🔗 文档间引用关系

```
overview.md ──────────────────────────────────────┐
    │                                              │
    ▼                                              │
architecture.md ─────────────────┐                 │
    │                            │                 │
    │  ┌─────────────────────────┤                 │
    │  │                         │                 │
    ▼  ▼                         ▼                 │
security.md              gsd_tasks.md ◄────────────┤
    │                         │                    │
    │                         │                    │
    ▼                         ▼                    │
contracts/              acceptance.md ◄────────────┘
skill_schema.json            │
    │                        │
    └────────┬───────────────┘
             │
             ▼
         eval/
    test_cases.md
    redteam.md

roadmap_b.md ← 独立，仅参考 overview.md 和 architecture.md
```

## 📝 变更日志

### 2026-02-03 v2.0.0

- 明确 Project A / Project B 分期
- 简化为单 dev 分支开发（移除 worktree 方案）
- 新增 `roadmap_b.md`（Project B 方向性设计）
- 移除 worktree-setup.md 和 `setup-worktrees.sh`

### 2026-02-02 v1.0.0

- 初始版本
