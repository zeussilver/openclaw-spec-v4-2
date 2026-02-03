# OpenClaw 使用说明（老板版）

## 这是什么（一句话）
OpenClaw 是一个“零信任”的技能 CI/CD 管线：从日志发现缺失能力 → 生成技能 → 安全验证 → 晋升到生产 → 可回滚。

## 能干什么（3-5 条）
- 自动从运行日志中提取缺失能力并入队。
- 用 MockLLM 生成候选技能并通过 AST + Docker 沙盒验证。
- 通过评测 Gate（replay/regression/redteam）后晋升到生产目录。
- 维护技能注册表（版本/状态/hash/验证结果）。
- 支持回滚到历史版本。

## 一键验证（从 0 到“OK”）
> 依赖：Python 3.11、uv、Docker（沙盒验证需要 Docker）。

```bash
# 1) 安装依赖
uv sync

# 2) 代码质量 + 全量测试
uv run ruff check .
uv run pytest tests/ -v

# 3) 端到端闭环（可选但推荐）
uv run pytest tests/test_e2e.py -v
```

成功标准：无报错退出。

## 规范在哪里？
- 规范入口：`spec/README.md`
- 核心契约（skill.json schema）：`spec/contracts/skill_schema.json`
- 安全约束：`spec/security.md`
- 验收清单：`spec/acceptance.md`

> 注意：当前 `spec/` 在 git 中是未追踪文件（需要纳入版本控制）。

## 业务流怎么跑（最短路径）
```bash
# Day Mode: 从日志提取缺失能力
python -m src.day_logger --log /tmp/runtime.log --out data/nightly_queue.json

# Night Mode: 生成候选技能并入 staging
python -m src.night_evolver --queue data/nightly_queue.json --staging skills_staging \
  --registry data/registry.json --provider mock

# Promote: 通过 gate 后晋升到 prod
python -m src.promote --staging skills_staging --prod skills_prod \
  --registry data/registry.json --eval-dir data/eval

# Rollback: 回滚到历史版本（需要已有多版本）
python -m src.rollback --skill <name> --to <version> --registry data/registry.json
```

## 发布版本（最短流程）
1. 确认 `spec/` 已更新并提交（如有变更）。
2. 完成 `uv run ruff check .` 与 `uv run pytest tests/ -v`。
3. 根据变更类型决定版本号（建议遵循 SemVer）。
4. 打 tag（参考 `spec/gsd_tasks.md` 中 `v0.1.0-project-a` 提示）。

## 常见问题（FAQ）
1. **为什么必须 Docker？**
   - Sandbox 验证依赖 Docker 资源限制与隔离策略。
2. **MockLLM 能否换成真实 LLM？**
   - 规范中预留接口（`src/llm/base.py`），Project B 规划引入真实 LLM。
3. **为什么 spec 和代码版本不一致？**
   - 目前规范标注 `2.0.0`，代码为 `0.1.0`，需要统一口径。
4. **如何确认技能契约符合规范？**
   - 以 `spec/contracts/skill_schema.json` 为准，并运行 schema 校验。
5. **如果测试失败，先改代码还是改规范？**
   - 先按 `spec/iteration.md` 走“更新规范→再实现”的流程。
6. **为什么没有 CI？**
   - 目前没有 `.github/workflows`，建议尽快补上自动校验。
7. **如何回滚技能？**
   - 使用 `python -m src.rollback --skill <name> --to <version>`。
8. **如何知道评测集怎么跑？**
   - 查看 `spec/acceptance.md` 中的 Promote & 安全测试步骤。
