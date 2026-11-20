#!/usr/bin/env python3
"""Check that catalog entries point to usable Potions plugin snapshots.

All GitHub reads are pinned to one commit SHA per source repository. The check
does not execute downloaded code. It validates source repository status, the
plugin manifest format supported by Potions, and symlink-free tracked files.
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

import requests
import yaml
from manifest_validation import NAME_RE, VERSION_RE, UniqueKeyLoader, load_manifest, split_repository_spec, validate_repository_url


API_ROOT = "https://api.github.com"
REQUEST_TIMEOUT = (5, 15)
MAX_MANIFEST_BYTES = 256 * 1024
MAX_TREE_ENTRIES = 20_000
MAX_API_RESPONSE_BYTES = 8 * 1024 * 1024


class VerificationError(Exception):
    """A source repository did not satisfy the catalog's safety checks."""


def parse_repository(value: str) -> tuple[str, str, str | None]:
    """Return owner, repository, and optional exact tag from a GitHub URL."""
    problem = validate_repository_url(value)
    if problem:
        raise VerificationError(problem)
    url, tag = split_repository_spec(value)
    parts = urlsplit(url).path.strip("/").split("/")
    return parts[0], parts[1], tag


def github_json(session: requests.Session, url: str, token: str, *, params: dict[str, str] | None = None) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = session.get(
            url,
            headers=headers,
            params=params,
            timeout=REQUEST_TIMEOUT,
            stream=True,
            allow_redirects=False,
        )
    except requests.RequestException as error:
        raise VerificationError("GitHub API request failed") from error

    try:
        if response.status_code == 404:
            raise VerificationError("repository or requested source object was not found")
        if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
            raise VerificationError("GitHub API rate limit was reached")
        if response.status_code != 200:
            raise VerificationError(f"GitHub API returned HTTP {response.status_code}")
        content_length = response.headers.get("Content-Length")
        if content_length and content_length.isdigit() and int(content_length) > MAX_API_RESPONSE_BYTES:
            raise VerificationError("GitHub API response is too large to verify safely")
        content = bytearray()
        for chunk in response.iter_content(chunk_size=64 * 1024):
            content.extend(chunk)
            if len(content) > MAX_API_RESPONSE_BYTES:
                raise VerificationError("GitHub API response is too large to verify safely")
        result = json.loads(content)
    except VerificationError:
        raise
    except ValueError as error:
        raise VerificationError("GitHub API returned invalid JSON") from error
    except requests.RequestException as error:
        raise VerificationError("GitHub API response could not be read") from error
    finally:
        response.close()
    if not isinstance(result, dict):
        raise VerificationError("GitHub API returned an unexpected response")
    return result


def get_source_commit(
    session: requests.Session,
    owner: str,
    repository: str,
    tag: str | None,
    default_branch: str,
    token: str,
) -> str:
    base = f"{API_ROOT}/repos/{quote(owner, safe='')}/{quote(repository, safe='')}"
    if tag is None:
        ref_type = "heads"
        ref_name = default_branch
    else:
        ref_type = "tags"
        ref_name = tag

    ref = github_json(session, f"{base}/git/ref/{ref_type}/{quote(ref_name, safe='/')}", token)
    obj = ref.get("object")
    if not isinstance(obj, dict):
        raise VerificationError("GitHub did not return a source ref")

    object_type = obj.get("type")
    object_sha = obj.get("sha")
    depth = 0
    while object_type == "tag":
        if not isinstance(object_sha, str) or not re.fullmatch(r"[0-9a-f]{40,64}", object_sha):
            raise VerificationError("GitHub returned an invalid tag object")
        depth += 1
        if depth > 5:
            raise VerificationError("tag points through too many nested annotated tags")
        tag_object = github_json(session, f"{base}/git/tags/{object_sha}", token)
        obj = tag_object.get("object")
        if not isinstance(obj, dict):
            raise VerificationError("GitHub returned an invalid annotated tag")
        object_type = obj.get("type")
        object_sha = obj.get("sha")

    if object_type != "commit" or not isinstance(object_sha, str) or not re.fullmatch(r"[0-9a-f]{40,64}", object_sha):
        raise VerificationError("source ref does not resolve to a commit")
    return object_sha


def load_source_manifest(
    session: requests.Session,
    base: str,
    tree: list[dict[str, Any]],
    token: str,
) -> tuple[str, str]:
    entries = {entry.get("path"): entry for entry in tree if isinstance(entry.get("path"), str)}
    manifest_path = next((path for path in (".potion", "plugin.potions.json") if path in entries), None)
    if manifest_path is None:
        raise VerificationError("resolved source commit has no root .potion or plugin.potions.json manifest")

    install_hook = entries.get("install.sh")
    if install_hook is not None and (
        install_hook.get("type") != "blob" or install_hook.get("mode") != "100755"
    ):
        raise VerificationError("install.sh must be a regular executable file when present")

    entry = entries[manifest_path]
    if entry.get("type") != "blob" or entry.get("mode") not in ("100644", "100755"):
        raise VerificationError("source manifest must be a regular tracked file")
    blob_sha = entry.get("sha")
    if not isinstance(blob_sha, str) or not re.fullmatch(r"[0-9a-f]{40,64}", blob_sha):
        raise VerificationError("source manifest has an invalid Git blob identifier")

    blob = github_json(session, f"{base}/git/blobs/{blob_sha}", token)
    encoded = blob.get("content")
    if not isinstance(encoded, str):
        raise VerificationError("source manifest is missing or too large")
    encoded = "".join(encoded.split())
    if len(encoded) > ((MAX_MANIFEST_BYTES + 2) // 3) * 4:
        raise VerificationError("source manifest is missing or too large")
    try:
        content = base64.b64decode(encoded, validate=True)
        if len(content) > MAX_MANIFEST_BYTES:
            raise VerificationError("source manifest is too large")
        if manifest_path == "plugin.potions.json":
            manifest = json.loads(content, object_pairs_hook=unique_json_object)
        else:
            manifest = load_source_yaml(content)
    except (ValueError, yaml.YAMLError) as error:
        raise VerificationError("source manifest is not valid JSON or YAML") from error

    if not isinstance(manifest, dict):
        raise VerificationError("source manifest must contain an object")
    name = manifest.get("name")
    version = manifest.get("version")
    minimum = manifest.get("potions_min_version")
    description = manifest.get("description")
    author = manifest.get("author")
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        raise VerificationError("source manifest has an invalid plugin name")
    if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
        raise VerificationError("source manifest has an invalid version")
    if not isinstance(minimum, str) or not VERSION_RE.fullmatch(minimum):
        raise VerificationError("source manifest has an invalid potions_min_version")
    if not isinstance(description, str) or not description.strip():
        raise VerificationError("source manifest has no description")
    if not isinstance(author, str) or not author.strip():
        raise VerificationError("source manifest has no author")
    return name, version


def load_source_yaml(content: bytes) -> Any:
    source = content.decode("utf-8")
    for token in yaml.scan(source):
        if isinstance(token, (yaml.tokens.AnchorToken, yaml.tokens.AliasToken)):
            raise VerificationError("source manifest YAML anchors and aliases are unsupported")
    node = yaml.compose(source)
    if node is None:
        raise VerificationError("source manifest YAML is empty")

    def reject_merge_keys(current: Any) -> None:
        if isinstance(current, yaml.MappingNode):
            for key_node, value_node in current.value:
                if getattr(key_node, "tag", "") == "tag:yaml.org,2002:merge":
                    raise VerificationError("source manifest YAML merge keys are unsupported")
                reject_merge_keys(key_node)
                reject_merge_keys(value_node)
        elif isinstance(current, yaml.SequenceNode):
            for child in current.value:
                reject_merge_keys(child)

    reject_merge_keys(node)
    return yaml.load(source, Loader=UniqueKeyLoader)


def unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def verify_repository(
    session: requests.Session, repository_url: str, token: str
) -> tuple[str, str, str]:
    owner, repository, tag = parse_repository(repository_url)
    base = f"{API_ROOT}/repos/{quote(owner, safe='')}/{quote(repository, safe='')}"
    metadata = github_json(session, base, token)
    if metadata.get("private") is not False or metadata.get("archived") is not False or metadata.get("disabled") is not False:
        raise VerificationError("repository must be public, enabled, and not archived")
    canonical_name = metadata.get("full_name")
    if not isinstance(canonical_name, str) or canonical_name.lower() != f"{owner}/{repository}".lower():
        raise VerificationError("GitHub repository identity changed or redirected")
    default_branch = metadata.get("default_branch")
    if not isinstance(default_branch, str) or not default_branch:
        raise VerificationError("repository has no default branch")

    commit_sha = get_source_commit(session, owner, repository, tag, default_branch, token)
    commit = github_json(session, f"{base}/git/commits/{commit_sha}", token)
    tree_data = commit.get("tree")
    tree_sha = tree_data.get("sha") if isinstance(tree_data, dict) else None
    if not isinstance(tree_sha, str) or not re.fullmatch(r"[0-9a-f]{40,64}", tree_sha):
        raise VerificationError("resolved commit has no Git tree")
    tree = github_json(session, f"{base}/git/trees/{tree_sha}", token, params={"recursive": "1"})
    entries = tree.get("tree")
    if tree.get("truncated") is True or not isinstance(entries, list) or len(entries) > MAX_TREE_ENTRIES:
        raise VerificationError("source tree is truncated or too large to verify safely")
    for item in entries:
        if not isinstance(item, dict):
            raise VerificationError("source tree contains an invalid entry")
        if item.get("mode") == "120000" or item.get("type") == "commit":
            raise VerificationError("source tree contains a symlink or submodule unsupported by Potions")

    plugin_name, version = load_source_manifest(session, base, entries, token)
    print(f"Verified source https://github.com/{owner}/{repository}@{commit_sha} ({plugin_name} {version})")
    return commit_sha, plugin_name, version


def changed_manifest_paths(file_list: str) -> list[Path]:
    path = Path(file_list)
    if not path.is_file():
        raise VerificationError("changed-manifest list was not found")
    result: list[Path] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        item = line.strip()
        if not item:
            continue
        candidate = Path(item)
        if (
            candidate.is_absolute()
            or len(candidate.parts) != 2
            or candidate.parts[0] != "plugins"
            or candidate.name in {".", ".."}
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.potion", candidate.name)
            or candidate.suffix != ".potion"
        ):
            raise VerificationError(f"changed-manifest list contains an unsupported path: {item}")
        if candidate.is_file():
            result.append(candidate)
    return result


def all_active_manifest_paths() -> list[Path]:
    directory = Path("plugins")
    if not directory.is_dir():
        raise VerificationError("active plugins directory was not found")
    paths = sorted(
        path for path in directory.iterdir()
        if path.is_file() and path.suffix == ".potion"
    )
    for path in paths:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.potion", path.name):
            raise VerificationError(f"active manifest has an invalid filename: {path.name}")
    return paths


def verify_changed_sources(file_list: str, token: str, *, all_active: bool = False,
                           session: requests.Session | None = None) -> bool:
    try:
        paths = all_active_manifest_paths() if all_active else changed_manifest_paths(file_list)
        if not paths:
            print("No active source manifests changed; skipping GitHub source checks.")
            return True
        client = session or requests.Session()
        errors: list[str] = []
        verified_sources: dict[str, tuple[str, str, str]] = {}
        for path in paths:
            try:
                catalog_manifest = load_manifest(path)
                repository_url = catalog_manifest.get("repository")
                if not isinstance(repository_url, str) or not repository_url:
                    raise VerificationError("catalog manifest is missing a repository URL")
                owner, repository, tag = parse_repository(repository_url)
                source_key = f"{owner.lower()}/{repository.lower()}@{tag or ''}"
                if source_key not in verified_sources:
                    verified_sources[source_key] = verify_repository(client, repository_url, token)
                _, source_name, source_version = verified_sources[source_key]
                if source_name != catalog_manifest.get("name"):
                    raise VerificationError("catalog name does not match the plugin manifest at the resolved source commit")
                if source_version != catalog_manifest.get("version"):
                    raise VerificationError("catalog version does not match the plugin manifest at the resolved source commit")
            except (OSError, UnicodeError, yaml.YAMLError, VerificationError) as error:
                errors.append(f"{path}: {error}")

        if errors:
            print("Source verification failed:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return False
        return True
    except VerificationError as error:
        print(f"Source verification failed: {error}", file=sys.stderr)
        return False


def main() -> int:
    all_active = len(sys.argv) == 2 and sys.argv[1] == "--all"
    if len(sys.argv) > 2 or (len(sys.argv) == 2 and sys.argv[1].startswith("--") and not all_active):
        print("Usage: verify-plugin-sources.py [--all | changed-files.txt]", file=sys.stderr)
        return 2
    file_list = "changed_files.txt" if all_active or len(sys.argv) == 1 else sys.argv[1]
    if not verify_changed_sources(file_list, os.environ.get("GITHUB_TOKEN", ""), all_active=all_active):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
