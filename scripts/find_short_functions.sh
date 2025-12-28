#!/bin/bash
# Find short functions that might be unnecessary wrappers
# Usage: ./scripts/find_short_functions.sh

echo "=== Functions that just return another method call ==="
grep -rn "def " apps/ --include="*.py" -A3 | grep -B3 "return " | grep -E "(def |return )"

echo ""
echo "=== Duplicate function definitions ==="
grep -rhn "^def \|^    def " apps/ --include="*.py" | cut -d: -f2 | sort | uniq -d
