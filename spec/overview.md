# OpenClaw - Overview

> 版本：2.0.0 | 最后更新：2026-02-03

## 1. 项目定位

OpenClaw 分两阶段交付：

| 阶段 | 代号 | 交付物 | 依赖 |
|------|------|--------|------|
| **Project A** | Secure Skill Lifecycle Manager | 可验证、可回滚、零信任的技能 CI/CD 管线 | 无 |
| **Project B** | Self-Evolving Agent | Yunjue 风格的多智能体运行时 + 批量进化 + 收敛监控 | Project A |

本文档集覆盖 **Project A** 的完整规格。Project B 的设计见 `roadmap_b.md`（仅方向性，不在 MVP 范围内）。

---

## 2. Project A 目标（MVP Scope）

### 2.1 Day Mode
- 从运行日志中结构化提取缺失能力（`[MISSING: ...]`）
- 写入 `data/nightly_queue.json`

### 2.2 Night Mode（SVM Pipeline）
1. 读取队列
2. 生成候选技能（MVP 使用 `MockLLM`，真实 LLM 作为可插拔 provider）
3. 静态安全门（AST/规则扫描）
4. Docker 沙盒验证（`verify()` + `pytest`）
5. 进入 staging（`skills_staging/`）并写入 `registry.json`

### 2.3 Promotion
- 满足 gate 后晋升到 prod（`skills_prod/`）
- 保留旧版本，支持回滚

### 2.4 评测集
- `replay/`：真实失败样本
- `regression/`：历史能力回归
- `redteam/`：安全对抗

---

## 3. 非目标（Project A 不做）

| 非目标 | 归属 |
|--------|------|
| 运行时智能体调度（Manager/Executor） | Project B |
| 批量进化与工具去重（Parallel Batch Evolution） | Project B |
| 收敛度监控指标 | Project B |
| 真实 LLM 集成 | Project B |
| 多机分布式执行 | 未规划 |
| 自动依赖下载 | 安全风险，不做 |
| GUI/Web 界面 | 未规划 |

---

## 4. 术语表

| 术语 | 定义 |
|------|------|
| **Day Mode** | 系统正常运行模式，记录缺失能力到队列 |
| **Night Mode** | 离线进化模式，生成并验证新技能 |
| **Skill** | 一个独立的能力单元，包含 `skill.py` + `skill.json` + `tests/` |
| **Staging** | 技能暂存区，通过初步验证但未进入生产 |
| **Prod** | 生产技能区，线上只加载这里的技能 |
| **Gate** | 晋升门槛，必须通过才能进入下一阶段 |
| **Registry** | 技能注册表，记录版本、状态、hash、验证结果 |
| **SVM** | Skill Version Management，技能版本管理 |
| **Manifest** | 技能元数据文件 `skill.json` |
| **MockLLM** | 用于测试的模拟 LLM，返回预定义的技能代码 |
| **Allowlist** | 允许使用的 Python 包白名单 |
| **AST Gate** | 基于抽象语法树的静态安全检查 |
| **Sandbox Runner** | Docker 容器内的技能执行器 |

---

## 5. 成功标准

Project A 完成的定义：

1. **闭环可运行**：Day logger → Night evolver → Promote → Rollback 全流程可执行
2. **安全可验证**：任意候选技能无法通过已知绕过手法（SystemExit、__import__、getattr 等）
3. **可追溯**：Registry 记录完整的版本历史、hash、验证结果
4. **可回滚**：任意时刻可回退到历史版本
5. **可复现**：相同输入产生相同输出（依赖锁定、评测数据固定）
6. **可扩展**：LLM Provider 接口清晰，Project B 可直接对接

---

## 6. 约束与假设

### 6.1 约束
- Python 3.11+
- Docker 可用（用于沙盒）
- 单机运行
- 离线模式（无外部 API 依赖）

### 6.2 假设
- 开发者有 Docker 权限
- 技能粒度适中（单一职责，可独立测试）
- 评测数据可预先准备（不依赖实时数据）

---

## 7. 分支策略（简化）

MVP 使用**单 dev 分支**开发：

```
main          稳定版本，合并点
└── dev       所有 Task 1-8 顺序开发

每个 Task 完成后：
  dev 上 commit → 全部完成后 merge 到 main
```

不使用 worktree、不使用多分支并行。原因：
- 8 个 Task 存在严格顺序依赖
- 单人开发无并行收益
- 减少合并冲突和上下文切换开销
