# OpenClaw - Project B Roadmap: Self-Evolving Agent

> 版本：0.1.0 (方向性设计，不在 MVP 范围内)
> 
> 前置条件：Project A 全部 8 个 Task 完成并通过验收

## 1. 目标

在 Project A 的安全管线之上，构建 Yunjue 风格的自进化智能体系统，使其能够：

1. **运行时感知能力缺口** — 不再依赖离线日志扫描，而是在任务执行中实时检测
2. **在线合成并验证工具** — 调用真实 LLM 生成技能，通过 Project A 管线验证后立即可用
3. **批量进化与去重** — 防止工具爆炸，将功能相似的工具合并为通用版本
4. **收敛度监控** — 量化工具库的成熟度，类比训练 loss 曲线

---

## 2. 架构增量

### 2.1 新增模块

```
src/
├── agent/                     # 新增：智能体运行时
│   ├── manager.py             # Manager Agent：任务路由与决策
│   ├── executor.py            # Executor Agent：调用已有技能执行任务
│   ├── developer.py           # Tool Developer Agent：合成新技能
│   └── router.py              # 路由逻辑：已有技能 vs 新建技能
├── evolution/                 # 新增：进化引擎
│   ├── batch_evolver.py       # 批量进化策略
│   ├── dedup.py               # 技能去重与合并（absorbing）
│   └── convergence.py         # 收敛度指标计算
├── llm/
│   ├── base.py                # 已有
│   ├── mock.py                # 已有
│   ├── anthropic.py           # 新增：Claude API 集成
│   └── openai.py              # 新增：OpenAI API 集成
└── ...existing modules...
```

### 2.2 数据流变化

```
Project A (离线管线):
  Day Log → Queue → Generate → AST Gate → Sandbox → Staging → Promote → Prod

Project B (在线闭环):
  Task → Manager → Router ─┬─ 已有技能 → Executor → Result
                           └─ 需要新技能 → Developer → [Project A 管线] → Executor → Result
                                              │
                                              ▼
                                    Batch Evolution (周期性)
                                         │
                                         ▼
                                    去重/合并/收敛监控
```

关键变化：**Project A 的管线从"每夜批量运行"变为"按需实时触发"**。安全门（AST Gate、Sandbox）不变，但执行时机从离线变为在线。

---

## 3. Yunjue 核心机制映射

### 3.1 Multi-Agent Architecture

| Yunjue 角色 | OpenClaw 对应 | 职责 |
|-------------|---------------|------|
| Manager | `agent/manager.py` | 接收任务、决定策略、分配执行 |
| Tool Developer | `agent/developer.py` | 调用 LLM 生成新技能，提交到 Project A 管线 |
| Executor | `agent/executor.py` | 加载 prod 技能执行任务，返回结果 |

### 3.2 Parallel Batch Evolution

```python
# evolution/batch_evolver.py 概念设计

class BatchEvolver:
    """
    周期性运行（每 N 个任务或每 T 时间）:
    1. 收集近期新增的 staging/prod 技能
    2. 计算技能间的功能相似度（embedding or 签名匹配）
    3. 将相似技能聚类
    4. 对每个聚类，调用 LLM 生成"合并版"通用技能
    5. 合并版通过 Project A 管线验证后替换原技能
    """
    
    def evolve_batch(self, recent_skills: list[str]) -> list[MergeProposal]:
        clusters = self.cluster_by_similarity(recent_skills)
        proposals = []
        for cluster in clusters:
            if len(cluster) >= 2:
                merged = self.llm.merge_skills(cluster)
                proposals.append(MergeProposal(sources=cluster, merged=merged))
        return proposals
```

### 3.3 Convergence Monitoring

```python
# evolution/convergence.py 概念设计

class ConvergenceMonitor:
    """
    追踪两个核心指标：
    
    1. Tool Reuse Rate（工具复用率）
       = 使用已有工具完成的任务数 / 总任务数
       趋近 1.0 表示工具库趋于收敛
    
    2. Novel Tool Rate（新工具生成率）
       = 需要新建工具的任务数 / 总任务数
       趋近 0.0 表示工具库趋于收敛
    
    类比：Tool Reuse Rate ≈ 1 - training loss
    """
    
    def compute(self, window: int = 100) -> ConvergenceMetrics:
        recent = self.task_log.last(window)
        reuse = sum(1 for t in recent if t.used_existing_tool) / len(recent)
        novel = sum(1 for t in recent if t.required_new_tool) / len(recent)
        return ConvergenceMetrics(reuse_rate=reuse, novel_rate=novel)
```

---

## 4. 预估 Task 分解（粗粒度）

| Task | 描述 | 依赖 |
|------|------|------|
| B1 | LLM Provider 真实实现（Anthropic/OpenAI） | Project A 完成 |
| B2 | Manager Agent + Router 基础框架 | B1 |
| B3 | Executor Agent — 加载 prod 技能并执行 | B2 |
| B4 | Developer Agent — 在线触发 Project A 管线 | B2, B3 |
| B5 | 端到端在线闭环测试 | B4 |
| B6 | Batch Evolution — 技能去重与合并 | B5 |
| B7 | Convergence Monitor — 指标计算与可视化 | B6 |
| B8 | Benchmark 评测（HLE / DeepSearchQA 子集） | B7 |

---

## 5. 开放问题（Project B 启动前需决策）

1. **LLM 选择**：Claude API vs OpenAI vs 本地模型？成本和延迟考量
2. **在线安全延迟**：AST Gate + Docker Sandbox 的端到端延迟是否可接受？是否需要"快速路径"（只做 AST Gate，跳过 Docker）用于低风险技能？
3. **去重策略**：基于代码 embedding 相似度？基于 manifest 签名？基于 LLM 判断？
4. **状态持久化**：Manager 的任务上下文如何跨轮次保持？
5. **评测基准**：是否直接跑 Yunjue 的 5 个 benchmark，还是定义自己的任务集？

---

## 6. 与 Project A 的接口约定

Project B 只通过以下接口与 Project A 交互：

```python
# Project A 暴露的接口（Project B 的唯一入口）

from src.security.ast_gate import ASTGate        # 静态检查
from src.sandbox.runner import SandboxRunner      # 沙盒验证
from src.registry import Registry                 # 技能注册表
from src.promote import promote_skill             # 晋升
from src.rollback import rollback_skill           # 回滚
from src.skill_loader import SkillLoader          # 加载 prod 技能
from src.llm.base import LLMProvider, SkillPackage  # LLM 接口
```

**约束**：Project B 不得绕过 Project A 的安全门。所有 LLM 生成的代码必须经过 AST Gate + Sandbox 验证才能进入 staging。
