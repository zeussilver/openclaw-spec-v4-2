# Contract Lint Report

> 目标：规范可验证性、引用完整性、命名一致性、示例一致性、文档链接可用性。

## 1) 校验矩阵（文件类型 → 方法 → 命令 → 失败定位）

| 类型 | 发现位置 | 校验方法 | 命令 | 失败定位 |
|---|---|---|---|---|
| JSON Schema | `spec/contracts/skill_schema.json` | `jsonschema` Draft-07 校验 + `$ref` 扫描 | `uv run python tools/contract_lint/lint.py` | 脚本输出 `$ref errors` 或 schema 校验异常 |
| Markdown 规范 | `spec/**/*.md` | Markdown 链接检查（显式链接）+ 反引号路径提示 | `uv run python tools/contract_lint/lint.py` | `Markdown reference errors/warnings` 列表 |
| 示例一致性 | `skills/**/skill.json`（当前无样本） | 使用 `jsonschema` 验证示例 | 建议新增 `tools/contract_lint/validate_skill_examples.py` | 输出 JSON schema 验证失败路径 |

> 注：目前 `tools/contract_lint/lint.py` 会把“反引号路径”作为 **warning**，避免误报（如运行时文件 `data/*.json`）。

## 2) 运行结果摘要（基于本次执行）
- Schema 校验：**通过**（Draft-07）
- `$ref`：**0 个**
- Markdown 显式链接：**无错误**
- Markdown 反引号路径：**11 条 warning**（多为路径提示或已移除文件的残留提及）

执行命令（本次使用 venv）：
```
/Users/liuzhenqian/Desktop/openclaw-spec-v4-2/.venv/bin/python \
  tools/contract_lint/lint.py
```

## 3) 发现问题（P0/P1/P2）

### P0（阻断性）
- 无。

### P1（高风险误用 / 契约与实现不一致）
- 无（已将 `SkillManifest` 与 schema 约束对齐）。

### P2（一致性/维护成本）
- 文档中存在“反引号路径”引用但非严格链接：
  - 例如 `spec/README.md` 中提到已移除的 `worktree-setup.md`；
  - `spec/architecture.md` / `spec/gsd_tasks.md` 使用 `spec/contracts/skill_schema.json` 等路径引用，但不是可点击链接。
  - 建议：改为 Markdown 链接或在文档中注明“路径为仓库根目录路径”。

## 4) 最小可落地自动化方案（CI 建议）

1. **新增轻量校验脚本（已提供）**
   - `tools/contract_lint/lint.py`
   - 功能：JSON Schema 合法性 + `$ref` + Markdown 链接检查（warning 级别）。

2. **CI Gate（已接入）**
   - 已在 `.github/workflows/ci.yml` 中运行：
     - `uv sync`
     - `uv run python tools/contract_lint/lint.py`
     - 若需要强约束，可将 warning 提升为 error（后续迭代）。

## 5) 可沉淀为 Skill 的候选流程（给 Skill-Creator）
- **spec-ref-audit**：自动扫描规范中的 $ref / 链接 / 反引号路径，输出可操作报告。
- **validate-spec-suite**：统一入口执行 JSON Schema 校验 + 示例校验 + Markdown 链接检查。
