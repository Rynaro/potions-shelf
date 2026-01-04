#!/usr/bin/env python3
"""
verify-potionfile-exists.py - Verifies Potionfile existence in repositories

This script checks if Potionfile exists at the specified path in each repository
specified in plugin manifests.
"""

import os
import sys
import yaml
import requests
from pathlib import Path


def verify_potionfile_exists(changed_files_path: str) -> bool:
    """Verify Potionfile exists for all repositories in changed manifest files"""
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

    errors = []
    
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

                repo_url = manifest.get("repository", "")
                potionfile_path = manifest.get("potionfile_path", "Potionfile")

                if not repo_url:
                    continue

                # Extract repo path
                repo_path = repo_url.replace("https://github.com/", "").rstrip("/")

                # Check if Potionfile exists
                api_url = f"https://api.github.com/repos/{repo_path}/contents/{potionfile_path}"
                response = requests.get(api_url, headers=headers, timeout=10)

                if response.status_code == 404:
                    errors.append(f"{file_path}: Potionfile not found at '{potionfile_path}' in {repo_url}")
                elif response.status_code != 200:
                    errors.append(f"{file_path}: Failed to check Potionfile (status {response.status_code})")

            except Exception as e:
                errors.append(f"{file_path}: Error checking Potionfile: {e}")

    if errors:
        print("Potionfile verification errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return False

    print("✓ All Potionfiles exist")
    return True


def main():
    """Main entry point"""
    changed_files_path = sys.argv[1] if len(sys.argv) > 1 else "changed_files.txt"
    
    success = verify_potionfile_exists(changed_files_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

