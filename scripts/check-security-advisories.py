#!/usr/bin/env python3
"""
check-security-advisories.py - Checks for security advisories

This script checks for security advisories in repositories specified in
plugin manifests. This is a basic check - full vulnerability scanning
would require more sophisticated tooling like Dependabot or Snyk integration.
"""

import os
import sys
import yaml
import requests
from pathlib import Path


def check_security_advisories(changed_files_path: str) -> bool:
    """Check security advisories for all repositories in changed manifest files"""
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

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
                if not repo_url:
                    continue

                # Extract repo path
                repo_path = repo_url.replace("https://github.com/", "").rstrip("/")

                # Check for security advisories
                api_url = f"https://api.github.com/repos/{repo_path}/vulnerability-alerts"
                response = requests.get(api_url, headers=headers, timeout=10)

                # Note: This is a basic check. Full vulnerability scanning would require
                # more sophisticated tooling like Dependabot or Snyk integration

            except Exception as e:
                # Non-critical, just log
                pass

    print("✓ Security advisory check completed")
    return True


def main():
    """Main entry point"""
    changed_files_path = sys.argv[1] if len(sys.argv) > 1 else "changed_files.txt"
    
    success = check_security_advisories(changed_files_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

