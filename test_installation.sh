#!/bin/bash
# Test PiSecure installation methods
# This script verifies that all installation options work correctly

# Note: Don't use set -e because we want to continue testing even if some tests fail

echo "========================================================================"
echo "  PiSecure Installation Test Suite"
echo "========================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -e "${YELLOW}Testing: ${test_name}${NC}"
    
    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}: $test_name"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}: $test_name"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test 1: Check setup.py exists and is valid
run_test "setup.py exists" "test -f setup.py"

# Test 2: Check setup.py can be parsed
run_test "setup.py syntax" "python setup.py --version"

# Test 3: Check MANIFEST.in exists
run_test "MANIFEST.in exists" "test -f MANIFEST.in"

# Test 4: Check all required dependencies are listed
run_test "Core dependencies listed" "grep -q 'cryptography' setup.py"

# Test 5: Check native extension support
run_test "Native extension defined" "grep -q '_pihash_native' setup.py"

# Test 6: Check extras_require includes native
run_test "Native extras defined" "grep -q \"'native'\" setup.py"

# Test 7: Check entry points defined
run_test "CLI entry point defined" "grep -q 'pisecure=pisecure.cli:main' setup.py"

# Test 8: Verify Cython source exists
run_test "Cython source exists" "test -f pisecure/core/_pihash_native.pyx"

# Test 9: Verify build script exists
run_test "Build script exists" "test -f pisecure/core/build_pihash_native.py"

# Test 10: Check README exists
run_test "README exists" "test -f README.md"

# Test 11: Check LICENSE exists
run_test "LICENSE exists" "test -f LICENSE"

# Test 12: Check package structure
run_test "Package __init__.py exists" "test -f pisecure/__init__.py"

# Test 13: Check version can be imported
run_test "Version importable" "python -c 'import sys; sys.path.insert(0, \".\"); from pisecure import __version__'"

# Test 14: Check pyproject.toml exists
run_test "pyproject.toml exists" "test -f pyproject.toml"

# Test 15: Dry-run installation check
echo ""
echo "Testing installation scenarios..."
echo ""

# Create temp venv for testing
TEST_VENV="/tmp/pisecure_test_venv_$$"
python3 -m venv "$TEST_VENV" > /dev/null 2>&1

# Test 16: Basic install (dry-run)
if [ -d "$TEST_VENV" ]; then
    run_test "Basic install (dry-run)" "$TEST_VENV/bin/pip install -e . --dry-run"
fi

# Test 17: Native install check (dry-run)
if [ -d "$TEST_VENV" ]; then
    run_test "Native install (dry-run)" "$TEST_VENV/bin/pip install -e '.[native]' --dry-run"
fi

# Cleanup
rm -rf "$TEST_VENV" 2>/dev/null

# Summary
echo ""
echo "========================================================================"
echo "  Test Summary"
echo "========================================================================"
echo -e "Tests passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "Tests failed: ${RED}${TESTS_FAILED}${NC}"
echo "Total tests: $((TESTS_PASSED + TESTS_FAILED))"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed! Installation is ready.${NC}"
    echo ""
    echo "To install PiSecure:"
    echo "  pip install .                    # Basic"
    echo "  pip install '.[native]'          # With 5-10x speedup"
    echo "  pip install '.[full,native]'     # All features"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please review the errors above.${NC}"
    exit 1
fi
