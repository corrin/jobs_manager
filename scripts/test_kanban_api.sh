#!/bin/bash
# Test Kanban API - verifies the API is working correctly
# Usage: ./scripts/test_kanban_api.sh [host:port]

HOST_PORT=${1:-localhost:8000}

echo "Testing Kanban API at $HOST_PORT..."
curl -s "http://$HOST_PORT/job/api/jobs/fetch-all/" > /tmp/api_response.json 2>&1

# Check for any errors in API response - this MUST catch the validation error case
if grep -q "ERROR\|500\|400\|Exception\|Traceback\|Internal Server Error\|Connection refused\|ErrorDetail\|field may not be blank" /tmp/api_response.json; then
    echo "✗ ERROR: API test failed"
    echo "Response:"
    cat /tmp/api_response.json
    rm -f /tmp/api_response.json
    exit 1
elif [ ! -s /tmp/api_response.json ]; then
    echo "✗ ERROR: No response from server (is it running at $HOST_PORT?)"
    rm -f /tmp/api_response.json
    exit 1
else
    # Parse successful response
    python -c "
import json, sys
try:
    with open('/tmp/api_response.json') as f:
        data = json.load(f)
    if data.get('success') and len(data.get('active_jobs', [])) > 0:
        print(f'✓ API working: {len(data[\"active_jobs\"])} active jobs, {len(data.get(\"archived_jobs\", []))} archived')
        sys.exit(0)
    else:
        print('✗ ERROR: API returned no data or success=false')
        print(f'Response: {data}')
        sys.exit(1)
except json.JSONDecodeError:
    print('✗ ERROR: Invalid JSON response')
    with open('/tmp/api_response.json') as f:
        print(f'Raw response: {f.read()[:200]}...')
    sys.exit(1)
except Exception as e:
    print(f'✗ ERROR: {e}')
    sys.exit(1)
"
    exit_code=$?
    rm -f /tmp/api_response.json
    exit $exit_code
fi
