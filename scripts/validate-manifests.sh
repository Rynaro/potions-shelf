#!/bin/bash
# validate-manifests.sh - Validates all manifest files from a list
#
# Usage: validate-manifests.sh [FILE_LIST] [ERROR_COUNT_FILE]
#
# This script reads a list of manifest file paths and validates each one
# using validate-manifest.sh. It counts errors and outputs the error count.
#
# Arguments:
#   FILE_LIST - File containing list of manifest files to validate (default: "changed_files.txt")
#               Can also be "-" to read from stdin, or a space-separated list of files
#   ERROR_COUNT_FILE - Optional file to write error count to (for GitHub Actions output)

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATE_SCRIPT="$SCRIPT_DIR/validate-manifest.sh"

# Get parameters
FILE_LIST="${1:-changed_files.txt}"
ERROR_COUNT_FILE="${2:-}"

ERROR_COUNT=0

# Function to validate a single file
validate_file() {
    local file="$1"
    if [ -f "$file" ]; then
        echo "Validating: $file"
        if ! "$VALIDATE_SCRIPT" "$file"; then
            echo "::error file=$file::Manifest validation failed" >&2
            return 1
        fi
        return 0
    else
        echo "Warning: File not found: $file" >&2
        return 1
    fi
}

# Check if validate-manifest.sh exists
if [ ! -f "$VALIDATE_SCRIPT" ]; then
    echo "Error: validate-manifest.sh not found at $VALIDATE_SCRIPT" >&2
    exit 1
fi

# Process file list
if [ "$FILE_LIST" = "-" ]; then
    # Read from stdin
    while IFS= read -r file || [ -n "$file" ]; do
        file=$(echo "$file" | xargs)  # Trim whitespace
        [ -z "$file" ] && continue
        if ! validate_file "$file"; then
            ERROR_COUNT=$((ERROR_COUNT + 1))
        fi
    done
elif [ -f "$FILE_LIST" ]; then
    # Read from file
    while IFS= read -r file || [ -n "$file" ]; do
        file=$(echo "$file" | xargs)  # Trim whitespace
        [ -z "$file" ] && continue
        if ! validate_file "$file"; then
            ERROR_COUNT=$((ERROR_COUNT + 1))
        fi
    done < "$FILE_LIST"
else
    # Treat as space-separated list of files
    for file in $FILE_LIST; do
        if ! validate_file "$file"; then
            ERROR_COUNT=$((ERROR_COUNT + 1))
        fi
    done
fi

# Output error count to file if specified
if [ -n "$ERROR_COUNT_FILE" ]; then
    echo "error_count=$ERROR_COUNT" > "$ERROR_COUNT_FILE"
fi

# Also output to stdout for GitHub Actions
echo "error_count=$ERROR_COUNT"

# Exit with error if any validation failed
if [ $ERROR_COUNT -gt 0 ]; then
    echo "✗ Validation failed for $ERROR_COUNT file(s)" >&2
    exit 1
fi

echo "✓ All manifest files validated successfully"
exit 0

