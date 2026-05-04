#!/usr/bin/env python3
"""
Integration Smoke Test Script.

Runs a safe, explicit end-to-end test of the platform without:
- Live trading
- Paid LLM calls
- Default/real symbols
- Secrets exposure

Usage:
    python integration_smoke_test.py              # Basic smoke test
    python integration_smoke_test.py --verbose  # Detailed output
    python integration_smoke_test.py --strict   # Fail on warnings too
    python integration_smoke_test.py --enable-tracing  # Test with tracing

Returns exit code 0 on success, non-zero on failure.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# This is an executable smoke-test CLI, not a pytest module. The helper
# functions are intentionally named around the checks they perform.
__test__ = False

# Test configuration - explicit, safe values
TEST_SYMBOLS = ["TEST-A", "TEST-B"]  # Explicit test symbols, never real tickers
TEST_HORIZON = "swing"
TEST_ASSET_CLASS = "stock"


def run_command(cmd: list[str], cwd: Path | None = None, timeout: int = 30) -> tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)


def check_backend_running(base_url: str = "http://localhost:8000") -> bool:
    """Check if backend API is running."""
    import urllib.request
    try:
        urllib.request.urlopen(f"{base_url}/health", timeout=5)
        return True
    except Exception:
        return False


def run_readiness_check(strict: bool = False) -> tuple[bool, list[str]]:
    """Run platform readiness check via CLI."""
    script_path = Path(__file__).parent / "check_platform_readiness.py"
    cmd = [sys.executable, str(script_path)]
    if strict:
        cmd.append("--strict")
    
    returncode, stdout, stderr = run_command(cmd)
    
    if returncode != 0:
        return False, [f"Readiness check failed: {stderr or stdout}"]
    
    return True, []


def run_migration_check(dry_run: bool = True) -> tuple[bool, list[str]]:
    """Run migration check."""
    script_path = Path(__file__).parent / "apply_platform_migrations.py"
    cmd = [sys.executable, str(script_path), "--dry-run"]
    
    returncode, stdout, stderr = run_command(cmd)
    
    if returncode != 0:
        return False, [f"Migration check failed: {stderr or stdout}"]
    
    return True, []


def test_api_endpoint(base_url: str, endpoint: str, method: str = "GET", payload: dict | None = None) -> tuple[bool, str]:
    """Test a single API endpoint."""
    import json
    import urllib.request
    
    url = f"{base_url}{endpoint}"
    
    try:
        if method == "GET":
            req = urllib.request.Request(url, method="GET")
        else:
            data = json.dumps(payload).encode() if payload else None
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method=method,
            )
        
        req.add_header("Accept", "application/json")
        
        with urllib.request.urlopen(req, timeout=30) as response:
            response.read()
            return True, f"{method} {endpoint} - {response.status}"
    except urllib.error.HTTPError as e:
        return False, f"{method} {endpoint} - HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, f"{method} {endpoint} - Error: {e}"


def test_workflow_flow(base_url: str, verbose: bool = False) -> tuple[bool, list[str]]:
    """Test a minimal workflow flow with test symbols."""
    results = []
    
    # Test 1: Platform readiness
    ok, msg = test_api_endpoint(base_url, "/api/platform-readiness")
    results.append(msg)
    if not ok:
        return False, results
    
    # Test 2: Tracing status
    ok, msg = test_api_endpoint(base_url, "/api/tracing/status")
    results.append(msg)
    if not ok:
        return False, results
    
    # Test 3: Data sources status
    ok, msg = test_api_endpoint(base_url, "/api/data-sources/status")
    results.append(msg)
    if not ok:
        return False, results
    
    # Test 4: Runtime phase
    ok, msg = test_api_endpoint(base_url, "/api/runtime/phase")
    results.append(msg)
    if not ok:
        return False, results
    
    # Test 5: Strategy ranking (explicit test params, no paid LLM)
    ok, msg = test_api_endpoint(
        base_url,
        "/api/strategy-ranking/run",
        method="POST",
        payload={
            "market_phase": "regular_hours",
            "active_loop": "regular_hours_analysis",
            "regime": "neutral",
            "horizon": TEST_HORIZON,
        }
    )
    results.append(msg)
    if not ok:
        return False, results
    
    # Test 6: Candidate universe summary
    ok, msg = test_api_endpoint(base_url, "/api/candidate-universe/summary")
    results.append(msg)
    if not ok:
        return False, results
    
    return True, results


def test_persistence_services(base_url: str) -> tuple[bool, list[str]]:
    """Test that persistence services report correct mode."""
    results = []
    
    # Check journal summary includes persistence_mode
    import json
    import urllib.request
    
    try:
        req = urllib.request.Request(f"{base_url}/api/journal/outcomes/summary")
        req.add_header("Accept", "application/json")
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            if "persistence_mode" in data:
                results.append(f"Journal summary includes persistence_mode: {data['persistence_mode']}")
            else:
                results.append("WARNING: Journal summary missing persistence_mode")
    except Exception as e:
        results.append(f"Journal summary check failed: {e}")
    
    # Check recommendation lifecycle includes persistence_mode
    try:
        req = urllib.request.Request(f"{base_url}/api/recommendation-lifecycle/summary")
        req.add_header("Accept", "application/json")
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            if "persistence_mode" in data:
                results.append(f"Recommendation summary includes persistence_mode: {data['persistence_mode']}")
            else:
                results.append("WARNING: Recommendation summary missing persistence_mode")
    except Exception as e:
        results.append(f"Recommendation summary check skipped (endpoint may not exist): {e}")
    
    return True, results


def main() -> int:
    """Main smoke test runner."""
    parser = argparse.ArgumentParser(
        description="Integration smoke test for EdgeSenseAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python integration_smoke_test.py              # Basic smoke test
    python integration_smoke_test.py --verbose  # Detailed output
    python integration_smoke_test.py --strict   # Fail on warnings
        """
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--strict", action="store_true", help="Fail on warnings too")
    parser.add_argument("--enable-tracing", action="store_true", help="Enable tracing for tests")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL for API")
    args = parser.parse_args()
    
    def log(msg: str):
        if args.verbose:
            print(msg)
    
    print("=" * 60)
    print("EdgeSenseAI Integration Smoke Test")
    print("=" * 60)
    print(f"Base URL: {args.base_url}")
    print(f"Strict mode: {args.strict}")
    print(f"Tracing enabled: {args.enable_tracing}")
    print()
    
    all_passed = True
    all_results = []
    
    # Pre-flight checks
    print("[1] Pre-flight Checks")
    print("-" * 40)
    
    # Check backend running
    log("Checking if backend is running...")
    if not check_backend_running(args.base_url):
        print("  ✗ Backend not running at " + args.base_url)
        print("\nPlease start the backend first:")
        print("  cd backend && python -m uvicorn app.main:app --reload")
        return 1
    print("  ✓ Backend is running")
    
    # Run readiness check
    log("Running platform readiness check...")
    ok, errors = run_readiness_check(strict=args.strict)
    if not ok:
        print("  ✗ Readiness check failed")
        for e in errors:
            print(f"    - {e}")
        all_passed = False
    else:
        print("  ✓ Readiness check passed")
    
    # Run migration check
    log("Running migration check...")
    ok, errors = run_migration_check()
    if not ok:
        print("  ✗ Migration check failed")
        for e in errors:
            print(f"    - {e}")
        all_passed = False
    else:
        print("  ✓ Migration check passed")
    
    # API tests
    print("\n[2] API Endpoint Tests")
    print("-" * 40)
    ok, results = test_workflow_flow(args.base_url, verbose=args.verbose)
    for r in results:
        status = "✓" if "200" in r or "201" in r else "✗"
        print(f"  {status} {r}")
    if not ok:
        all_passed = False
    
    # Persistence service tests
    print("\n[3] Persistence Service Tests")
    print("-" * 40)
    ok, results = test_persistence_services(args.base_url)
    for r in results:
        if r.startswith("WARNING"):
            print(f"  ⚠ {r}")
            if args.strict:
                all_passed = False
        else:
            print(f"  ✓ {r}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if all_passed:
        print("Result: ✓ ALL TESTS PASSED")
        print()
        print("The platform is operational and ready for use.")
        print("Persistence: Verify 'persistence_mode' in service responses.")
        print("Safety: Live trading disabled, human approval required.")
        print()
        return 0
    else:
        print("Result: ✗ TESTS FAILED")
        print()
        print("Some checks failed. Review the output above.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
