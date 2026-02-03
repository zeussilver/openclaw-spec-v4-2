# Change Impact Report (dev vs baseline)

## 1) Baseline 选择与依据
- 仓库 **无 tag**：`git tag` 为空。
- 存在 `main` 分支作为稳定基线：`git branch -a` 显示 `main`。
- `git ls-tree --name-only main` **为空**，表示 main 分支没有任何跟踪文件。

**结论：** 采用 `main` 作为基线，比较 `main..dev`。

## 2) Diff 摘要（main → dev）
`git diff --stat main..dev` 显示：
- **67 个文件新增**，约 8814 行新增。
- 新增内容覆盖：
  - 代码：`src/**`（Day/Night/Promote/Rollback/Sandbox/Security/LLM/Registry/Eval/Validators）
  - 测试：`tests/**`（AST Gate、Sandbox、安全集成、E2E 等）
  - 数据样例：`data/eval/**`
  - Docker 沙盒：`docker/**`
  - 工程化：`pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore`

`git log --oneline main..dev`：
```
f39a92e integration: cross-module wiring, e2e tests, security integration tests
5b752a4 task-7: promote gates (replay, regression, redteam)
b2eb1ef task-6: night evolver with MockLLM
4fd0b84 task-4: AST gate (static security analysis)
1b5226d task-5: docker sandbox harness and runner
2d9407e task-8: rollback and audit logging
3bdb55b task-3: skill contracts and registry
e553c1e task-2: day logger (log parsing and queue)
f55f27b task-1: project skeleton and dependency lock
```

## 3) 破坏性变更（Breaking Changes）
- 基线 `main` 为空目录，**无历史接口或契约可被破坏**。
- 因此：本次变更为 **初始引入**，不构成传统意义上的 breaking changes。

## 4) 迁移建议
- 对已有下游（如仅使用 main 分支的用户）：
  - 视为 **首次发布**，直接迁移到 dev 的结构与接口。
- 对规范用户：
  - 注意 `spec/` 当前未被 git 跟踪（见 `reports/repo_profile.md`），若要对外发布规范，需先纳入版本控制。

## 5) 版本建议
- 已统一版本口径为 `2.0.0`（代码与规范一致）。建议发布 `v2.0.0-project-a` 作为对外版本标签。
