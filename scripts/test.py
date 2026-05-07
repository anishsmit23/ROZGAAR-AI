#!/usr/bin/env python
"""Quick testing guide - Run this to test your ROZGAAR AI system."""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n{'='*60}")
    print(f"▶️  {description}")
    print(f"{'='*60}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=False)
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True
        else:
            print(f"❌ {description} - FAILED")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run testing suite."""
    print("""
╔════════════════════════════════════════════════════════════════╗
║       🧪 ROZGAAR AI - Testing Guide & Quick Start              ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    results = {}
    
    # Test 1: Unit tests
    results["Unit Tests"] = run_command(
        "pytest tests/unit/ -v",
        "Running Unit Tests (models, schemas)"
    )
    
    # Test 2: Integration tests
    results["Integration Tests"] = run_command(
        "pytest tests/integration/ -v",
        "Running Integration Tests (API, agents)"
    )
    
    # Test 3: All tests with coverage
    results["Coverage Report"] = run_command(
        "pytest tests/ --cov=app --cov-report=term-missing -v",
        "Running All Tests with Coverage Report"
    )
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 Test Summary")
    print(f"{'='*60}")
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:30} {status}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\nTotal: {passed}/{total} test suites passed")
    
    # Next steps
    print(f"\n{'='*60}")
    print("📋 Next Steps")
    print(f"{'='*60}")
    print("""
1. Start Docker environment:
   docker-compose up -d

2. Run migrations:
   docker-compose exec api alembic upgrade head

3. Test API with curl:
   curl http://localhost:8000/health

4. Access Streamlit UI:
   Open http://localhost:8501 in browser

5. View logs:
   docker-compose logs -f api

6. Run full test suite:
   pytest tests/ -v --cov=app
    """)
    
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
