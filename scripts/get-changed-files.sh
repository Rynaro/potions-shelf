#!/bin/bash
# get-changed-files.sh - Gets changed manifest files
#
# Usage: get-changed-files.sh [EVENT_NAME] [BASE_REF] [OUTPUT_FILE]
#
# This script detects changed manifest files based on the event type.
# For pull requests, it uses git diff. For other events, it finds all manifest files.
#
# Environment variables (can override arguments):
#   GITHUB_EVENT_NAME - The GitHub event name (pull_request, push, workflow_dispatch)
#   GITHUB_BASE_REF - The base ref for pull requests
#
# Arguments:
#   EVENT_NAME - GitHub event name (default: $GITHUB_EVENT_NAME or "workflow_dispatch")
#   BASE_REF - Base ref for PRs (default: $GITHUB_BASE_REF or "main")
#   OUTPUT_FILE - Output file path (default: "changed_files.txt")

set -euo pipefail

# Get parameters with defaults
EVENT_NAME="${1:-${GITHUB_EVENT_NAME:-workflow_dispatch}}"
BASE_REF="${2:-${GITHUB_BASE_REF:-main}}"
OUTPUT_FILE="${3:-changed_files.txt}"

# Determine changed files based on event type
if [ "$EVENT_NAME" = "pull_request" ]; then
    # For pull requests, use git diff
    git diff --name-only "origin/${BASE_REF}...HEAD" | grep -E '\.(potion|yaml|yml)$' > "$OUTPUT_FILE" || true
else
    # For push or workflow_dispatch, find all manifest files
    find plugins -name "*.potion" -o -name "*.yaml" -o -name "*.yml" > "$OUTPUT_FILE" || true
fi

# Ensure file exists (even if empty)
touch "$OUTPUT_FILE"

echo "✓ Found $(wc -l < "$OUTPUT_FILE" | tr -d ' ') changed manifest file(s)"
echo "  Output: $OUTPUT_FILE"

