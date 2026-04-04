#!/bin/bash
# Usage: resolve_scope.sh <TASK_FILE>
TASK_FILE=$1
echo "=== Allowed Scope ==="
jq -r '.touches.include[]' "$TASK_FILE"
echo "=== Excluded ==="
jq -r '.touches.exclude[]' "$TASK_FILE" 2>/dev/null || echo "(none)"
echo "=== Dependencies ==="
jq -r '.depends_on[]' "$TASK_FILE" 2>/dev/null || echo "(none)"
