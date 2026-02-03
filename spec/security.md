# OpenClaw Project A - Security

> 版本：2.0.0 | 最后更新：2026-02-03
>
> 范围：Project A (Secure Skill Lifecycle Manager)

## 1. 安全原则

- **默认零信任**：所有 LLM 生成的代码都被视为不可信
- **纵深防御**：静态检查 + 运行时沙盒 + 评测 gate 三层防护
- **最小权限**：技能只能访问必要的资源
- **可审计**：所有操作都有日志和 hash 追溯

---

## 2. 威胁模型

### 2.1 威胁来源

| 来源 | 描述 | 风险等级 |
|------|------|----------|
| LLM 生成代码 | 可能包含恶意或有缺陷的代码 | **高** |
| 评测数据 | 可能被污染以绕过 gate | 中 |
| 依赖包 | 可能有漏洞或后门 | 中 |
| 配置文件 | 可能被篡改 | 低 |

### 2.2 攻击向量（MVP 重点防护）

#### 2.2.1 绕过验证
| 攻击 | 描述 | 防护措施 |
|------|------|----------|
| SystemExit 绕过 | `raise SystemExit(0)` 提前退出 | Runner 捕获 `BaseException` |
| KeyboardInterrupt | 模拟用户中断 | Runner 捕获 `BaseException` |
| 异常逃逸 | 异常后继续执行 | 只有 `verify() is True` 才算通过 |

#### 2.2.2 危险导入
| 攻击 | 描述 | 防护措施 |
|------|------|----------|
| 直接导入 | `import os` | 顶层模块白名单 |
| 动态导入 | `__import__('os')` | 禁止 `__import__` 调用 |
| builtins 绕过 | `builtins.__import__` | AST 检查属性访问 |
| getattr 绕过 | `getattr(__builtins__, '__import__')` | 禁止 `getattr` 调用 |
| globals 绕过 | `globals()['__builtins__']` | 禁止 `globals` 调用 |

#### 2.2.3 沙箱逃逸
| 攻击 | 描述 | 防护措施 |
|------|------|----------|
| 子类链攻击 | `().__class__.__bases__[0].__subclasses__()` | 禁止 `__subclasses__` 等属性 |
| 代码对象访问 | `func.__code__` | 禁止 `__code__` 访问 |
| 全局变量访问 | `func.__globals__` | 禁止 `__globals__` 访问 |

#### 2.2.4 文件系统攻击
| 攻击 | 描述 | 防护措施 |
|------|------|----------|
| 路径穿越 | `../../../etc/passwd` | AST 检查 + Docker 只读 |
| 任意文件写 | `open('/etc/cron.d/...', 'w')` | 禁止 `open`，Docker 只读 |
| 符号链接攻击 | 创建指向敏感文件的链接 | Docker 只读根文件系统 |

#### 2.2.5 资源滥用
| 攻击 | 描述 | 防护措施 |
|------|------|----------|
| Fork bomb | 无限创建进程 | `--pids-limit 128` |
| 死循环 | CPU 耗尽 | `--cpus 1` + timeout |
| 内存爆 | 无限分配内存 | `--memory 512m` |
| 网络外联 | 数据泄露 | `--network none` |

---

## 3. 静态安全门（AST Gate）

### 3.1 检查项

#### 3.1.1 导入检查

```python
# 允许的顶层模块（完整列表）
ALLOWED_TOP_LEVEL_MODULES = frozenset({
    # 数据处理
    "json", "csv", "xml",
    # 字符串与正则
    "re", "string", "textwrap",
    # 路径（安全使用）
    "pathlib",
    # 时间
    "datetime", "time", "calendar",
    # 类型
    "typing", "types", "dataclasses", "enum",
    # 集合与迭代
    "collections", "itertools", "functools",
    # 数学
    "math", "decimal", "fractions", "statistics", "random",
    # 编码
    "hashlib", "base64", "binascii",
    # URL 解析（不含 urlopen）
    "urllib",
    # 工具
    "copy", "pprint", "operator",
    # 上下文
    "contextlib",
    # ABC
    "abc",
})

# 检查逻辑
def check_import(node: ast.Import | ast.ImportFrom) -> list[str]:
    violations = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            top_level = alias.name.split('.')[0]
            if top_level not in ALLOWED_TOP_LEVEL_MODULES:
                violations.append(f"禁止导入: {alias.name}")
    elif isinstance(node, ast.ImportFrom):
        if node.module:
            top_level = node.module.split('.')[0]
            if top_level not in ALLOWED_TOP_LEVEL_MODULES:
                violations.append(f"禁止从 {node.module} 导入")
    return violations
```

#### 3.1.2 调用检查

```python
FORBIDDEN_CALLS = frozenset({
    # 动态执行
    "__import__", "eval", "exec", "compile",
    # 文件操作
    "open", "input",
    # 反射（可用于绕过）
    "getattr", "setattr", "delattr",
    # 作用域访问
    "globals", "locals", "vars",
    # 调试
    "breakpoint",
})

def check_call(node: ast.Call) -> list[str]:
    violations = []
    # 检查直接调用: func_name(...)
    if isinstance(node.func, ast.Name):
        if node.func.id in FORBIDDEN_CALLS:
            violations.append(f"禁止调用: {node.func.id}")
    # 检查属性调用: obj.func_name(...)
    elif isinstance(node.func, ast.Attribute):
        if node.func.attr in FORBIDDEN_CALLS:
            violations.append(f"禁止调用: {node.func.attr}")
    return violations
```

#### 3.1.3 属性访问检查

```python
FORBIDDEN_ATTRIBUTES = frozenset({
    # 类型系统攻击
    "__subclasses__", "__bases__", "__mro__",
    # 代码对象
    "__globals__", "__code__", "__closure__",
    # 内置
    "__builtins__", "__import__",
    # 模块加载
    "__loader__", "__spec__",
})

def check_attribute(node: ast.Attribute) -> list[str]:
    violations = []
    if node.attr in FORBIDDEN_ATTRIBUTES:
        violations.append(f"禁止访问属性: {node.attr}")
    return violations
```

#### 3.1.4 字符串模式检查

```python
SUSPICIOUS_PATTERNS = [
    r'\.\./',           # 路径穿越
    r'\.\.\\',          # Windows 路径穿越
    r'/etc/',           # 系统目录
    r'/proc/',          # proc 文件系统
    r'/sys/',           # sys 文件系统
    r'~/',              # 用户目录
]

def check_strings(code: str) -> list[str]:
    violations = []
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, code):
            violations.append(f"发现可疑模式: {pattern}")
    return violations
```

### 3.2 AST Gate 完整实现框架

```python
class ASTGate:
    def check(self, code: str) -> tuple[bool, list[str]]:
        """
        返回 (passed, violations)
        """
        violations = []
        
        # 1. 字符串模式检查
        violations.extend(self.check_strings(code))
        
        # 2. AST 解析
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, [f"语法错误: {e}"]
        
        # 3. 遍历 AST
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                violations.extend(self.check_import(node))
            elif isinstance(node, ast.Call):
                violations.extend(self.check_call(node))
            elif isinstance(node, ast.Attribute):
                violations.extend(self.check_attribute(node))
        
        return len(violations) == 0, violations
```

---

## 4. 运行时沙盒（Docker）

### 4.1 Docker 运行参数

```bash
docker run \
    --rm \
    --network none \                    # 禁用网络
    --read-only \                       # 只读根文件系统
    --cpus 1 \                          # 限制 CPU
    --memory 512m \                     # 限制内存
    --memory-swap 512m \                # 禁用 swap
    --pids-limit 128 \                  # 限制进程数
    --cap-drop ALL \                    # 移除所有 capabilities
    --security-opt no-new-privileges:true \  # 禁止提权
    --tmpfs /tmp:size=64m,noexec \      # 受限的 /tmp
    -v /host/skill:/skill:ro \          # 只读挂载技能
    -v /host/output:/output:rw \        # 可写输出目录
    openclaw-sandbox:latest \
    python /sandbox/harness.py /skill
```

### 4.2 Dockerfile.sandbox

```dockerfile
FROM python:3.11-slim

# 安装允许的依赖（预装，运行时不可安装新包）
COPY requirements.allowlist.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.allowlist.txt \
    && rm /tmp/requirements.allowlist.txt \
    && rm -rf /root/.cache

# 删除 pip 防止运行时安装
RUN rm -rf /usr/local/bin/pip* /usr/local/lib/python*/dist-packages/pip*

# 复制 harness
COPY sandbox/harness.py /sandbox/

# 创建非 root 用户
RUN useradd -m -s /bin/false sandbox
USER sandbox

WORKDIR /work
```

### 4.3 Harness 实现

```python
#!/usr/bin/env python3
"""sandbox/harness.py - 容器内技能验证入口"""
import sys
import importlib.util
import traceback

VERIFICATION_SUCCESS = "VERIFICATION_SUCCESS"
VERIFICATION_FAILED = "VERIFICATION_FAILED"

def main(skill_path: str) -> int:
    try:
        # 加载技能模块
        spec = importlib.util.spec_from_file_location("skill", f"{skill_path}/skill.py")
        if spec is None or spec.loader is None:
            print(f"{VERIFICATION_FAILED}: 无法加载技能模块")
            return 1
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 检查必要函数存在
        if not hasattr(module, 'verify'):
            print(f"{VERIFICATION_FAILED}: 缺少 verify() 函数")
            return 1
        
        if not hasattr(module, 'action'):
            print(f"{VERIFICATION_FAILED}: 缺少 action() 函数")
            return 1
        
        # 执行 verify()
        result = module.verify()
        
        # 严格检查返回值
        if result is True:
            print(VERIFICATION_SUCCESS)
            return 0
        else:
            print(f"{VERIFICATION_FAILED}: verify() 返回 {result!r}，期望 True")
            return 1
            
    except BaseException as e:
        # 捕获所有异常，包括 SystemExit, KeyboardInterrupt
        print(f"{VERIFICATION_FAILED}: {type(e).__name__}: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <skill_path>")
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
```

### 4.4 Runner 实现要点

```python
import docker
from docker.errors import ContainerError, ImageNotFound, APIError

class SandboxRunner:
    def __init__(self, image: str = "openclaw-sandbox:latest", timeout: int = 30):
        self.client = docker.from_env()
        self.image = image
        self.timeout = timeout
    
    def run(self, skill_path: Path, output_path: Path) -> tuple[bool, str, dict]:
        """
        运行技能验证
        返回: (passed, logs, metrics)
        """
        container = None
        logs = ""
        
        try:
            container = self.client.containers.run(
                self.image,
                command=["python", "/sandbox/harness.py", "/skill"],
                volumes={
                    str(skill_path): {"bind": "/skill", "mode": "ro"},
                    str(output_path): {"bind": "/output", "mode": "rw"},
                },
                network_mode="none",
                read_only=True,
                mem_limit="512m",
                memswap_limit="512m",
                cpu_period=100000,
                cpu_quota=100000,  # 1 CPU
                pids_limit=128,
                cap_drop=["ALL"],
                security_opt=["no-new-privileges:true"],
                tmpfs={"/tmp": "size=64m,noexec"},
                detach=True,
            )
            
            # 等待完成，带超时
            result = container.wait(timeout=self.timeout)
            logs = container.logs().decode("utf-8", errors="replace")
            
            # 检查退出码和输出
            exit_code = result.get("StatusCode", 1)
            passed = exit_code == 0 and "VERIFICATION_SUCCESS" in logs
            
            return passed, logs, {"exit_code": exit_code}
            
        except Exception as e:
            # 超时或其他错误
            if container:
                try:
                    logs = container.logs().decode("utf-8", errors="replace")
                except:
                    pass
            return False, f"{logs}\nRunner error: {e}", {}
            
        finally:
            # 确保清理
            if container:
                try:
                    container.kill()
                except:
                    pass
                try:
                    container.remove(force=True)
                except:
                    pass
```

---

## 5. 依赖治理

### 5.1 Allowlist

```
# requirements.allowlist.txt
# 只有这些包可以被技能使用

# 数据验证
pydantic==2.5.0
jsonschema==4.20.0

# HTTP（若未来允许受控网络）
# requests==2.31.0  # MVP 禁用

# 数据处理
# pandas==2.1.0     # MVP 禁用，太大

# 测试（沙盒内需要）
pytest==7.4.0
```

### 5.2 版本锁定

- 使用 `uv.lock` 或 `requirements.lock` 锁定所有依赖版本
- Registry 记录每个技能版本对应的依赖 hash
- 构建 Docker 镜像时固定依赖版本

---

## 6. 审计与日志

### 6.1 Registry 审计字段

```json
{
  "name": "text_echo",
  "versions": {
    "1.0.0": {
      "code_hash": "sha256:abc123...",
      "manifest_hash": "sha256:def456...",
      "created_at": "2026-02-01T10:00:00Z",
      "created_by": "night_evolver",
      "status": "prod",
      "validation": {
        "ast_gate": {"passed": true, "violations": []},
        "sandbox": {"passed": true, "exit_code": 0, "duration_ms": 1234},
        "promote_gate": {
          "replay": {"passed": true, "total": 5, "passed_count": 5},
          "regression": {"passed": true, "total": 10, "passed_count": 10},
          "redteam": {"passed": true, "total": 3, "passed_count": 3}
        }
      },
      "promoted_at": "2026-02-01T12:00:00Z",
      "disabled_at": null,
      "disabled_reason": null
    }
  }
}
```

### 6.2 操作日志

所有关键操作写入 `data/audit.log`：

```
2026-02-01T10:00:00Z [GENERATE] skill=text_echo version=1.0.0 provider=mock
2026-02-01T10:00:01Z [AST_GATE] skill=text_echo version=1.0.0 passed=true
2026-02-01T10:00:05Z [SANDBOX] skill=text_echo version=1.0.0 passed=true duration=3.2s
2026-02-01T10:00:06Z [STAGING] skill=text_echo version=1.0.0
2026-02-01T12:00:00Z [PROMOTE] skill=text_echo version=1.0.0 gates=replay,regression,redteam
2026-02-02T08:00:00Z [ROLLBACK] skill=text_echo from=1.0.0 to=0.9.0 reason="regression failure"
```

---

## 7. LLM/审查者检查清单

在审查本系统安全性时，请重点关注：

- [ ] AST Gate 是否能被绕过（`__import__`、`getattr`、`globals` 等）
- [ ] Runner 是否正确捕获 `BaseException`
- [ ] `verify()` 返回值是否严格检查 `is True`
- [ ] Docker 是否真正零信任（network/read-only/caps/pids/timeout）
- [ ] 白名单解析口径是否一致（顶层模块名）
- [ ] Promote gate 是否与文档一致并可执行
- [ ] 超时后容器是否被正确清理
- [ ] 日志是否在 kill 前被保留
