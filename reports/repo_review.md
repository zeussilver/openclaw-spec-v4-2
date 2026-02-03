# Repo Review (Engineering Quality & Risk)

## 1) CI / Automation
- **CI 状态**：未发现 `.github/workflows`（`ls .github` 为空），当前无自动化 lint/test/validate。
- **现有脚本**：`scripts/spec-review.sh` 提供手工规范回顾清单；缺少自动化 gate。

## 2) 依赖与锁定
- **依赖声明**：`pyproject.toml`（`jsonschema`, `pytest`, `ruff`, `pydantic`, `docker`）。
- **锁文件**：`uv.lock` 存在（有助于可复现）。
- **潜在风险**：无 CI 时锁文件变更缺乏强制验证。

## 3) 安全与供应链
- **Docker 沙盒**：存在 `docker/requirements.allowlist.txt`，表明有供应链白名单策略。
- **密钥扫描**：未发现明显密钥/Token 模式（基于简单 grep 扫描）。
- **风险**：无 CI 的安全检查/静态分析 gate。

## 4) License / 贡献流程
- **LICENSE**：未找到 LICENSE 文件。
- **CONTRIBUTING / Code of Conduct**：未找到。
- **README**：标注 “Proprietary”，但无正式 License 文件支撑。

## 5) 可维护性
- 目录结构清晰（`src/`, `tests/`, `docker/`, `data/`）。
- 存在 `.venv/`、`.pytest_cache/` 等本地目录；虽已在 `.gitignore`，但需避免误提交。

## 6) 问题分级

### P0
- 无直接阻断问题。

### P1
- **缺少 CI**：无法保证 lint/test/contract 校验在合并前通过。
- **LICENSE 缺失**：与 README 中 “Proprietary” 表述不一致，法律/合规风险。

### P2
- 缺少 CONTRIBUTING / Code of Conduct。
- 缺少统一的 `make` 或 `task` 入口，验证路径分散。

## 7) 高性价比改进建议（3-5 条）
1. 新增 CI（ruff + pytest + spec contract lint）。
2. 提供 LICENSE（与 README 的“Proprietary”一致）。
3. 增加 CONTRIBUTING，写明开发/验证/发布流程。
4. 提供统一命令入口（如 `make validate` 或 `scripts/validate.sh`）。
