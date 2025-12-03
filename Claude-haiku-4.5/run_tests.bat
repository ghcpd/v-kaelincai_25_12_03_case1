@echo off
REM 快速测试运行脚本 (Quick Test Runner Script)

cd /d "%~dp0"

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║          Logistics Routing v2 - 测试运行 (Test Runner)         ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM 检查虚拟环境
if not exist ".venv\Scripts\pytest.exe" (
    echo ❌ 错误: 虚拟环境未找到
    echo 请先运行: python -m venv .venv
    echo 然后运行: .venv\Scripts\pip install pytest
    exit /b 1
)

echo ✓ 虚拟环境已就绪
echo.

REM 显示菜单
echo 选择要运行的测试:
echo.
echo [1] 运行所有测试 (All Tests) - 推荐
echo [2] 运行生产集成测试 (Production Integration Tests)
echo [3] 运行问题验证测试 (Issue Validation Tests)
echo [4] 运行特定测试类 (Specific Test Class)
echo [5] 显示详细错误信息 (Detailed Output)
echo [6] 保存结果到文件 (Save to File)
echo [0] 退出 (Exit)
echo.

set /p choice="请选择 (1-6, 0 退出): "

if "%choice%"=="1" (
    echo.
    echo 运行所有测试...
    echo.
    call .venv\Scripts\pytest tests/test_production_integration.py tests/test_issue_validation.py -v --tb=short
    goto end
)

if "%choice%"=="2" (
    echo.
    echo 运行生产集成测试 (14 tests)...
    echo.
    call .venv\Scripts\pytest tests/test_production_integration.py -v --tb=short
    goto end
)

if "%choice%"=="3" (
    echo.
    echo 运行问题验证测试 (7 tests)...
    echo.
    call .venv\Scripts\pytest tests/test_issue_validation.py -v --tb=short
    goto end
)

if "%choice%"=="4" (
    echo.
    set /p testclass="输入测试类名 (例如: TestNormalPath): "
    echo 运行测试类: %testclass%
    echo.
    call .venv\Scripts\pytest tests/test_production_integration.py::%testclass% -v --tb=short
    goto end
)

if "%choice%"=="5" (
    echo.
    echo 运行所有测试 (显示详细错误)...
    echo.
    call .venv\Scripts\pytest tests/test_production_integration.py tests/test_issue_validation.py -v --tb=long
    goto end
)

if "%choice%"=="6" (
    echo.
    echo 保存测试结果到 test_results_latest.log...
    echo.
    call .venv\Scripts\pytest tests/test_production_integration.py tests/test_issue_validation.py -v > test_results_latest.log 2>&1
    echo ✓ 结果已保存到: test_results_latest.log
    echo.
    goto end
)

if "%choice%"=="0" (
    echo 退出...
    exit /b 0
)

echo ❌ 无效选择
goto menu

:end
echo.
echo ✓ 测试完成
echo.
pause
