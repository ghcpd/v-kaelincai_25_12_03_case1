# 测试执行指南 (Test Execution Guide)

## 快速开始 (Quick Start)

### 方法 1: 运行所有测试 (Run All Tests - RECOMMENDED)

打开 PowerShell，进入项目目录：

```powershell
cd c:\c\c\workspace\Claude-haiku-4.5
```

然后运行：

```powershell
.\.venv\Scripts\pytest tests/test_production_integration.py tests/test_issue_validation.py -v
```

**预期结果：**
- 21 个测试全部通过 ✓
- 执行时间：0.16 秒
- 总结：`21 passed, 31 warnings`

---

## 详细命令说明 (Detailed Commands)

### 1️⃣ 运行生产环境集成测试 (Production Integration Tests)

```powershell
.\.venv\Scripts\pytest tests/test_production_integration.py -v
```

**测试内容：**
- 非负权重的最短路径 (Dijkstra)
- 负权重自动选择 Bellman-Ford
- 负循环检测
- 缓存验证
- 验证错误处理
- 并发测试
- 日志记录

**预期结果：** 14 个测试通过

---

### 2️⃣ 运行原问题验证测试 (Issue Validation Tests)

```powershell
.\.venv\Scripts\pytest tests/test_issue_validation.py -v
```

**测试内容：**
- 验证负权重问题已修复
- 验证最优路径正确计算
- 验证负循环检测
- 验证边界情况处理

**预期结果：** 7 个测试通过

---

### 3️⃣ 运行特定测试类 (Run Specific Test Class)

```powershell
.\.venv\Scripts\pytest tests/test_production_integration.py::TestNormalPath -v
```

**选项：**
- `TestNormalPath` - 正常路径测试
- `TestNegativeWeights` - 负权重测试
- `TestNegativeCycleDetection` - 循环检测
- `TestIdempotency` - 缓存测试
- `TestValidationErrors` - 验证错误
- `TestEdgeCases` - 边界情况
- `TestComplexScenarios` - 复杂场景
- `TestTimeout` - 超时处理
- `TestObservability` - 日志记录
- `TestConcurrency` - 并发测试

---

### 4️⃣ 运行单个测试 (Run Single Test)

```powershell
.\.venv\Scripts\pytest tests/test_production_integration.py::TestNormalPath::test_simple_dijkstra_path -v
```

---

### 5️⃣ 显示详细错误信息 (Show Detailed Output)

```powershell
.\.venv\Scripts\pytest tests/test_production_integration.py tests/test_issue_validation.py -v --tb=long
```

**选项说明：**
- `-v` = 详细输出 (verbose)
- `--tb=short` = 简短错误追踪
- `--tb=long` = 详细错误追踪
- `--tb=line` = 单行错误

---

### 6️⃣ 显示覆盖率 (Show Coverage - if coverage installed)

```powershell
.\.venv\Scripts\pytest tests/test_production_integration.py tests/test_issue_validation.py --cov=src --cov-report=term
```

---

## 完整测试输出示例 (Full Output Example)

```
================= test session starts =================
platform win32 -- Python 3.13.9, pytest-9.0.1

collected 21 items

tests/test_production_integration.py::TestNormalPath::test_simple_dijkstra_path PASSED [  4%]
tests/test_production_integration.py::TestNegativeWeights::test_negative_edge_bellman_ford PASSED [  9%]
...
tests/test_issue_validation.py::TestEdgeCaseHandling::test_v2_handles_unreachable_goal PASSED [100%]

=================== 21 passed in 0.16s =================
```

---

## 测试结果解释 (Test Results Explanation)

| 符号 | 含义 | 说明 |
|------|------|------|
| ✓ PASSED | 通过 | 测试成功 |
| ✗ FAILED | 失败 | 测试失败，查看错误信息 |
| ⊘ SKIPPED | 跳过 | 测试被跳过 |
| ⚠ WARNING | 警告 | 警告信息（不影响测试结果） |

---

## 预期测试结果 (Expected Results)

### ✅ 全部通过的情况

```
======================= 21 passed, 31 warnings in 0.16s =======================
```

这表示：
- 所有 21 个测试都通过了 ✓
- 有 31 条警告信息（主要是关于 datetime.utcnow() 的弃用警告，不影响功能）
- 执行时间约 0.16 秒

### 🟡 有警告但测试通过

- 左下角的 `DeprecationWarning` 是 Python 3.13 的弃用警告
- 不影响测试结果
- 可以忽略

---

## 常见问题 (FAQs)

### Q1: 如何只查看失败的测试？

```powershell
.\.venv\Scripts\pytest tests/test_production_integration.py tests/test_issue_validation.py -v --tb=short -x
```

参数 `-x` 会在第一个失败处停止

---

### Q2: 如何并行运行测试（更快）？

首先安装 pytest-xdist：

```powershell
.\.venv\Scripts\pip install pytest-xdist
```

然后运行：

```powershell
.\.venv\Scripts\pytest tests/test_production_integration.py tests/test_issue_validation.py -v -n auto
```

---

### Q3: 如何保存测试结果到文件？

```powershell
.\.venv\Scripts\pytest tests/test_production_integration.py tests/test_issue_validation.py -v > test_results.log 2>&1
```

然后查看 `test_results.log` 文件

---

### Q4: 如果测试失败了怎么办？

1. 查看错误信息 (AssertionError)
2. 查看错误堆栈信息 (Traceback)
3. 检查 `VALIDATION_REPORT.md` 文件获取详细信息
4. 确保虚拟环境已激活

---

## 关键文件位置 (Important Files)

```
Claude-haiku-4.5/
├── src/
│   └── routing_v2.py              ← 生产代码 (Production Code)
├── tests/
│   ├── test_production_integration.py  ← 集成测试 (Integration Tests) ✅ 14 tests
│   └── test_issue_validation.py       ← 问题验证 (Issue Validation) ✅ 7 tests
├── test_data.json                 ← 测试数据 (Test Data)
├── VALIDATION_REPORT.md           ← 验证报告 (Validation Report)
└── test_results.txt               ← 原始测试结果 (Raw Results)
```

---

## 总结 (Summary)

✅ **推荐命令** (Recommended Command):
```powershell
cd c:\c\c\workspace\Claude-haiku-4.5
.\.venv\Scripts\pytest tests/test_production_integration.py tests/test_issue_validation.py -v
```

✅ **预期结果** (Expected Result):
```
======================= 21 passed, 31 warnings in 0.16s =======================
```

✅ **项目状态** (Project Status):
- 所有测试通过 ✓
- 原问题已修复 ✓
- 生产环境已准备好 ✓

---

有任何问题，请查看 `VALIDATION_REPORT.md` 获取更多详细信息！
