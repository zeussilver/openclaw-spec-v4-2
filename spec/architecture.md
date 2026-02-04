# OpenClaw Project A - Architecture

> 版本：2.0.0 | 最后更新：2026-02-03
>
> 范围：Project A (Secure Skill Lifecycle Manager)

## 1. 目录结构

```
openclaw/
├── src/
│   ├── __init__.py
│   ├── day_logger.py       # Day Mode: 日志解析 → 队列
│   ├── night_evolver.py    # Night Mode: 生成 → 验证 → staging
│   ├── promote.py          # Staging → Prod 晋升
│   ├── rollback.py         # 版本回滚
│   ├── registry.py         # Registry 数据模型与操作
│   ├── skill_loader.py     # 技能加载器（生产使用）
│   ├── security/
│   │   ├── __init__.py
│   │   ├── ast_gate.py     # AST 静态安全检查
│   │   └── policy.py       # 安全策略配置
│   ├── sandbox/
│   │   ├── __init__.py
│   │   ├── runner.py       # Docker 沙盒执行器
│   │   └── harness.py      # 容器内执行入口
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py         # LLM Provider 接口
│   │   └── mock.py         # MockLLM 实现
│   └── eval/
│       ├── __init__.py
│       └── gate.py         # 评测 gate 执行器
├── skills/                  # 内置基础技能（只读，随代码发布）
│   └── text_echo/
│       ├── skill.py
│       ├── skill.json
│       └── tests/
├── skills_staging/          # Night 产物暂存区
├── skills_prod/             # 生产技能区
├── data/
│   ├── nightly_queue.json   # 缺失能力队列
│   ├── registry.json        # 技能注册表
│   └── eval/
│       ├── replay/          # 真实失败样本
│       ├── regression/      # 回归测试用例
│       └── redteam/         # 安全对抗用例
├── docker/
│   ├── Dockerfile.sandbox   # 沙盒基础镜像
│   └── entrypoint.sh
├── spec/                    # 本文档目录
├── tests/                   # 系统级测试
├── pyproject.toml
└── uv.lock                  # 依赖锁文件
```

---

## 2. 模块职责

### 2.1 Day Mode 模块

#### `day_logger.py`
- **输入**：运行时日志文件（包含 `[MISSING: ...]` 标记）
- **输出**：`data/nightly_queue.json`
- **职责**：
  - 解析日志提取缺失能力描述
  - 去重（相同能力不重复入队）
  - 记录首次出现时间、出现次数

```python
# 队列条目结构
{
    "id": "uuid",
    "capability": "convert CSV to JSON with schema validation",
    "first_seen": "2026-02-01T10:30:00Z",
    "occurrences": 3,
    "context": "user requested CSV parsing with strict types",
    "status": "pending"  # pending | processing | completed | failed
}
```

### 2.2 Night Mode 模块

#### `night_evolver.py`
- **输入**：`nightly_queue.json`
- **输出**：`skills_staging/<skill>/`、更新 `registry.json`
- **职责**：
  1. 读取 pending 队列条目
  2. 调用 LLM Provider 生成候选技能
  3. 调用 AST Gate 静态检查
  4. 调用 Sandbox Runner 运行验证
  5. 通过后写入 staging 并更新 registry

#### `llm/mock.py` (MockLLM)
- **输入**：能力描述
- **输出**：技能包（`skill.py` + `skill.json` + `tests/`）
- **职责**：返回预定义的技能代码用于测试流程

#### `llm/base.py` (LLMProvider Interface)
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class SkillPackage:
    name: str
    code: str           # skill.py 内容
    manifest: dict      # skill.json 内容
    tests: list[str]    # 测试文件内容列表

class LLMProvider(ABC):
    @abstractmethod
    def generate_skill(self, capability: str, context: str) -> SkillPackage:
        """根据能力描述生成技能包"""
        pass
```

### 2.3 Security 模块

#### `security/ast_gate.py`
- **输入**：Python 源代码字符串
- **输出**：`(passed: bool, violations: list[str])`
- **职责**：
  - 检查禁止的导入（顶层模块白名单）
  - 检查禁止的调用（`__import__`, `eval`, `exec` 等）
  - 检查危险属性访问（`__subclasses__`, `__globals__` 等）
  - 检查路径穿越模式

#### `security/policy.py`
```python
# 顶层模块白名单（只允许这些）
ALLOWED_TOP_LEVEL_MODULES = frozenset({
    "json", "re", "pathlib", "datetime", "typing",
    "collections", "itertools", "functools", "math",
    "decimal", "fractions", "statistics", "random",
    "hashlib", "base64", "urllib", "dataclasses",
    "enum", "copy", "pprint", "textwrap", "string",
})

# 禁止的函数调用
FORBIDDEN_CALLS = frozenset({
    "__import__", "eval", "exec", "compile",
    "open", "input", "breakpoint",
    "getattr", "setattr", "delattr",
    "globals", "locals", "vars",
})

# 禁止的属性访问
FORBIDDEN_ATTRIBUTES = frozenset({
    "__subclasses__", "__bases__", "__mro__",
    "__globals__", "__code__", "__builtins__",
    "__import__", "__loader__", "__spec__",
})
```

### 2.4 Sandbox 模块

#### `sandbox/runner.py`
- **输入**：技能包路径
- **输出**：`(passed: bool, logs: str, metrics: dict)`
- **职责**：
  - 构建/启动 Docker 容器
  - 挂载技能文件（只读）
  - 执行 `harness.py`
  - 捕获输出并判定结果
  - 超时处理与清理

#### `sandbox/harness.py`（容器内执行）
- **职责**：
  - 导入技能模块
  - 执行 `verify()` 并检查返回值（必须 `is True`）
  - 执行 pytest
  - 输出 `VERIFICATION_SUCCESS` 或错误信息

### 2.5 Promotion 模块

#### `promote.py`
- **输入**：staging 技能名、registry
- **输出**：复制到 `skills_prod/`、更新 registry
- **职责**：
  1. 执行 Promote Gate（replay/regression/redteam）
  2. 全部通过后复制到 prod
  3. 更新 registry 的 prod 指针

#### `rollback.py`
- **输入**：技能名、目标版本
- **输出**：更新 registry
- **职责**：
  - 验证目标版本存在
  - 切换 prod 指针到目标版本
  - 标记当前版本为 disabled（不删除）

### 2.6 Registry 模块

#### `registry.py`
```python
@dataclass
class SkillVersion:
    version: str
    code_hash: str
    manifest_hash: str
    created_at: str
    status: str  # staging | prod | disabled
    validation_result: dict  # gate 通过情况

@dataclass  
class SkillEntry:
    name: str
    current_prod: str | None      # 当前生产版本
    current_staging: str | None   # 当前 staging 版本
    versions: dict[str, SkillVersion]
    
class Registry:
    def load(self, path: Path) -> dict[str, SkillEntry]: ...
    def save(self, path: Path) -> None: ...
    def add_staging(self, skill: SkillEntry, version: SkillVersion) -> None: ...
    def promote(self, name: str, version: str) -> None: ...
    def rollback(self, name: str, target_version: str) -> None: ...
```

---

## 3. 数据流

```
┌─────────────────────────────────────────────────────────────────────┐
│                           DAY MODE                                   │
│  Runtime Log ──► day_logger ──► nightly_queue.json                  │
│  [MISSING: ...]                 {capability, context, status}       │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          NIGHT MODE                                  │
│                                                                      │
│  nightly_queue.json                                                  │
│         │                                                            │
│         ▼                                                            │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐      │
│  │ LLMProvider │───►│  AST Gate   │───►│  Sandbox Runner     │      │
│  │ (MockLLM)   │    │ (静态检查)   │    │  (Docker verify)    │      │
│  └─────────────┘    └─────────────┘    └─────────────────────┘      │
│         │                  │                     │                   │
│         │              violation?            passed?                 │
│         │                  │                     │                   │
│         │                  ▼                     ▼                   │
│         │              REJECT              skills_staging/           │
│         │                                        │                   │
│         └────────────────────────────────────────┼──────────────────│
│                                                  ▼                   │
│                                          registry.json               │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         PROMOTION                                    │
│                                                                      │
│  skills_staging/<skill>                                              │
│         │                                                            │
│         ▼                                                            │
│  ┌──────────────────────────────────────────┐                       │
│  │           Promote Gate                    │                       │
│  │  ┌─────────┐ ┌───────────┐ ┌─────────┐  │                       │
│  │  │ replay  │ │regression │ │ redteam │  │                       │
│  │  │  100%   │ │   ≥99%    │ │  100%   │  │                       │
│  │  └─────────┘ └───────────┘ └─────────┘  │                       │
│  └──────────────────────────────────────────┘                       │
│         │                                                            │
│     all pass?                                                        │
│         │                                                            │
│    ┌────┴────┐                                                       │
│    ▼         ▼                                                       │
│  REJECT   skills_prod/ ──► registry.json (prod pointer)             │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         ROLLBACK                                     │
│                                                                      │
│  rollback --skill <name> --to <version>                             │
│         │                                                            │
│         ▼                                                            │
│  registry.json: prod pointer ──► target version                      │
│                 current version ──► disabled                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. 接口契约

### 4.1 CLI 接口

```bash
# Day Mode
python -m src.day_logger \
    --log data/runtime.log \
    --out data/nightly_queue.json

# Night Mode
python -m src.night_evolver \
    --queue data/nightly_queue.json \
    --staging skills_staging \
    --registry data/registry.json \
    --provider mock  # mock | openai | anthropic

# Promote
python -m src.promote \
    --staging skills_staging \
    --prod skills_prod \
    --registry data/registry.json \
    --eval-dir data/eval

# Rollback
python -m src.rollback \
    --skill <name> \
    --to <version> \
    --registry data/registry.json
```

### 4.2 技能契约

见 `contracts/skill_schema.json`

---

## 5. 依赖关系

```
day_logger
    └── (无外部依赖，纯 Python)

night_evolver
    ├── llm.base / llm.mock
    ├── security.ast_gate
    ├── security.policy
    ├── sandbox.runner
    └── registry

promote
    ├── eval.gate
    └── registry

rollback
    └── registry

sandbox.runner
    └── docker (系统依赖)
```
