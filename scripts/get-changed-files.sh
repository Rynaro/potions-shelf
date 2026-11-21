#!/bin/bash
# get-changed-files.sh - Gets changed manifest files
#
# Usage: get-changed-files.sh [EVENT_NAME] [BASE_REF] [OUTPUT_FILE]
#
# This script detects changed registry manifests. Renames are reported at their
# destination path by git diff --name-only. Deleted manifests are omitted.
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

# Use a temporary file so a failed diff never leaves a partial manifest list.
temporary_file=$(mktemp)
trap 'rm -f "$temporary_file"' EXIT

case "$EVENT_NAME" in
    pull_request)
        if ! git rev-parse --verify "origin/${BASE_REF}^{commit}" >/dev/null 2>&1; then
            echo "Base ref is not available: $BASE_REF" >&2
            exit 1
        fi
        git diff --name-only -z --diff-filter=ACMRT "origin/${BASE_REF}...HEAD" > "$temporary_file"
        ;;
    push)
        if git rev-parse --verify 'HEAD^' >/dev/null 2>&1; then
            git diff --name-only -z --diff-filter=ACMRT HEAD^ HEAD > "$temporary_file"
        else
            find plugins -type f -name '*.potion' -print0 > "$temporary_file"
        fi
        ;;
    *)
        find plugins -type f -name '*.potion' -print0 > "$temporary_file"
        ;;
esac

: > "$OUTPUT_FILE"
while IFS= read -r -d '' path; do
    case "$path" in
        plugins/*.potion)
            if [ -f "$path" ]; then
                printf '%s\n' "$path" >> "$OUTPUT_FILE"
            fi
            ;;
    esac
done < "$temporary_file"

echo "✓ Found $(wc -l < "$OUTPUT_FILE" | tr -d ' ') changed manifest file(s)"
echo "  Output: $OUTPUT_FILE"

