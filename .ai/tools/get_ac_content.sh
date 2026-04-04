#!/bin/bash
# Usage: get_ac_content.sh <AC_ID> [task_file]
AC_ID=$1
TASK_FILE=${2:-""}
SPRINT_FILE=$(grep -l "<ac-block id=\"$AC_ID\">" specs/sprints/*.md | head -n 1)

if [ -z "$SPRINT_FILE" ]; then
  printf 'ERROR: AC block %s not found in any sprint file\n' "$AC_ID"
  exit 1
fi

AC_CONTENT=$(sed -n "/<ac-block id=\"$AC_ID\">/,/<\/ac-block>/p" "$SPRINT_FILE" | \
  sed '1d;$d')

if [ -z "$AC_CONTENT" ]; then
  printf 'ERROR: AC block %s not found\n' "$AC_ID"
  exit 1
fi

ACTUAL_HASH=$(printf '%s' "$AC_CONTENT" | tr -d '\r' | sha256sum | cut -d' ' -f1)

if [ -n "$TASK_FILE" ]; then
  EXPECTED_HASH=$(jq -r '.expected_hash' "$TASK_FILE")
  if [ "$ACTUAL_HASH" != "$EXPECTED_HASH" ]; then
    printf 'ERROR: STALE_CONTEXT - AC block has been modified\n'
    printf 'Expected hash: %s\n' "$EXPECTED_HASH"
    printf 'Actual hash: %s\n' "$ACTUAL_HASH"
    exit 2
  fi
fi

printf '%s\n' "$AC_CONTENT"
