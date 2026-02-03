# OpenClaw Project A - Acceptance Criteria

> 版本：2.0.0 | 最后更新：2026-02-03
>
> 范围：Project A (Secure Skill Lifecycle Manager)

## 1. 必跑命令

以下命令必须全部通过才能认为 MVP 完成：

### 1.1 代码质量

```bash
# Lint 检查
ruff check .

# 类型检查（如果使用）
# mypy src/

# 单元测试
pytest tests/ -v

# 覆盖率（可选，MVP 不强制）
# pytest tests/ --cov=src --cov-report=term-missing
```

### 1.2 Day Mode

```bash
# 准备测试日志
cat > /tmp/test_runtime.log << 'EOF'
2026-02-01 10:00:00 INFO Starting service
2026-02-01 10:01:00 WARN [MISSING: convert CSV to JSON with schema validation]
2026-02-01 10:02:00 INFO Processing request
2026-02-01 10:03:00 WARN [MISSING: normalize filename removing special characters]
2026-02-01 10:04:00 WARN [MISSING: convert CSV to JSON with schema validation]
EOF

# 运行 day_logger
python -m src.day_logger \
    --log /tmp/test_runtime.log \
    --out data/nightly_queue.json

# 验证输出
python -c "
import json
with open('data/nightly_queue.json') as f:
    q = json.load(f)
assert len(q['items']) == 2, f'Expected 2 items, got {len(q[\"items\"])}'
assert q['items'][0]['occurrences'] == 2, 'First item should have 2 occurrences'
print('✓ day_logger verification passed')
"
```

### 1.3 Night Mode

```bash
# 运行 night_evolver（使用 MockLLM）
python -m src.night_evolver \
    --queue data/nightly_queue.json \
    --staging skills_staging \
    --registry data/registry.json \
    --provider mock

# 验证 staging 输出
python -c "
import json
from pathlib import Path

# 检查 registry
with open('data/registry.json') as f:
    reg = json.load(f)
assert len(reg['skills']) > 0, 'No skills in registry'

# 检查 staging 目录结构
staging = Path('skills_staging')
for skill_name in reg['skills']:
    skill_entry = reg['skills'][skill_name]
    if skill_entry.get('current_staging'):
        version = skill_entry['current_staging']
        skill_dir = staging / skill_name / version
        assert skill_dir.exists(), f'{skill_dir} not found'
        assert (skill_dir / 'skill.py').exists(), f'{skill_dir}/skill.py not found'
        assert (skill_dir / 'skill.json').exists(), f'{skill_dir}/skill.json not found'
        print(f'✓ {skill_name}/{version} structure verified')

print('✓ night_evolver verification passed')
"
```

### 1.4 Promotion

```bash
# 运行 promote
python -m src.promote \
    --staging skills_staging \
    --prod skills_prod \
    --registry data/registry.json \
    --eval-dir data/eval

# 验证 prod 输出
python -c "
import json
from pathlib import Path

with open('data/registry.json') as f:
    reg = json.load(f)

prod = Path('skills_prod')
promoted_count = 0
for skill_name, entry in reg['skills'].items():
    if entry.get('current_prod'):
        version = entry['current_prod']
        skill_dir = prod / skill_name / version
        assert skill_dir.exists(), f'{skill_dir} not found'
        promoted_count += 1
        print(f'✓ {skill_name}/{version} promoted to prod')

assert promoted_count > 0, 'No skills promoted'
print(f'✓ promote verification passed ({promoted_count} skills)')
"
```

### 1.5 Rollback

```bash
# 假设有技能需要回滚（此命令在有多版本时测试）
# python -m src.rollback \
#     --skill text_echo \
#     --to 0.9.0 \
#     --registry data/registry.json

# 基本验证：rollback CLI 可用
python -m src.rollback --help
echo "✓ rollback CLI available"
```

### 1.6 安全验证

```bash
# AST Gate 测试
pytest tests/test_ast_gate.py -v

# Sandbox 测试（需要 Docker）
pytest tests/test_sandbox.py -v

# 集成安全测试
pytest tests/test_security_integration.py -v
```

### 1.7 端到端测试

```bash
# 完整闭环测试
pytest tests/test_e2e.py -v
```

---

## 2. DoD（Definition of Done）

### 2.1 功能完整性

| 检查项 | 验证方法 | 状态 |
|--------|----------|------|
| Day logger 可解析日志提取 MISSING 标记 | `test_day_logger.py` | ☐ |
| Day logger 支持去重和计数 | `test_day_logger.py` | ☐ |
| Night evolver 可调用 MockLLM 生成技能 | `test_night_evolver.py` | ☐ |
| AST Gate 拦截所有禁止的导入 | `test_ast_gate.py::test_forbidden_imports` | ☐ |
| AST Gate 拦截所有禁止的调用 | `test_ast_gate.py::test_forbidden_calls` | ☐ |
| AST Gate 拦截危险属性访问 | `test_ast_gate.py::test_forbidden_attributes` | ☐ |
| Sandbox 正确执行 verify() | `test_sandbox.py::test_verify_success` | ☐ |
| Sandbox 捕获 SystemExit | `test_sandbox.py::test_system_exit_bypass` | ☐ |
| Sandbox 超时处理正确 | `test_sandbox.py::test_timeout` | ☐ |
| Promote 执行三套 gate | `test_promote.py` | ☐ |
| Rollback 可切换版本 | `test_rollback.py` | ☐ |
| Registry 记录完整审计信息 | `test_registry.py` | ☐ |

### 2.2 安全性

| 检查项 | 验证方法 | 状态 |
|--------|----------|------|
| 无法通过 `SystemExit` 绕过验证 | `test_security_integration.py::test_systemexit_bypass` | ☐ |
| 无法通过 `__import__` 导入危险模块 | `test_security_integration.py::test_import_bypass` | ☐ |
| 无法通过 `getattr` 获取危险函数 | `test_security_integration.py::test_getattr_bypass` | ☐ |
| 无法通过 `globals()` 访问内置 | `test_security_integration.py::test_globals_bypass` | ☐ |
| 无法通过 `__subclasses__` 逃逸 | `test_security_integration.py::test_subclasses_bypass` | ☐ |
| Docker 网络隔离生效 | `test_sandbox.py::test_network_isolation` | ☐ |
| Docker 只读文件系统生效 | `test_sandbox.py::test_readonly_fs` | ☐ |
| Docker 资源限制生效 | `test_sandbox.py::test_resource_limits` | ☐ |

### 2.3 可追溯性

| 检查项 | 验证方法 | 状态 |
|--------|----------|------|
| Registry 记录 code_hash | 检查 `registry.json` | ☐ |
| Registry 记录 manifest_hash | 检查 `registry.json` | ☐ |
| Registry 记录验证结果 | 检查 `registry.json` | ☐ |
| 操作日志记录关键事件 | 检查 `data/audit.log` | ☐ |

### 2.4 可复现性

| 检查项 | 验证方法 | 状态 |
|--------|----------|------|
| 依赖版本锁定 | 检查 `uv.lock` 存在且完整 | ☐ |
| Docker 镜像可构建 | `docker build -f docker/Dockerfile.sandbox -t openclaw-sandbox .` | ☐ |
| 相同输入产生相同输出 | 运行两次 night_evolver 对比 | ☐ |

---

## 3. 验收测试矩阵

### 3.1 AST Gate 测试用例

| 输入代码 | 预期结果 | 测试函数 |
|----------|----------|----------|
| `import os` | REJECT | `test_import_os` |
| `import subprocess` | REJECT | `test_import_subprocess` |
| `from os import path` | REJECT | `test_from_os_import` |
| `import json` | PASS | `test_import_json` |
| `import pathlib` | PASS | `test_import_pathlib` |
| `__import__('os')` | REJECT | `test_dunder_import` |
| `eval('1+1')` | REJECT | `test_eval` |
| `exec('pass')` | REJECT | `test_exec` |
| `getattr(x, 'y')` | REJECT | `test_getattr` |
| `globals()` | REJECT | `test_globals` |
| `x.__subclasses__()` | REJECT | `test_subclasses` |
| `func.__globals__` | REJECT | `test_func_globals` |
| `'../etc/passwd'` | REJECT | `test_path_traversal` |

### 3.2 Sandbox 测试用例

| 场景 | 技能代码 | 预期结果 | 测试函数 |
|------|----------|----------|----------|
| 正常通过 | `def verify(): return True` | PASS | `test_verify_success` |
| 返回 False | `def verify(): return False` | FAIL | `test_verify_false` |
| 返回 None | `def verify(): pass` | FAIL | `test_verify_none` |
| 返回 1 | `def verify(): return 1` | FAIL | `test_verify_truthy` |
| 抛出异常 | `def verify(): raise ValueError()` | FAIL | `test_verify_exception` |
| SystemExit(0) | `def verify(): raise SystemExit(0)` | FAIL | `test_systemexit_zero` |
| SystemExit(1) | `def verify(): raise SystemExit(1)` | FAIL | `test_systemexit_one` |
| KeyboardInterrupt | `def verify(): raise KeyboardInterrupt()` | FAIL | `test_keyboard_interrupt` |
| 超时 | `def verify(): while True: pass` | FAIL | `test_timeout` |
| Fork bomb | `def verify(): import os; os.fork()` | FAIL（AST 拦截） | `test_fork_bomb` |

### 3.3 Promote Gate 测试用例

| Gate | 通过条件 | 测试函数 |
|------|----------|----------|
| replay | 100% 通过 | `test_replay_gate` |
| regression | ≥99% 通过 | `test_regression_gate` |
| redteam | 100% 通过 | `test_redteam_gate` |

---

## 4. 手动验收检查清单

在自动化测试通过后，执行以下手动检查：

### 4.1 代码审查

- [ ] 所有 TODO 已处理或记录到 issue
- [ ] 没有硬编码的敏感信息
- [ ] 日志输出不包含敏感数据
- [ ] 错误消息对用户友好

### 4.2 文档检查

- [ ] README.md 包含安装和使用说明
- [ ] spec/ 文档与实现一致
- [ ] 示例技能可正常工作

### 4.3 运维检查

- [ ] Docker 镜像大小合理（< 500MB）
- [ ] 内存使用在限制内
- [ ] 日志文件有轮转配置（或说明）

---

## 5. 已知限制（MVP 接受）

以下限制在 MVP 中是已知且接受的：

1. **MockLLM 有限**：只能生成预定义的技能，不测试真实 LLM 集成
2. **单机运行**：不支持分布式
3. **离线模式**：不支持运行时下载依赖或访问网络
4. **评测数据有限**：replay/regression/redteam 各 3-5 个用例
5. **无 GUI**：纯 CLI 操作

---

## 6. Post-Project A 改进方向

以下改进在 Project B 中实现（见 `roadmap_b.md`）：

1. 真实 LLM 集成（Anthropic/OpenAI）
2. Multi-Agent 运行时（Manager/Executor/Developer）
3. Parallel Batch Evolution（技能去重与合并）
4. 收敛度监控
5. Benchmark 评测（HLE / DeepSearchQA）

以下改进未规划：

6. Web UI 管理界面
7. 分布式执行支持
8. 更细粒度的权限控制
9. 自动化 CI/CD 集成
