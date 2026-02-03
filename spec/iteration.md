# OpenClaw - Iteration Protocol

> 版本：2.0.0 | 最后更新：2026-02-03
>
> 开发过程中如何迭代 spec 的协议

## 1. 迭代触发条件

当遇到以下情况时，**停止实现，先更新 spec**：

| 触发条件 | 示例 | 处理方式 |
|----------|------|----------|
| **设计缺陷** | AST Gate 漏掉了某个绕过方式 | 更新 `security.md` |
| **契约变更** | skill.json 需要新字段 | 更新 `contracts/skill_schema.json` |
| **任务拆分** | Task 5 太大，需要拆成 5a/5b | 更新 `gsd_tasks.md` |
| **验收变更** | 发现新的必要测试用例 | 更新 `acceptance.md` 或 `eval/` |
| **非目标变更** | 某个"非目标"其实必须做 | 更新 `overview.md` |

## 2. 变更记录格式

每次 spec 变更，在文件顶部的变更日志中记录：

```markdown
## Changelog

### 2026-02-03 - v1.1.0 (Task 4 实现中发现)
- **security.md**: 增加 `__class__` 属性检查（发现新绕过方式）
- **gsd_tasks.md**: Task 4 拆分为 4a (检查器) 和 4b (测试)
- **原因**: 实现 AST Gate 时发现 `obj.__class__.__bases__` 绕过

### 2026-02-02 - v1.0.0 (初始版本)
- 初始 spec 文档集
```

## 3. 变更目录结构

```
spec/
├── ...existing files...
└── changes/                    # 变更记录目录
    ├── 001-ast-gate-bypass.md  # 每个重大变更一个文件
    └── 002-task-split.md
```

### 变更文件模板

```markdown
# Change 001: AST Gate 新增绕过检测

## 触发点
Task 4 实现中，测试发现以下代码可以绕过当前检查：
```python
obj.__class__.__bases__[0].__subclasses__()
```

## 影响范围
- `security.md` - FORBIDDEN_ATTRIBUTES 列表
- `gsd_tasks.md` - Task 4 验证命令
- `eval/redteam.md` - 新增测试用例

## 变更内容
### security.md
```diff
FORBIDDEN_ATTRIBUTES = frozenset({
    "__subclasses__", "__bases__", "__mro__",
+   "__class__",  # 新增：防止 obj.__class__.__bases__ 链
    ...
})
```

### eval/redteam.md
```diff
+ // redteam_class_bypass_001.json
+ {
+   "id": "redteam_class_001",
+   "attack_vector": "class_chain_bypass",
+   "input": "obj.__class__.__bases__[0].__subclasses__()",
+   ...
+ }
```

## 验证
- [ ] 更新 security.md
- [ ] 更新 redteam.md
- [ ] 运行 `pytest tests/test_ast_gate.py -v`
- [ ] 继续 Task 4
```

## 4. Claude Code 迭代工作流

```
┌─────────────────────────────────────────────────────────────────┐
│                    正常开发流程                                   │
│                                                                  │
│  Task N ──► 实现 ──► 验证 ──► commit ──► Task N+1               │
│                │                                                 │
│                │ 遇到问题                                         │
│                ▼                                                 │
│  ┌─────────────────────────────────────────┐                    │
│  │         迭代流程 (PAUSE)                 │                    │
│  │                                          │                    │
│  │  1. 创建 spec/changes/00X-<name>.md     │                    │
│  │  2. 记录问题和影响范围                    │                    │
│  │  3. 更新相关 spec 文件                   │                    │
│  │  4. git commit -m "spec: <变更描述>"     │                    │
│  │  5. 继续实现                             │                    │
│  │                                          │                    │
│  └─────────────────────────────────────────┘                    │
│                │                                                 │
│                ▼                                                 │
│  Task N (继续) ──► 验证 ──► commit ──► Task N+1                 │
└─────────────────────────────────────────────────────────────────┘
```

## 5. 给 Claude Code 的指令模板

在开始开发前，告诉 Claude Code：

```
## 迭代协议

当你在实现过程中发现以下情况时，**不要硬编码解决方案**，而是：

1. 暂停当前任务
2. 创建 `spec/changes/NNN-<描述>.md` 记录问题
3. 提议对 spec 的修改
4. 等待我确认后再更新 spec
5. 然后继续实现

需要迭代的情况：
- 发现安全漏洞或绕过方式
- 数据模型需要变更
- 任务粒度不合适（太大或太小）
- 验收标准不完整或不正确
- 依赖问题无法解决

不需要迭代的情况：
- 纯实现细节（函数命名、代码风格）
- 已在 spec 范围内的技术选型
- 测试用例的具体实现
```

## 6. 版本控制策略

```bash
# Spec 变更单独提交
git add spec/
git commit -m "spec: add __class__ bypass detection (change-001)"

# 实现代码单独提交
git add src/ tests/
git commit -m "feat(ast-gate): implement __class__ attribute check"
```

## 7. 回顾检查点

每完成 2 个 Task，进行一次 spec 回顾：

```markdown
## Task 2 完成后回顾

### Spec 准确性
- [ ] overview.md 的目标仍然正确
- [ ] architecture.md 与实际实现一致
- [ ] security.md 覆盖了所有已知威胁

### 待处理变更
- change-001: 已合并
- change-002: 待讨论

### 下一步
继续 Task 3，重点关注...
```
