#!/bin/bash
# validate-manifest.sh - Validates a Potions plugin manifest file
#
# Usage: validate-manifest.sh <manifest-file>
#
# This script validates a .potion manifest file against the JSON schema
# and performs additional checks for repository accessibility and format.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCHEMA_FILE="$REPO_ROOT/schema/potion-manifest.schema.json"

# Check if manifest file is provided
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: No manifest file provided${NC}" >&2
    echo "Usage: $0 <manifest-file>" >&2
    exit 1
fi

MANIFEST_FILE="$1"

# Check if manifest file exists
if [ ! -f "$MANIFEST_FILE" ]; then
    echo -e "${RED}Error: Manifest file not found: $MANIFEST_FILE${NC}" >&2
    exit 1
fi

# Check if schema file exists
if [ ! -f "$SCHEMA_FILE" ]; then
    echo -e "${RED}Error: Schema file not found: $SCHEMA_FILE${NC}" >&2
    exit 1
fi

# Check if required tools are available
if ! command -v yq &> /dev/null; then
    echo -e "${RED}Error: yq is required but not installed${NC}" >&2
    echo "Install with: brew install yq" >&2
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is required but not installed${NC}" >&2
    exit 1
fi

echo -e "${GREEN}Validating manifest: $MANIFEST_FILE${NC}"

# Check file extension
if [[ ! "$MANIFEST_FILE" =~ \.(potion|yaml|yml)$ ]]; then
    echo -e "${YELLOW}Warning: Manifest file should have .potion, .yaml, or .yml extension${NC}"
fi

# Convert YAML to JSON for schema validation
TEMP_JSON=$(mktemp)
trap "rm -f $TEMP_JSON" EXIT

if ! yq eval -o json "$MANIFEST_FILE" > "$TEMP_JSON" 2>/dev/null; then
    echo -e "${RED}Error: Failed to parse YAML file${NC}" >&2
    exit 1
fi

# Validate against JSON schema using Python
VALIDATION_SCRIPT=$(cat <<'PYTHON_EOF'
import json
import sys
from jsonschema import validate, ValidationError, Draft7Validator

def validate_manifest(manifest_path, schema_path):
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        validator = Draft7Validator(schema)
        errors = sorted(validator.iter_errors(manifest), key=lambda e: e.path)
        
        if errors:
            print("Validation errors:", file=sys.stderr)
            for error in errors:
                path = '.'.join(str(p) for p in error.path) if error.path else 'root'
                print(f"  - {path}: {error.message}", file=sys.stderr)
                if error.context:
                    for suberror in error.context:
                        subpath = '.'.join(str(p) for p in suberror.path) if suberror.path else 'root'
                        print(f"    - {subpath}: {suberror.message}", file=sys.stderr)
            return False
        
        return True
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}", file=sys.stderr)
        return False
    except FileNotFoundError as e:
        print(f"File not found: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Validation error: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    manifest_path = sys.argv[1]
    schema_path = sys.argv[2]
    success = validate_manifest(manifest_path, schema_path)
    sys.exit(0 if success else 1)
PYTHON_EOF
)

# Run Python validation
if ! python3 -c "$VALIDATION_SCRIPT" "$TEMP_JSON" "$SCHEMA_FILE"; then
    echo -e "${RED}Schema validation failed${NC}" >&2
    exit 1
fi

echo -e "${GREEN}✓ Schema validation passed${NC}"

# Extract repository URL for additional checks
REPO_URL=$(yq eval '.repository' "$MANIFEST_FILE" 2>/dev/null || echo "")

if [ -n "$REPO_URL" ]; then
    # Validate repository URL format
    if [[ ! "$REPO_URL" =~ ^https://github\.com/[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+(/)?$ ]]; then
        echo -e "${RED}Error: Invalid repository URL format: $REPO_URL${NC}" >&2
        exit 1
    fi
    
    echo -e "${GREEN}✓ Repository URL format valid${NC}"
    
    # Check if repository is accessible (optional, can be skipped if GitHub API is unavailable)
    if [ -n "${GITHUB_TOKEN:-}" ]; then
        REPO_PATH=$(echo "$REPO_URL" | sed 's|https://github.com/||' | sed 's|/$||')
        if ! curl -s -f -H "Authorization: token $GITHUB_TOKEN" \
            "https://api.github.com/repos/$REPO_PATH" > /dev/null 2>&1; then
            echo -e "${YELLOW}Warning: Repository may not be accessible or does not exist${NC}"
        else
            echo -e "${GREEN}✓ Repository is accessible${NC}"
        fi
    else
        echo -e "${YELLOW}Note: GITHUB_TOKEN not set, skipping repository accessibility check${NC}"
    fi
fi

# Check version format
VERSION=$(yq eval '.version' "$MANIFEST_FILE" 2>/dev/null || echo "")
if [ -n "$VERSION" ]; then
    if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$ ]]; then
        echo -e "${RED}Error: Invalid version format: $VERSION${NC}" >&2
        exit 1
    fi
    echo -e "${GREEN}✓ Version format valid${NC}"
fi

# Check name format
NAME=$(yq eval '.name' "$MANIFEST_FILE" 2>/dev/null || echo "")
if [ -n "$NAME" ]; then
    if [[ ! "$NAME" =~ ^[a-z0-9-]+$ ]]; then
        echo -e "${RED}Error: Invalid name format (must be lowercase alphanumeric with hyphens): $NAME${NC}" >&2
        exit 1
    fi
    echo -e "${GREEN}✓ Name format valid${NC}"
fi

echo -e "${GREEN}✓ All validations passed!${NC}"
exit 0

