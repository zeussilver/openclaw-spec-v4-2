# OpenClaw Project A - GSD Tasks

> 版本：2.0.0 | 最后更新：2026-02-03
> 
> GSD = Get Stuff Done，原子任务驱动开发
>
> 范围：Project A (Secure Skill Lifecycle Manager) 全部 8 个 Task

## 开发原则

1. **每步独立可验证**：完成一步即可验证，不依赖后续步骤
2. **先测试后实现**：每步先写测试，再实现功能
3. **增量提交**：每步完成后提交，保持可回滚
4. **文档同步**：代码变更同步更新相关文档

## 分支工作流

```bash
# 开始开发
git checkout -b dev

# 每个 Task 完成后
git add .
git commit -m "task-N: <描述>"

# 全部完成后
git checkout main
git merge dev
git tag v2.0.0-project-a
```

---

## Task 1: 初始化工程骨架与依赖锁

### 目的
建立项目基础结构，锁定依赖版本，确保可复现。

### 改动文件
```
openclaw/
├── pyproject.toml          # 新建
├── uv.lock                  # 生成
├── .python-version          # 新建
├── .gitignore               # 新建
├── README.md                # 新建
├── src/
│   └── __init__.py          # 新建
├── tests/
│   ├── __init__.py          # 新建
│   └── conftest.py          # 新建
├── skills/                  # 新建（空目录保留）
├── skills_staging/          # 新建（空目录保留）
├── skills_prod/             # 新建（空目录保留）
├── data/
│   └── .gitkeep             # 新建
└── docker/
    └── .gitkeep             # 新建
```

### 实现步骤

```bash
# 1. 创建项目目录
mkdir -p openclaw && cd openclaw

# 2. 初始化 uv 项目
uv init --name openclaw --python 3.11

# 3. 添加依赖
uv add pydantic jsonschema pytest ruff

# 4. 添加开发依赖
uv add --dev pytest-cov mypy

# 5. 创建目录结构
mkdir -p src tests skills skills_staging skills_prod data docker

# 6. 创建 __init__.py
touch src/__init__.py tests/__init__.py

# 7. 创建 .gitkeep
touch skills/.gitkeep skills_staging/.gitkeep skills_prod/.gitkeep data/.gitkeep docker/.gitkeep

# 8. 创建 .gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
.venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.egg-info/
dist/
build/
data/nightly_queue.json
data/registry.json
data/audit.log
skills_staging/*
!skills_staging/.gitkeep
skills_prod/*
!skills_prod/.gitkeep
EOF
```

### 验证命令
```bash
ls -la src/ tests/ skills/ data/ docker/
cat uv.lock | head -20
pytest --version
```

### DoD
- [ ] `pyproject.toml` 存在且包含正确的依赖
- [ ] `uv.lock` 存在
- [ ] 目录结构完整
- [ ] `pytest --version` 成功运行

---

## Task 2: Day Logger（日志→队列）

### 目的
实现从运行日志中提取 `[MISSING: ...]` 标记并写入队列。

### 改动文件
```
src/
├── day_logger.py            # 新建
└── models/
    ├── __init__.py          # 新建
    └── queue.py             # 新建
tests/
└── test_day_logger.py       # 新建
```

### 实现步骤

1. 定义队列数据模型 (`models/queue.py`)
2. 实现日志解析器 (`day_logger.py`)
3. 实现去重与计数逻辑
4. 实现 CLI 入口

### 核心代码框架

```python
# src/models/queue.py
from pydantic import BaseModel
from datetime import datetime

class QueueItem(BaseModel):
    id: str
    capability: str
    first_seen: datetime
    occurrences: int = 1
    context: str = ""
    status: str = "pending"  # pending | processing | completed | failed

class NightlyQueue(BaseModel):
    items: list[QueueItem] = []
    updated_at: datetime = datetime.now()
```

```python
# src/day_logger.py
import re
import json
import uuid
from pathlib import Path
from datetime import datetime
from .models.queue import QueueItem, NightlyQueue

MISSING_PATTERN = re.compile(r'\[MISSING:\s*(.+?)\]')

def parse_log(log_path: Path) -> list[str]:
    """从日志文件提取所有 MISSING 能力描述"""
    capabilities = []
    with open(log_path) as f:
        for line in f:
            match = MISSING_PATTERN.search(line)
            if match:
                capabilities.append(match.group(1).strip())
    return capabilities

def build_queue(capabilities: list[str], existing: NightlyQueue | None = None) -> NightlyQueue:
    """构建去重后的队列，合并已有队列"""
    # 实现去重和计数逻辑
    ...

def main():
    """CLI 入口"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--log', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    ...
```

### 验证命令
```bash
pytest tests/test_day_logger.py -v

echo '[MISSING: test capability]' > /tmp/test.log
python -m src.day_logger --log /tmp/test.log --out /tmp/queue.json
cat /tmp/queue.json
```

### DoD
- [ ] `pytest tests/test_day_logger.py` 全部通过
- [ ] CLI 可正常运行
- [ ] 去重逻辑正确（相同能力只出现一次，occurrences 累加）
- [ ] 输出 JSON 格式正确

---

## Task 3: Skill 契约与 Registry 数据模型

### 目的
定义技能契约（manifest schema）和注册表数据模型。

### 改动文件
```
src/
├── models/
│   ├── skill.py             # 新建
│   └── registry.py          # 新建
├── registry.py              # 新建（Registry 操作类）
└── validators/
    ├── __init__.py          # 新建
    └── manifest.py          # 新建（manifest 校验）
tests/
├── test_skill_model.py      # 新建
├── test_registry.py         # 新建
└── test_manifest_validator.py  # 新建
```

### 实现步骤

1. 定义 `SkillManifest` 模型 (Pydantic)
2. 定义 `SkillVersion`、`SkillEntry` 模型
3. 实现 `Registry` 类（load/save/add/promote/rollback）
4. 实现 manifest schema 校验器

### 核心代码框架

```python
# src/models/skill.py
from pydantic import BaseModel, Field
from typing import Literal

class Permission(BaseModel):
    filesystem: Literal["none", "read_workdir", "write_workdir"] = "none"
    network: bool = False
    subprocess: bool = False

class SkillManifest(BaseModel):
    name: str = Field(..., pattern=r'^[a-z][a-z0-9_]{2,63}$')
    version: str = Field(..., pattern=r'^\d+\.\d+\.\d+$')
    description: str = Field(..., min_length=10, max_length=500)
    inputs_schema: dict
    outputs_schema: dict
    permissions: Permission
    dependencies: list[dict] = []
```

```python
# src/models/registry.py
from pydantic import BaseModel
from datetime import datetime

class ValidationResult(BaseModel):
    ast_gate: dict | None = None
    sandbox: dict | None = None
    promote_gate: dict | None = None

class SkillVersion(BaseModel):
    version: str
    code_hash: str
    manifest_hash: str
    created_at: datetime
    status: str  # staging | prod | disabled
    validation: ValidationResult = ValidationResult()

class SkillEntry(BaseModel):
    name: str
    current_prod: str | None = None
    current_staging: str | None = None
    versions: dict[str, SkillVersion] = {}
```

### 验证命令
```bash
pytest tests/test_skill_model.py tests/test_registry.py tests/test_manifest_validator.py -v
```

### DoD
- [ ] `SkillManifest` 校验正确（name/version 格式）
- [ ] `Registry` CRUD 操作正确
- [ ] manifest schema 校验与 `contracts/skill_schema.json` 一致

---

## Task 4: 静态安全门（AST Gate）

### 目的
实现基于 AST 的静态安全检查。

### 改动文件
```
src/
└── security/
    ├── __init__.py          # 新建
    ├── policy.py            # 新建（安全策略配置）
    └── ast_gate.py          # 新建（AST 检查器）
tests/
└── test_ast_gate.py         # 新建
```

### 实现步骤

1. 定义安全策略常量 (`policy.py`)
2. 实现 AST 遍历检查 (`ast_gate.py`)
3. 实现字符串模式检查
4. 编写全面的测试用例

### 核心代码框架

```python
# src/security/policy.py
ALLOWED_TOP_LEVEL_MODULES = frozenset({
    "json", "re", "pathlib", "datetime", "typing",
    "collections", "itertools", "functools", "math",
    "decimal", "fractions", "statistics", "random",
    "hashlib", "base64", "urllib", "dataclasses",
    "enum", "copy", "pprint", "textwrap", "string",
    "contextlib", "abc", "time", "calendar", "types",
    "operator", "csv", "xml", "binascii",
})

FORBIDDEN_CALLS = frozenset({
    "__import__", "eval", "exec", "compile",
    "open", "input", "breakpoint",
    "getattr", "setattr", "delattr",
    "globals", "locals", "vars",
})

FORBIDDEN_ATTRIBUTES = frozenset({
    "__subclasses__", "__bases__", "__mro__",
    "__globals__", "__code__", "__closure__",
    "__builtins__", "__import__",
    "__loader__", "__spec__",
})
```

```python
# src/security/ast_gate.py
import ast
from dataclasses import dataclass
from .policy import *

@dataclass
class GateResult:
    passed: bool
    violations: list[str]

class ASTGate:
    def check(self, code: str) -> GateResult:
        violations = []
        # 1. 字符串模式检查
        # 2. AST 解析
        # 3. 遍历检查
        return GateResult(passed=len(violations) == 0, violations=violations)
```

### 验证命令
```bash
pytest tests/test_ast_gate.py -v
```

### DoD
- [ ] 所有禁止的导入被拦截
- [ ] 所有禁止的调用被拦截
- [ ] 所有禁止的属性访问被拦截
- [ ] 路径穿越模式被拦截
- [ ] 允许的代码通过检查

---

## Task 5: Docker 沙盒 Harness

### 目的
实现 Docker 容器内的技能执行器和外部 Runner。

### 改动文件
```
src/
└── sandbox/
    ├── __init__.py          # 新建
    ├── harness.py           # 新建（容器内执行）
    └── runner.py            # 新建（Docker 控制）
docker/
├── Dockerfile.sandbox       # 新建
├── entrypoint.sh           # 新建
└── requirements.allowlist.txt  # 新建
tests/
└── test_sandbox.py          # 新建
```

### 实现步骤

1. 创建 Dockerfile.sandbox
2. 实现 harness.py（容器内）
3. 实现 runner.py（Docker API 调用）
4. 编写测试（包括绕过测试）

### 核心代码框架

参见 `security.md` 中的完整实现。

### 验证命令
```bash
docker build -f docker/Dockerfile.sandbox -t openclaw-sandbox:latest .
pytest tests/test_sandbox.py -v
```

### DoD
- [ ] Docker 镜像构建成功
- [ ] `verify() = True` 的技能通过
- [ ] `verify() = False` 的技能失败
- [ ] `SystemExit(0)` 被捕获并判定失败
- [ ] 超时被正确处理
- [ ] 容器在测试后被清理

---

## Task 6: Night Evolver（生成→验证→staging）

### 目的
实现完整的 Night Mode 流程。

### 改动文件
```
src/
├── night_evolver.py         # 新建
└── llm/
    ├── __init__.py          # 新建
    ├── base.py              # 新建（Provider 接口）
    └── mock.py              # 新建（MockLLM）
tests/
├── test_night_evolver.py    # 新建
└── test_mock_llm.py         # 新建
```

### 实现步骤

1. 定义 LLMProvider 接口
2. 实现 MockLLM（返回预定义技能）
3. 实现 night_evolver 主流程
4. 集成 AST Gate 和 Sandbox Runner

### 核心代码框架

```python
# src/night_evolver.py
def evolve(queue_path: Path, staging_path: Path, registry_path: Path, provider: str):
    """Night Mode 主流程"""
    queue = load_queue(queue_path)
    registry = load_registry(registry_path)
    llm = get_provider(provider)
    
    for item in queue.items:
        if item.status != "pending":
            continue
        
        # 1. 生成技能
        skill_pkg = llm.generate_skill(item.capability, item.context)
        
        # 2. AST Gate
        gate = ASTGate()
        result = gate.check(skill_pkg.code)
        if not result.passed:
            item.status = "failed"
            continue
        
        # 3. Manifest 校验
        if not validate_manifest(skill_pkg.manifest):
            item.status = "failed"
            continue
        
        # 4. Sandbox 验证
        runner = SandboxRunner()
        passed, logs, metrics = runner.run(skill_pkg)
        if not passed:
            item.status = "failed"
            continue
        
        # 5. 写入 staging
        write_to_staging(staging_path, skill_pkg)
        update_registry(registry, skill_pkg, "staging")
        item.status = "completed"
    
    save_queue(queue_path, queue)
    save_registry(registry_path, registry)
```

### 设计注意：LLM Provider 接口要为 Project B 留口

```python
# src/llm/base.py
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
    
    # Project B 会扩展这个接口：
    # def merge_skills(self, skills: list[str]) -> SkillPackage:  # 批量进化
    # def assess_similarity(self, a: str, b: str) -> float:       # 去重判断
```

### 验证命令
```bash
pytest tests/test_night_evolver.py tests/test_mock_llm.py -v

# 端到端
python -m src.day_logger --log /tmp/test.log --out data/nightly_queue.json
python -m src.night_evolver --queue data/nightly_queue.json --staging skills_staging --registry data/registry.json --provider mock
ls -la skills_staging/
```

### DoD
- [ ] MockLLM 可生成预定义技能
- [ ] Night evolver 完整流程可运行
- [ ] 失败的技能被正确标记
- [ ] 成功的技能写入 staging
- [ ] Registry 被正确更新

---

## Task 7: Promote Gate（评测集验证）

### 目的
实现 Staging→Prod 的晋升门槛验证。

### 改动文件
```
src/
├── promote.py               # 新建
└── eval/
    ├── __init__.py          # 新建
    └── gate.py              # 新建（Gate 执行器）
data/
└── eval/
    ├── replay/              # 新建（测试数据）
    ├── regression/          # 新建（测试数据）
    └── redteam/             # 新建（测试数据）
tests/
├── test_promote.py          # 新建
└── test_eval_gate.py        # 新建
```

### 实现步骤

1. 设计评测用例格式
2. 实现三类 Gate（replay/regression/redteam）
3. 实现 promote 主流程
4. 准备最小评测数据集

### 评测用例格式

```json
// data/eval/replay/text_echo_001.json
{
  "skill": "text_echo",
  "input": {"text": "hello", "format": "uppercase"},
  "expected_output": "HELLO",
  "match_type": "exact"
}
```

### 验证命令
```bash
pytest tests/test_promote.py tests/test_eval_gate.py -v

python -m src.promote --staging skills_staging --prod skills_prod --registry data/registry.json --eval-dir data/eval
ls -la skills_prod/
```

### DoD
- [ ] 三类 Gate 可独立执行
- [ ] Gate 通过率计算正确
- [ ] 晋升逻辑正确（全部通过才晋升）
- [ ] 失败原因被记录到 Registry

---

## Task 8: Rollback 与审计报告

### 目的
实现版本回滚和审计日志。

### 改动文件
```
src/
├── rollback.py              # 新建
└── audit.py                 # 新建（审计日志）
tests/
├── test_rollback.py         # 新建
└── test_audit.py            # 新建
```

### 实现步骤

1. 实现 rollback CLI
2. 实现审计日志记录
3. 集成审计日志到所有关键操作

### 核心代码框架

```python
# src/rollback.py
def rollback(skill_name: str, target_version: str, registry_path: Path):
    """回滚到指定版本"""
    registry = load_registry(registry_path)
    entry = registry.skills.get(skill_name)
    
    if not entry:
        raise ValueError(f"Skill not found: {skill_name}")
    
    if target_version not in entry.versions:
        raise ValueError(f"Version not found: {target_version}")
    
    # 禁用当前版本
    if entry.current_prod:
        entry.versions[entry.current_prod].status = "disabled"
        entry.versions[entry.current_prod].disabled_at = datetime.now()
        entry.versions[entry.current_prod].disabled_reason = f"Rollback to {target_version}"
    
    # 切换指针
    entry.current_prod = target_version
    entry.versions[target_version].status = "prod"
    
    save_registry(registry_path, registry)
    log_audit("ROLLBACK", skill=skill_name, from_version=entry.current_prod, to_version=target_version)
```

### 验证命令
```bash
pytest tests/test_rollback.py tests/test_audit.py -v

python -m src.rollback --skill text_echo --to 1.0.0 --registry data/registry.json
cat data/audit.log
```

### DoD
- [ ] Rollback 可切换版本
- [ ] 旧版本被标记为 disabled 而非删除
- [ ] 审计日志记录所有关键操作
- [ ] 审计日志格式正确（时间戳、操作、参数）

---

## 执行顺序总结

```
git checkout -b dev

Task 1 ─► Task 2 ─► Task 3 ─► Task 4 ─► Task 5 ─► Task 6 ─► Task 7 ─► Task 8
  │         │         │         │         │         │         │         │
骨架      Day       模型      AST      Docker    Night    Promote  Rollback
          Logger             Gate     Sandbox   Evolver   Gate     Audit

git checkout main && git merge dev && git tag v2.0.0-project-a
```

每个 Task 完成后：
1. 运行该 Task 的验证命令
2. 检查 DoD 清单
3. `git add . && git commit -m "task-N: <描述>"`
4. 继续下一个 Task

---

## Project A 完成后

Project A 全部通过验收后（见 `acceptance.md`），标记里程碑：

```bash
git tag v2.0.0-project-a -m "Project A: Secure Skill Lifecycle Manager complete"
```

然后参考 `roadmap_b.md` 开始 Project B 的设计与实现。
