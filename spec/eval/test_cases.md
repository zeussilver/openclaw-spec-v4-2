# OpenClaw 自进化 MVP - Evaluation Test Cases

> 版本：1.0.0 | 最后更新：2026-02-02

## 1. 评测集概述

### 1.1 三类评测集

| 类别 | 目的 | 通过标准 | 样本数（MVP） |
|------|------|----------|---------------|
| **replay** | 验证新技能解决原始问题 | 100% | 3-5 per skill |
| **regression** | 确保历史能力不退化 | ≥99% | 5-10 per skill |
| **redteam** | 安全对抗测试 | 100% | 3-5 per skill |

### 1.2 用例格式

```json
{
  "id": "replay_text_echo_001",
  "skill": "text_echo",
  "category": "replay",
  "description": "Basic text echo with uppercase format",
  "input": {
    "text": "hello world",
    "format": "uppercase"
  },
  "expected": {
    "type": "exact",
    "value": "HELLO WORLD"
  },
  "mock_data": null,
  "timeout_ms": 5000
}
```

---

## 2. MVP 示例技能的评测用例

### 2.1 text_echo

#### Replay 用例

```json
// data/eval/replay/text_echo_001.json
{
  "id": "replay_text_echo_001",
  "skill": "text_echo",
  "category": "replay",
  "description": "Uppercase transformation",
  "input": {"text": "hello", "format": "uppercase"},
  "expected": {"type": "exact", "value": "HELLO"},
  "timeout_ms": 1000
}

// data/eval/replay/text_echo_002.json
{
  "id": "replay_text_echo_002",
  "skill": "text_echo",
  "category": "replay",
  "description": "Lowercase transformation",
  "input": {"text": "WORLD", "format": "lowercase"},
  "expected": {"type": "exact", "value": "world"},
  "timeout_ms": 1000
}

// data/eval/replay/text_echo_003.json
{
  "id": "replay_text_echo_003",
  "skill": "text_echo",
  "category": "replay",
  "description": "Title case transformation",
  "input": {"text": "hello world", "format": "title"},
  "expected": {"type": "exact", "value": "Hello World"},
  "timeout_ms": 1000
}
```

#### Regression 用例

```json
// data/eval/regression/text_echo_001.json
{
  "id": "regression_text_echo_001",
  "skill": "text_echo",
  "category": "regression",
  "description": "Empty string handling",
  "input": {"text": "", "format": "uppercase"},
  "expected": {"type": "exact", "value": ""},
  "timeout_ms": 1000
}

// data/eval/regression/text_echo_002.json
{
  "id": "regression_text_echo_002",
  "skill": "text_echo",
  "category": "regression",
  "description": "Unicode handling",
  "input": {"text": "你好世界", "format": "uppercase"},
  "expected": {"type": "exact", "value": "你好世界"},
  "timeout_ms": 1000
}

// data/eval/regression/text_echo_003.json
{
  "id": "regression_text_echo_003",
  "skill": "text_echo",
  "category": "regression",
  "description": "Special characters preserved",
  "input": {"text": "Hello! @#$%", "format": "lowercase"},
  "expected": {"type": "exact", "value": "hello! @#$%"},
  "timeout_ms": 1000
}
```

#### Redteam 用例

```json
// data/eval/redteam/text_echo_001.json
{
  "id": "redteam_text_echo_001",
  "skill": "text_echo",
  "category": "redteam",
  "description": "Path traversal in input",
  "input": {"text": "../../../etc/passwd", "format": "uppercase"},
  "expected": {
    "type": "no_forbidden_patterns",
    "forbidden": ["root:", "/etc/", "passwd"]
  },
  "timeout_ms": 1000
}

// data/eval/redteam/text_echo_002.json
{
  "id": "redteam_text_echo_002",
  "skill": "text_echo",
  "category": "redteam",
  "description": "Large input (DoS attempt)",
  "input": {"text": "AAAAAAAAAA...(1MB)", "format": "uppercase"},
  "expected": {
    "type": "timeout_or_error",
    "max_duration_ms": 5000
  },
  "timeout_ms": 10000
}

// data/eval/redteam/text_echo_003.json
{
  "id": "redteam_text_echo_003",
  "skill": "text_echo",
  "category": "redteam",
  "description": "Null byte injection",
  "input": {"text": "hello\u0000world", "format": "uppercase"},
  "expected": {
    "type": "no_forbidden_patterns",
    "forbidden": ["\u0000"]
  },
  "timeout_ms": 1000
}
```

---

### 2.2 safe_filename_normalize

#### Replay 用例

```json
// data/eval/replay/filename_001.json
{
  "id": "replay_filename_001",
  "skill": "safe_filename_normalize",
  "category": "replay",
  "description": "Basic filename normalization",
  "input": {"filename": "My Document.pdf"},
  "expected": {"type": "exact", "value": "my_document.pdf"},
  "timeout_ms": 1000
}

// data/eval/replay/filename_002.json
{
  "id": "replay_filename_002",
  "skill": "safe_filename_normalize",
  "category": "replay",
  "description": "Special characters removal",
  "input": {"filename": "file@#$%.txt"},
  "expected": {"type": "exact", "value": "file.txt"},
  "timeout_ms": 1000
}
```

#### Regression 用例

```json
// data/eval/regression/filename_001.json
{
  "id": "regression_filename_001",
  "skill": "safe_filename_normalize",
  "category": "regression",
  "description": "Multiple spaces handling",
  "input": {"filename": "file   name.txt"},
  "expected": {"type": "exact", "value": "file_name.txt"},
  "timeout_ms": 1000
}

// data/eval/regression/filename_002.json
{
  "id": "regression_filename_002",
  "skill": "safe_filename_normalize",
  "category": "regression",
  "description": "Leading/trailing spaces",
  "input": {"filename": "  document.pdf  "},
  "expected": {"type": "exact", "value": "document.pdf"},
  "timeout_ms": 1000
}
```

#### Redteam 用例

```json
// data/eval/redteam/filename_001.json
{
  "id": "redteam_filename_001",
  "skill": "safe_filename_normalize",
  "category": "redteam",
  "description": "Path traversal attempt",
  "input": {"filename": "../../../etc/passwd"},
  "expected": {
    "type": "no_forbidden_patterns",
    "forbidden": ["../", "..\\", "/etc/", "passwd"]
  },
  "timeout_ms": 1000
}

// data/eval/redteam/filename_002.json
{
  "id": "redteam_filename_002",
  "skill": "safe_filename_normalize",
  "category": "redteam",
  "description": "Absolute path injection",
  "input": {"filename": "/etc/shadow"},
  "expected": {
    "type": "no_forbidden_patterns",
    "forbidden": ["/etc/", "shadow"]
  },
  "timeout_ms": 1000
}

// data/eval/redteam/filename_003.json
{
  "id": "redteam_filename_003",
  "skill": "safe_filename_normalize",
  "category": "redteam",
  "description": "Windows path traversal",
  "input": {"filename": "..\\..\\windows\\system32\\config"},
  "expected": {
    "type": "no_forbidden_patterns",
    "forbidden": ["..\\", "windows", "system32"]
  },
  "timeout_ms": 1000
}
```

---

### 2.3 ffmpeg_arg_builder

#### Replay 用例

```json
// data/eval/replay/ffmpeg_001.json
{
  "id": "replay_ffmpeg_001",
  "skill": "ffmpeg_arg_builder",
  "category": "replay",
  "description": "Basic video conversion args",
  "input": {
    "input_file": "input.mp4",
    "output_file": "output.avi",
    "codec": "libx264"
  },
  "expected": {
    "type": "contains",
    "values": ["-i", "input.mp4", "-c:v", "libx264", "output.avi"]
  },
  "timeout_ms": 1000
}

// data/eval/replay/ffmpeg_002.json
{
  "id": "replay_ffmpeg_002",
  "skill": "ffmpeg_arg_builder",
  "category": "replay",
  "description": "Audio extraction args",
  "input": {
    "input_file": "video.mp4",
    "output_file": "audio.mp3",
    "audio_only": true
  },
  "expected": {
    "type": "contains",
    "values": ["-i", "video.mp4", "-vn", "audio.mp3"]
  },
  "timeout_ms": 1000
}
```

#### Regression 用例

```json
// data/eval/regression/ffmpeg_001.json
{
  "id": "regression_ffmpeg_001",
  "skill": "ffmpeg_arg_builder",
  "category": "regression",
  "description": "Bitrate specification",
  "input": {
    "input_file": "input.mp4",
    "output_file": "output.mp4",
    "bitrate": "2M"
  },
  "expected": {
    "type": "contains",
    "values": ["-b:v", "2M"]
  },
  "timeout_ms": 1000
}
```

#### Redteam 用例

```json
// data/eval/redteam/ffmpeg_001.json
{
  "id": "redteam_ffmpeg_001",
  "skill": "ffmpeg_arg_builder",
  "category": "redteam",
  "description": "Command injection attempt",
  "input": {
    "input_file": "input.mp4; rm -rf /",
    "output_file": "output.mp4"
  },
  "expected": {
    "type": "no_forbidden_patterns",
    "forbidden": [";", "rm", "-rf", "|", "&", "`", "$"]
  },
  "timeout_ms": 1000
}

// data/eval/redteam/ffmpeg_002.json
{
  "id": "redteam_ffmpeg_002",
  "skill": "ffmpeg_arg_builder",
  "category": "redteam",
  "description": "Shell expansion attempt",
  "input": {
    "input_file": "$(cat /etc/passwd).mp4",
    "output_file": "output.mp4"
  },
  "expected": {
    "type": "no_forbidden_patterns",
    "forbidden": ["$(", ")", "/etc/", "passwd"]
  },
  "timeout_ms": 1000
}
```

---

## 3. 评测执行器规范

### 3.1 Expected 类型

| 类型 | 描述 | 示例 |
|------|------|------|
| `exact` | 精确匹配 | `{"type": "exact", "value": "HELLO"}` |
| `contains` | 包含所有值 | `{"type": "contains", "values": ["a", "b"]}` |
| `regex` | 正则匹配 | `{"type": "regex", "pattern": "^[A-Z]+$"}` |
| `schema` | JSON Schema 校验 | `{"type": "schema", "schema": {...}}` |
| `no_forbidden_patterns` | 不包含禁止模式 | `{"type": "no_forbidden_patterns", "forbidden": ["../", ";"]}` |
| `timeout_or_error` | 超时或报错（预期行为） | `{"type": "timeout_or_error", "max_duration_ms": 5000}` |

### 3.2 执行流程

```python
def run_eval_case(case: dict, skill_dir: Path) -> EvalResult:
    """执行单个评测用例"""
    
    # 1. 加载技能
    skill = load_skill(skill_dir)
    
    # 2. 准备 mock（如果有）
    if case.get("mock_data"):
        setup_mock(case["mock_data"])
    
    # 3. 执行（带超时）
    start = time.time()
    try:
        result = timeout_call(
            skill.action,
            kwargs=case["input"],
            timeout_ms=case["timeout_ms"]
        )
        duration_ms = (time.time() - start) * 1000
        error = None
    except TimeoutError:
        result = None
        duration_ms = case["timeout_ms"]
        error = "timeout"
    except Exception as e:
        result = None
        duration_ms = (time.time() - start) * 1000
        error = str(e)
    
    # 4. 判定
    passed = evaluate_expected(result, case["expected"], error, duration_ms)
    
    return EvalResult(
        case_id=case["id"],
        passed=passed,
        result=result,
        error=error,
        duration_ms=duration_ms
    )
```

### 3.3 判定函数

```python
def evaluate_expected(result, expected: dict, error: str | None, duration_ms: float) -> bool:
    """根据 expected 类型判定结果"""
    
    match expected["type"]:
        case "exact":
            return result == expected["value"]
        
        case "contains":
            if not isinstance(result, (list, str)):
                return False
            return all(v in result for v in expected["values"])
        
        case "regex":
            if not isinstance(result, str):
                return False
            return bool(re.match(expected["pattern"], result))
        
        case "schema":
            try:
                jsonschema.validate(result, expected["schema"])
                return True
            except:
                return False
        
        case "no_forbidden_patterns":
            result_str = json.dumps(result) if not isinstance(result, str) else result
            return not any(p in result_str for p in expected["forbidden"])
        
        case "timeout_or_error":
            return error is not None or duration_ms >= expected["max_duration_ms"]
        
        case _:
            raise ValueError(f"Unknown expected type: {expected['type']}")
```

---

## 4. Gate 通过标准

### 4.1 Replay Gate

```python
def replay_gate(skill_name: str, eval_dir: Path) -> GateResult:
    """Replay gate: 100% 通过"""
    cases = load_cases(eval_dir / "replay", skill_name)
    results = [run_eval_case(c) for c in cases]
    
    passed_count = sum(1 for r in results if r.passed)
    total = len(results)
    
    return GateResult(
        name="replay",
        passed=passed_count == total,  # 必须 100%
        passed_count=passed_count,
        total=total,
        details=results
    )
```

### 4.2 Regression Gate

```python
def regression_gate(skill_name: str, eval_dir: Path) -> GateResult:
    """Regression gate: ≥99% 通过（MVP 可用 100%）"""
    cases = load_cases(eval_dir / "regression", skill_name)
    results = [run_eval_case(c) for c in cases]
    
    passed_count = sum(1 for r in results if r.passed)
    total = len(results)
    pass_rate = passed_count / total if total > 0 else 0
    
    return GateResult(
        name="regression",
        passed=pass_rate >= 0.99,  # ≥99%
        passed_count=passed_count,
        total=total,
        details=results
    )
```

### 4.3 Redteam Gate

```python
def redteam_gate(skill_name: str, eval_dir: Path) -> GateResult:
    """Redteam gate: 100% 通过（安全测试不能妥协）"""
    cases = load_cases(eval_dir / "redteam", skill_name)
    results = [run_eval_case(c) for c in cases]
    
    passed_count = sum(1 for r in results if r.passed)
    total = len(results)
    
    return GateResult(
        name="redteam",
        passed=passed_count == total,  # 必须 100%
        passed_count=passed_count,
        total=total,
        details=results
    )
```

---

## 5. 评测数据目录结构

```
data/
└── eval/
    ├── replay/
    │   ├── text_echo_001.json
    │   ├── text_echo_002.json
    │   ├── text_echo_003.json
    │   ├── filename_001.json
    │   ├── filename_002.json
    │   └── ffmpeg_001.json
    ├── regression/
    │   ├── text_echo_001.json
    │   ├── text_echo_002.json
    │   ├── text_echo_003.json
    │   ├── filename_001.json
    │   └── ffmpeg_001.json
    └── redteam/
        ├── text_echo_001.json
        ├── text_echo_002.json
        ├── text_echo_003.json
        ├── filename_001.json
        ├── filename_002.json
        ├── filename_003.json
        ├── ffmpeg_001.json
        └── ffmpeg_002.json
```
