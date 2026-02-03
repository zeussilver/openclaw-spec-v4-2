# 老板版（5分钟读完）
- 这是什么：OpenClaw 是一个“零信任”技能 CI/CD 管线规范 + 实现仓库，覆盖 Day/Night/Promote/Rollback 全流程（见 `spec/overview.md`, `spec/architecture.md`）。
- 能干什么：
  1. 从日志提取缺失能力入队（`src/day_logger.py`）。
  2. 生成候选技能并通过 AST + Sandbox 验证（`src/night_evolver.py`, `src/security/*`, `src/sandbox/*`）。
  3. 评测 gate 后晋升到生产（`src/promote.py`）。
  4. 维护技能版本注册表并回滚（`src/registry.py`, `src/rollback.py`）。
  5. 提供完整测试与验收路径（`spec/acceptance.md`, `tests/`）。
- 现在仓库健康度：黄。
  - 理由：缺少 CI 与 LICENSE（`repo_review.md`）；契约与实现校验仍未对齐（`reports/contract_lint_report.md`）。
- P0 风险（必须修）：无明确 P0。
- P1（应该修）：
  - Schema 约束强于实现校验（`spec/contracts/skill_schema.json` vs `src/models/skill.py`，见 `reports/contract_lint_report.md`）。
  - 缺少 CI 与 LICENSE（`reports/repo_review.md`）。
  - 规范描述引用 `src/skill_loader.py`，但实际不存在（`reports/spec_architecture.md`）。
- 下一步 2 周路线图：
  1. **W1**：补齐 CI 模板（建议 `.github/workflows`），并补充 `LICENSE`。
  2. **W1**：对齐契约与实现校验（在 `SkillManifest` 中校验 `inputs_schema`/`outputs_schema`）。
  3. **W2**：发布 `v2.0.0-project-a` tag，形成可对外说明版本。
- 我如何使用：
  - 一键验证命令：
    ```bash
    uv sync
    uv run ruff check .
    uv run pytest tests/ -v
    uv run python tools/contract_lint/lint.py
    ```
  - 成功标准：全部命令无报错退出。

# 工程版（可交接）
- Repo Profile（证据）：见 `reports/repo_profile.md`。
- 规范架构地图（模块/契约边界/引用拓扑）：见 `reports/spec_architecture.md`。
- 变更影响分析（breaking changes + 迁移建议）：见 `reports/change_impact.md`。
- 校验体系与 CI 建议：见 `reports/contract_lint_report.md` 与 `reports/repo_review.md`。
- Skills 清单（新增/复用）及触发方式：见 `skills/README.md`。
