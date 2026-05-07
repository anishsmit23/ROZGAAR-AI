#!/bin/bash
# Quick testing script for ROZGAAR AI

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║       🧪 ROZGAAR AI - Testing Quick Start                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Installing..."
    pip install pytest pytest-asyncio pytest-cov
fi

echo "1️⃣  Running Unit Tests..."
pytest tests/unit/ -v --tb=short
UNIT_RESULT=$?

echo ""
echo "2️⃣  Running Integration Tests..."
pytest tests/integration/ -v --tb=short
INTEGRATION_RESULT=$?

echo ""
echo "3️⃣  Running All Tests with Coverage..."
pytest tests/ --cov=app --cov-report=term-missing -v
COVERAGE_RESULT=$?

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "📊 Test Results Summary"
echo "════════════════════════════════════════════════════════════════"

[ $UNIT_RESULT -eq 0 ] && echo "✅ Unit Tests PASSED" || echo "❌ Unit Tests FAILED"
[ $INTEGRATION_RESULT -eq 0 ] && echo "✅ Integration Tests PASSED" || echo "❌ Integration Tests FAILED"
[ $COVERAGE_RESULT -eq 0 ] && echo "✅ Coverage Report PASSED" || echo "❌ Coverage Report FAILED"

echo ""
echo "📋 For full testing guide, see: TESTING.md"
echo ""
