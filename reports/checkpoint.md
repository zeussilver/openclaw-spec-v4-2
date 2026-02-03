# Checkpoint — OpenClaw (dev)

Last updated: 2026-02-03 23:53:30 +0800

## Goal
建立可持续的“规范 + 实现 + 校验 + CI + 激进跑一周”闭环，让你能判断何时可以接入本地 openclaw agent。

## Repo State (evidence)
- Branch: `dev`
- Recent commits (top → older):
  - `1ed6552` test: add aggressive harvester mode (github search + opt-in network)
  - `fd2de32` tools: add aggressive skill test harness
  - `cd4fd9d` feat: enforce skill manifest schema in model
  - `e583095` ci: add minimal GitHub Actions pipeline
  - `7724e47` chore: track spec and align version to 2.0.0
- Untracked local-only files (not committed): `.prompts/`, `.gsd/`, `.swarm-logs/`, `scripts/`, `CLAUDE.md`, `init-project.sh`, `.claude/`, `.DS_Store`

## What Was Done
### 1) Spec tracked + version aligned
- `spec/` 已纳入 git 追踪。
- 版本口径统一为 `2.0.0`：`pyproject.toml`, `uv.lock`, `spec/*` 头部。

### 2) Minimal CI
- GitHub Actions: `.github/workflows/ci.yml`
- Runs:
  - `uv sync`
  - `uv run ruff check .`
  - `uv run pytest tests/ -v`
  - `uv run python tools/contract_lint/lint.py`

### 3) Skill manifest schema enforced
- `src/models/skill.py` 现在对齐 `spec/contracts/skill_schema.json`：
  - `inputs_schema.type == "object"` 且 `properties` 必填
  - `outputs_schema.type` 必填
  - 顶层与 `permissions` 均 `extra=forbid`
- Tests:
  - `tests/test_skill_model.py`

### 4) Aggressive testing harness (更激进模式)
- 目的：每日/每4小时自动从来源拉取/发现技能 → 复制到隔离目录 → manifest 校验 → AST Gate → Sandbox 跑 → 输出报告。
- 代码：`tools/aggressive_test/run.py`
- 配置：`tools/aggressive_test/sources.json` (默认空), `tools/aggressive_test/sources.sample.json`
- 运行时产物（已加入 `.gitignore`）：
  - `data/aggressive_skills/`
  - `reports/aggressive_test/`

## How To Run (manual)
### Baseline validation
```bash
uv sync
uv run ruff check .
uv run pytest tests/ -v
uv run python tools/contract_lint/lint.py
```

### Aggressive harvester (discover via GitHub search)
1) 先限制范围（推荐：只搜你自己的 org/user）：
```bash
uv run python tools/aggressive_test/run.py \
  --build-sandbox-image \
  --window-days 7 \
  --github-query "\"inputs_schema\" \"outputs_schema\" \"permissions\"" \
  --github-filename skill.json \
  --github-owner zeussilver \
  --github-limit 30 \
  --max-skills 10
```
2) 看报告：`reports/aggressive_test/<timestamp>.md`

### 网络开关（危险）
- 默认：沙盒 `--network none`。
- 允许联网（但仍“按 manifest.permissions.network 决定是否给网”）：
```bash
uv run python tools/aggressive_test/run.py --allow-network --network-mode bridge
```
- 更激进：对所有技能强制开网（高风险）：
```bash
uv run python tools/aggressive_test/run.py --allow-network --network-mode bridge --network-always-on
```

### MVP 约束开关
- 默认 enforce：`permissions.network/subprocess` 必须为 `false`（MVP）。
- 放开（用于激进测试）：
```bash
uv run python tools/aggressive_test/run.py --relax-mvp-constraints
```

### 极限压力测试（更危险）
- 即使 manifest 校验或 AST Gate 失败，也强行进沙盒跑：
```bash
uv run python tools/aggressive_test/run.py --stress-sandbox
```

## Automation Plan (Codex)
建议用 Codex automation 跑 7 天窗口：
- 频率：每 4 小时
- 内容：跑 `tools/aggressive_test/run.py --window-days 7` 并生成报告
- 结束：脚本超过 7 天会输出“window complete”的报告；你仍需要手动停用 automation

## Known Issues / Risks
- GitHub code search 可能网络抖动（脚本已加重试，但仍可能失败）。
- “联网跑第三方技能”本质上是运行不可信代码开放 egress：
  - 建议先只对自己 org/user 的来源启用
  - 不要开启 `--network-always-on` 直到你确认来源可靠
- 规范中提到 `src/skill_loader.py` 但仓库里不存在（`reports/spec_architecture.md`）。

## Next Steps
- 如果你要继续更激进：
  - 先把 `--github-owner` 固定为你信任的 owner；跑 2-3 天观察报告稳定性
  - 再逐步放开 owner/repo 范围
- 如果要接入本地 openclaw agent：
  - 以“连续 N 天无 P0”作为 gate（你决定 N，建议 7）
