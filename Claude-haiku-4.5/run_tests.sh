#!/usr/bin/env python3
"""
Test runner for Logistics Routing v2 integration tests.

Runs all integration tests, collects results, and generates metrics.

Usage:
    python run_tests.sh
    
Output:
    - Test results in console
    - JSON results in results/results_post.json
    - Metrics summary in results/test_metrics.json
"""

import subprocess
import sys
import json
import time
from pathlib import Path
from datetime import datetime


def run_integration_tests():
    """Run pytest on integration tests."""
    project_root = Path(__file__).parent
    tests_dir = project_root / "tests"
    results_dir = project_root / "results"
    results_dir.mkdir(exist_ok=True)
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║         Logistics Routing v2 - Integration Test Suite                ║
╚══════════════════════════════════════════════════════════════════════╝

Project Root: {project_root}
Tests Directory: {tests_dir}
Results Directory: {results_dir}

Running pytest on {tests_dir}/test_integration.py...
    """)
    
    # Run pytest with JSON output
    test_results_file = results_dir / "pytest_results.json"
    cmd = [
        sys.executable, "-m", "pytest",
        str(tests_dir / "test_integration.py"),
        "-v",
        "--tb=short",
        f"--json-report",
        f"--json-report-file={test_results_file}",
    ]
    
    start_time = time.time()
    result = subprocess.run(cmd)
    elapsed_sec = time.time() - start_time
    
    print(f"\n{'='*70}")
    print(f"Test execution completed in {elapsed_sec:.2f}s")
    print(f"{'='*70}\n")
    
    # Summarize results
    metrics = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "test_suite": "integration_tests",
        "total_duration_sec": elapsed_sec,
        "exit_code": result.returncode,
        "status": "PASSED" if result.returncode == 0 else "FAILED",
    }
    
    metrics_file = results_dir / "test_metrics.json"
    with open(metrics_file, "w") as f:
        json.dump(metrics, f, indent=2)
    
    print(f"✓ Metrics saved to: {metrics_file}")
    
    # Generate results summary
    results_summary = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "test_suite": "Logistics Routing v2 Integration Tests",
        "total_duration_sec": elapsed_sec,
        "exit_code": result.returncode,
        "status": "PASSED" if result.returncode == 0 else "FAILED",
        "test_categories": {
            "normal_path": {
                "test_case": "TC-001",
                "description": "Simple Dijkstra non-negative path",
                "expected_result": "SUCCESS"
            },
            "negative_weights": {
                "test_case": "TC-002",
                "description": "Bellman-Ford negative edges",
                "expected_result": "SUCCESS"
            },
            "negative_cycle": {
                "test_case": "TC-003",
                "description": "Negative cycle detection",
                "expected_result": "ERROR (NEG_CYCLE)"
            },
            "idempotency": {
                "test_case": "TC-004",
                "description": "Cache hit on identical request",
                "expected_result": "cache_hit=true, latency<5ms"
            },
            "validation_errors": {
                "test_case": "TC-005 to TC-007",
                "description": "Node not found, empty graph",
                "expected_result": "ERROR"
            },
            "edge_cases": {
                "test_case": "TC-008 to TC-009",
                "description": "Single node, disconnected graph",
                "expected_result": "SUCCESS or ERROR as expected"
            },
            "observability": {
                "test_case": "Logging tests",
                "description": "Structured JSON logs, request_id tracking",
                "expected_result": "All logs valid JSON with request_id"
            },
            "concurrency": {
                "test_case": "Thread-safety tests",
                "description": "10 concurrent requests",
                "expected_result": "SUCCESS, no race conditions"
            }
        },
        "acceptance_criteria": {
            "correctness": "100% match on all test cases",
            "idempotency": "Cache hit rate >= 60%",
            "latency": "p99 < 50ms for typical graphs",
            "reliability": "Error rate < 1.5%",
            "observability": "All requests traced with request_id"
        },
        "notes": "See results/pytest_results.json for detailed test results"
    }
    
    results_file = results_dir / "results_post.json"
    with open(results_file, "w") as f:
        json.dump(results_summary, f, indent=2)
    
    print(f"✓ Results summary saved to: {results_file}")
    
    return result.returncode


if __name__ == "__main__":
    exit_code = run_integration_tests()
    sys.exit(exit_code)
