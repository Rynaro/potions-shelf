"""Static, bounded triage of a plugin's immutable Git tree."""

from __future__ import annotations

import base64
import re
from pathlib import PurePosixPath
from typing import Callable

MAX_FILES = 200
MAX_FILE_BYTES = 256 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024
COMMAND = r"(?:^|[;&|()]|\$\()\s*(?:command\s+)?"
RULES = (
    ("remote-execution", COMMAND + r"(?:curl|wget)\b[^\n]*\|\s*(?:bash|sh|zsh|python\d*)\b", "high", "Remove execution of downloaded code before listing."),
    ("network-access", COMMAND + r"(?:curl|wget|nc|ncat|netcat|telnet)\b|\b(?:requests|urllib|httpx|socket)\s*[.(]", "review-required", "Review network destinations and downloaded dependencies."),
    ("dynamic-execution", COMMAND + r"eval\b|\b(?:exec|eval)\s*\(|" + COMMAND + r"(?:bash|sh|zsh|python\d*)\s+-[A-Za-z]*c\b", "high", "Replace dynamically constructed code with explicit commands."),
    ("privilege-change", COMMAND + r"(?:sudo|doas|pkexec|su)\s|" + COMMAND + r"chmod\b[^\n]*(?:[24]777|[46][0-7]{3}|[uoa]\+s)", "review-required", "Review elevated privileges and permission changes."),
    ("credential-access", COMMAND + r"(?:cat|cp|mv|tar|rsync|scp)\b[^\n]*(?:\.ssh|\.aws|\.gnupg|\.netrc|/etc/shadow|id_rsa|id_ed25519)|" + COMMAND + r"security\s+find-", "high", "Remove access to credentials or private configuration."),
    ("persistence", COMMAND + r"(?:crontab|launchctl|systemctl)\b", "review-required", "Review startup, service, and scheduled-task changes."),
    ("destructive-operation", COMMAND + r"rm\s+(?:-[A-Za-z]*[rf][A-Za-z]*\s+)+|" + COMMAND + r"(?:mkfs|fdisk|diskutil\s+erase)\b", "high", "Review destructive filesystem operations."),
)
COMPILED_RULES = [(name, re.compile(pattern, re.IGNORECASE), severity, advice) for name, pattern, severity, advice in RULES]
SECRET_MARKERS = re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----")


def finding(path: str, line: int, rule: str, message: str, severity: str = "review-required") -> dict:
    return {"path": path, "line": line, "rule": rule, "severity": severity, "message": message}


def scan_text(path: str, text: str) -> list[dict]:
    """Return review blockers without echoing contributed source into reports."""
    findings = []
    seen = set()
    for number, line in enumerate(text.splitlines(), 1):
        if SECRET_MARKERS.search(line):
            findings.append(finding(path, number, "private-key", "Remove private key material and rotate exposed credentials.", "high"))
        if line.lstrip().startswith("#"):
            continue
        for rule, pattern, severity, message in COMPILED_RULES:
            if rule not in seen and pattern.search(line):
                findings.append(finding(path, number, rule, message, severity))
                seen.add(rule)
    return findings


def scan_tree(entries: list[dict], fetch_blob: Callable[[str], dict]) -> dict:
    """Read every tracked blob, fail closed on uninspectable data or limits."""
    files = [entry for entry in entries if entry.get("type") == "blob"]
    findings = []
    if len(files) > MAX_FILES:
        return {"files_scanned": 0, "bytes_scanned": 0, "findings": [finding("", 0, "file-limit", "Source tree exceeds the triage file limit.")]}
    total = 0
    scanned = 0
    blobs = {}
    for entry in sorted(files, key=lambda value: value.get("path", "")):
        path = entry.get("path", "")
        normalized = PurePosixPath(path)
        if (not path or normalized.is_absolute() or ".." in normalized.parts
                or any(ord(character) < 32 or ord(character) == 127 for character in path)):
            findings.append(finding("", 0, "invalid-path", "Source tree contains an unsupported path."))
            continue
        if entry.get("mode") not in {"100644", "100755"}:
            findings.append(finding(path, 0, "file-mode", "Source file uses an unsupported Git mode."))
            continue
        size = entry.get("size")
        if isinstance(size, int) and size > MAX_FILE_BYTES:
            findings.append(finding(path, 0, "file-limit", "Source file exceeds the triage size limit."))
            continue
        sha = entry.get("sha")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
            findings.append(finding(path, 0, "invalid-blob", "Source file has an invalid Git blob identifier."))
            continue
        try:
            if sha not in blobs:
                blob = fetch_blob(sha)
                encoded = "".join(blob.get("content", "").split())
                if len(encoded) > ((MAX_FILE_BYTES + 2) // 3) * 4:
                    raise ValueError("file-limit")
                blobs[sha] = base64.b64decode(encoded, validate=True)
            content = blobs[sha]
            total += len(content)
            if len(content) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                findings.append(finding(path, 0, "scan-limit", "Source exceeds the triage byte limit."))
                break
            if b"\x00" in content:
                raise ValueError("binary-content")
            text = content.decode("utf-8")
        except (ValueError, TypeError, AttributeError, UnicodeError):
            findings.append(finding(path, 0, "uninspectable-file", "Source file cannot be inspected as bounded UTF-8 text."))
            continue
        scanned += 1
        findings.extend(scan_text(path, text))
    return {"files_scanned": scanned, "bytes_scanned": total, "findings": findings}
