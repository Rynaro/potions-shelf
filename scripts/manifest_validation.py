#!/usr/bin/env python3
"""Strict parsing and validation shared by the Potions Shelf scripts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml
from yaml.tokens import AliasToken, AnchorToken
from jsonschema import Draft7Validator, FormatChecker


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_mapping(loader: UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in result
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                "found an unhashable key", key_node.start_mark,
            ) from exc
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                f"duplicate key {key!r}", key_node.start_mark,
            )
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)

NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,98}[a-z0-9])?$")
VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
GITHUB_OWNER_RE = re.compile(r"^[A-Za-z0-9-]+$")
GITHUB_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,98}[A-Za-z0-9])?$")
RELEASE_TAG_RE = re.compile(r"^v?(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")


def load_manifest(path: Path) -> dict[str, Any]:
    """Load one UTF-8 YAML document and reject unsafe or ambiguous values."""
    if path.is_symlink():
        raise ValueError("manifest must not be a symlink")
    if path.stat().st_size > 65536:
        raise ValueError("manifest exceeds the 64 KiB size limit")
    source = path.read_text(encoding="utf-8")
    nesting = 0
    for token in yaml.scan(source, Loader=UniqueKeyLoader):
        if isinstance(token, (AliasToken, AnchorToken)):
            raise ValueError("YAML anchors and aliases are not supported")
        if isinstance(token, yaml.tokens.BlockMappingStartToken) or isinstance(token, yaml.tokens.BlockSequenceStartToken) or isinstance(token, yaml.tokens.FlowMappingStartToken) or isinstance(token, yaml.tokens.FlowSequenceStartToken):
            nesting += 1
            if nesting > 32:
                raise ValueError("manifest nesting exceeds the 32-level limit")
        elif isinstance(token, (yaml.tokens.BlockEndToken, yaml.tokens.FlowMappingEndToken, yaml.tokens.FlowSequenceEndToken)):
            nesting = max(0, nesting - 1)
    value = yaml.load(source, Loader=UniqueKeyLoader)
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError("manifest must contain one YAML mapping with string keys")
    return value


def validate_cli_literals(path: Path, manifest: dict[str, Any]) -> list[str]:
    """Ensure Bash's line-based catalog parser sees the same top-level values."""
    fields = ("name", "version", "description", "author", "repository", "license", "reviewed_commit")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [f"unable to read manifest: {exc}"]
    errors = []
    for field in fields:
        matching = [line for line in lines if re.match(rf"^\s*{field}\s*:", line)]
        top_level = [line for line in lines if re.match(rf"^{field}\s*:", line)]
        if field not in manifest:
            if matching:
                errors.append(f"{field}: CLI-visible value is absent from parsed manifest")
            continue
        if len(top_level) != 1 or not matching or matching[0] != top_level[0]:
            errors.append(f"{field}: must appear once at the top level before any nested field with the same name")
            continue
        line = top_level[0]
        if line[:1].isspace():
            errors.append(f"{field}: must be a top-level literal for Potions compatibility")
            continue
        literal = re.sub(rf"^{field}\s*:\s*", "", line)
        if literal[:1] in {"'", '"'}:
            literal = literal[1:]
        if literal[-1:] in {"'", '"'}:
            literal = literal[:-1]
        literal = literal.strip()
        if any(ord(character) < 32 for character in literal):
            errors.append(f"{field}: control characters are not supported by Potions")
            continue
        if literal != manifest[field]:
            errors.append(f"{field}: Potions line parser would read a different value than YAML")
    return errors


def validate_repository_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return "repository must be a string"
    if len(value) > 255:
        return "repository URL must not exceed 255 characters"
    if not value.startswith("https://github.com/"):
        return "repository must be a canonical https://github.com/OWNER/REPO URL"
    url, separator, ref = value.partition("@")
    if separator and not RELEASE_TAG_RE.fullmatch(ref):
        return "repository ref suffix must be a release tag such as @v1.2.3"
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.netloc.lower() != "github.com"
            or parts.query or parts.fragment or parts.username or parts.password):
        return "repository must be a canonical https://github.com/OWNER/REPO URL"
    segments = parts.path.strip("/").split("/")
    if len(segments) != 2 or not GITHUB_OWNER_RE.fullmatch(segments[0]) or not GITHUB_REPOSITORY_RE.fullmatch(segments[1]):
        return "repository must point to a GitHub repository root without a path, query, or fragment"
    if value.endswith("/"):
        return "repository URL must not have a trailing slash"
    return None


def split_repository_spec(value: str) -> tuple[str, str | None]:
    """Return canonical GitHub repository URL and optional release-tag suffix."""
    repository, separator, ref = value.partition("@")
    return repository, (ref if separator else None)


def validate_manifest(manifest: dict[str, Any], schema_path: Path, source_path: Path | None = None) -> list[str]:
    with schema_path.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)
    validator = Draft7Validator(schema, format_checker=FormatChecker())
    errors = []
    if source_path is not None:
        errors.extend(validate_cli_literals(source_path, manifest))
    for error in sorted(validator.iter_errors(manifest), key=lambda item: (tuple(map(str, item.path)), item.message)):
        field = ".".join(map(str, error.path)) or "root"
        errors.append(f"{field}: {error.message}")

    name = manifest.get("name")
    if isinstance(name, str) and not NAME_RE.fullmatch(name):
        errors.append("name: must be lowercase letters, digits, and single hyphen-separated words")
    if isinstance(name, str) and source_path is not None and source_path.stem != name:
        errors.append(f"name: must match manifest filename {source_path.stem!r}")
    version = manifest.get("version")
    if isinstance(version, str) and not VERSION_RE.fullmatch(version):
        errors.append("version: must be a semantic version")
    repository = manifest.get("repository")
    repository_error = validate_repository_url(repository)
    if repository_error:
        errors.append(f"repository: {repository_error}")
    elif isinstance(repository, str):
        repository_url, _release_tag = split_repository_spec(repository)
        repository_slug = urlsplit(repository_url).path.rstrip("/").rsplit("/", 1)[-1]
        expected_name = repository_slug.removeprefix("potions-")
        if isinstance(name, str) and expected_name != name:
            errors.append(f"name: must match the install name derived from repository slug ({expected_name!r})")
    if "verified" in manifest:
        errors.append("verified: maintainer trust is managed outside plugin manifests")
    if "checksum" in manifest:
        errors.append("checksum: this catalog does not verify plugin content checksums")
    if "signature" in manifest:
        errors.append("signature: plugin signatures are not verified by the Potions client")
    for key in ("min_potions_version", "max_potions_version"):
        value = manifest.get(key)
        if value is not None and (not isinstance(value, str) or not VERSION_RE.fullmatch(value)):
            errors.append(f"{key}: must be a semantic version string")
    dependencies = manifest.get("dependencies", [])
    if isinstance(dependencies, list):
        seen = set()
        for index, dependency in enumerate(dependencies):
            if isinstance(dependency, dict) and isinstance(dependency.get("name"), str):
                dep_name = dependency["name"]
                if dep_name in seen:
                    errors.append(f"dependencies.{index}.name: duplicate dependency {dep_name!r}")
                seen.add(dep_name)
                if dep_name == name:
                    errors.append("dependencies: plugin cannot depend on itself")
    return errors
