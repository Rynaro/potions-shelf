#!/usr/bin/env python3
"""
verify-checksums.py - Verifies checksum format in plugin manifests

This script validates that checksums in plugin manifests follow the correct
format (sha256: prefix with 64 hex characters). Missing checksums generate
warnings but do not cause failures.
"""

import sys
import yaml
from pathlib import Path


def verify_checksums(changed_files_path: str) -> bool:
    """Verify checksum format for all manifests in changed files"""
    errors = []
    warnings = []

    changed_files = Path(changed_files_path)
    if not changed_files.exists():
        print(f"Error: Changed files list not found: {changed_files_path}", file=sys.stderr)
        return False

    with open(changed_files, "r") as f:
        for line in f:
            file_path = line.strip()
            if not file_path:
                continue

            try:
                manifest_path = Path(file_path)
                if not manifest_path.exists():
                    continue

                with open(manifest_path, "r") as mf:
                    manifest = yaml.safe_load(mf)

                checksum = manifest.get("checksum", "")
                repo_url = manifest.get("repository", "")

                if not checksum:
                    warnings.append(f"{file_path}: No checksum provided (recommended for security)")
                    continue

                if not repo_url:
                    continue

                # Extract expected checksum
                if not checksum.startswith("sha256:"):
                    errors.append(f"{file_path}: Invalid checksum format (must start with 'sha256:')")
                    continue

                expected_hash = checksum.replace("sha256:", "")

                # Note: Full checksum verification would require downloading the plugin
                # This is a placeholder that validates the format
                if len(expected_hash) != 64:
                    errors.append(f"{file_path}: Invalid SHA256 checksum length")

            except Exception as e:
                errors.append(f"{file_path}: Error verifying checksum: {e}")

    if warnings:
        print("Checksum warnings:", file=sys.stderr)
        for warning in warnings:
            print(f"  - {warning}", file=sys.stderr)

    if errors:
        print("Checksum verification errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return False

    print("✓ Checksum format validation passed")
    return True


def main():
    """Main entry point"""
    changed_files_path = sys.argv[1] if len(sys.argv) > 1 else "changed_files.txt"
    
    success = verify_checksums(changed_files_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

