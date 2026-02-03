# Contributor Guide (工程版)

## 1) 环境准备
- Python 3.11+
- uv
- Docker（Sandbox 验证需要）

```bash
uv sync
```

## 2) 仓库结构速览
- `src/`：核心实现
- `tests/`：测试套件
- `spec/`：规范文档与契约（建议纳入 git 追踪）
- `data/`：评测与运行时数据
- `docker/`：Sandbox 运行环境
- `tools/`：一次性或可复用的工具脚本（可升级为 skill）

## 3) 一键验证（推荐）
```bash
# Lint
uv run ruff check .

# Unit + integration tests
uv run pytest tests/ -v

# 端到端闭环
uv run pytest tests/test_e2e.py -v

# 规范/契约校验（新增）
uv run python tools/contract_lint/lint.py
```

## 4) 规范变更流程（强制）
依据 `spec/iteration.md`：
1. 发现问题 → **先更新规范**
2. 创建 `spec/changes/NNN-<desc>.md`
3. 更新相关 spec 文件
4. 单独提交 spec 变更
5. 再实现代码

推荐命令：
```bash
./scripts/spec-review.sh
```

## 5) 发布流程（建议）
1. 确认 `spec/` 更新并提交。
2. 完整通过 lint + tests + contract lint。
3. 统一版本口径：
   - 如果遵循 SemVer，确认 `pyproject.toml` 与 `spec/*` 头部版本一致。
4. 打 tag（参考 `spec/gsd_tasks.md` 的 `v0.1.0-project-a`）。

## 6) 示例与契约一致性
- `spec/contracts/skill_schema.json` 为唯一真相。
- 任何新增 `skills/**/skill.json` 必须通过 JSON Schema 校验。
- 建议新增脚本自动校验所有 `skill.json`（可扩展 `tools/contract_lint/validate_skill_examples.py`）。

## 7) 常见问题
1. **本地测试与 CI 不一致怎么办？**
   - 目前没有 CI，请以 `uv run pytest tests/ -v` 为准，并优先补充 CI。
2. **Docker 相关测试失败？**
   - 确认 Docker 启动与权限；测试依赖 `docker` CLI。
3. **规范文件在 git 中丢失？**
   - 目前 `spec/` 未跟踪，需要尽快纳入版本控制。
4. **技能契约字段新增如何处理？**
   - 更新 `spec/contracts/skill_schema.json` + `src/models/skill.py` + 测试。
5. **如何识别 breaking change？**
   - 删除字段/收紧约束/改变默认语义 → 必须升级 major 或在 0.x 内明确标注。
6. **如何生成 Release Notes？**
   - 建议从 `git log main..dev` 或 `git diff --stat` 生成模板。
7. **如何新增评测用例？**
   - 放入 `data/eval/{replay,regression,redteam}` 并更新 `spec/eval/*.md`。
8. **如何确保安全策略一致？**
   - `spec/security.md` 与 `src/security/*` 必须同步更新。
