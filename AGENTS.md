# AGENTS.md - Guide for AI Tools and Developers

This document provides comprehensive guidance for AI coding assistants and developers working on the Potions Plugin Registry.

## Architecture Overview

The Potions Plugin Registry is a GitHub-hosted, manifest-based plugin registry system inspired by Homebrew and RubyGems. It provides a reliable, secure, and auditable way to manage plugins for the Potions system.

### Core Principles

1. **Manifest-First**: Each plugin is defined by a `.potion` manifest file (YAML format)
2. **Dual Format**: Human-readable manifests + machine-readable `index.json`
3. **GitHub-Native**: All operations use GitHub (no external services)
4. **Security by Default**: Comprehensive automated security checks
5. **Progressive Enhancement**: Simple base with powerful extensions

### Directory Structure

```
potions-shelf/
├── plugins/                    # Plugin manifest files (.potion)
├── schema/                     # JSON schema for validation
│   └── potion-manifest.schema.json
├── scripts/                    # Utility scripts
│   ├── validate-manifest.sh    # Manifest validation
│   ├── dependency-resolver.py  # Dependency resolution
│   └── generate-index.py       # Index generation
├── .github/workflows/          # GitHub Actions workflows
│   ├── validate-plugin.yml     # PR validation
│   ├── security-scan.yml       # Security scanning
│   └── generate-index.yml      # Auto-index generation
├── index.json                   # Generated plugin index
├── AGENTS.md                   # This file
├── CONTRIBUTING.md             # Contribution guidelines
└── README.md                   # Project documentation
```

## Manifest File Format

### Location
- All plugin manifests must be in the `plugins/` directory
- Filename format: `{plugin-name}.potion`
- Must be valid YAML

### Required Fields

```yaml
name: plugin-name              # Unique identifier (lowercase, alphanumeric, hyphens)
version: "1.2.3"              # Semantic version
description: "Plugin description"  # 10-500 characters
author: "Author Name"         # Author or GitHub username
repository: "https://github.com/user/repo"  # GitHub repository URL
```

### Optional Fields

```yaml
homepage: "https://plugin-website.com"
license: "MIT"                # SPDX license identifier
tags: ["category1", "category2"]  # Categories for discovery
potionfile_path: "Potionfile"  # Path to Potionfile in repo (default: "Potionfile")
min_potions_version: "0.1.0"   # Minimum Potions version
max_potions_version: "1.0.0"   # Maximum Potions version
checksum: "sha256:abc123..."   # SHA256 checksum
signature: "gpg:..."           # GPG signature (optional)
verified: true                 # Maintainer verification status
dependencies:                  # Plugin dependencies
  - name: other-plugin
    version: ">=1.0.0"
install:                       # Installation configuration
  type: "git"                  # git, archive, or script
  path: "/"                    # Path within repository
  branch: "main"               # Git branch/tag
hooks:                         # Lifecycle hooks
  pre_install: "scripts/pre-install.sh"
  post_install: "scripts/post-install.sh"
```

### Schema Validation

All manifests are validated against `schema/potion-manifest.schema.json` using JSON Schema Draft 7.

## Validation Process

### Local Validation

```bash
# Validate a single manifest
./scripts/validate-manifest.sh plugins/my-plugin.potion

# Validate all dependencies
python3 scripts/dependency-resolver.py plugins/

# Generate index
python3 scripts/generate-index.py plugins/ index.json
```

### Automated Validation (GitHub Actions)

1. **PR Validation** (`.github/workflows/validate-plugin.yml`)
   - Triggers on PRs that modify `plugins/**/*.potion`
   - Validates manifest schema
   - Validates dependencies
   - Checks format and required fields

2. **Security Scan** (`.github/workflows/security-scan.yml`)
   - Verifies repository accessibility
   - Checks Potionfile existence
   - Validates checksum format
   - Checks for security advisories

3. **Index Generation** (`.github/workflows/generate-index.yml`)
   - Auto-generates `index.json` on manifest changes
   - Commits and pushes updated index

## Dependency Resolution

The dependency resolver (`scripts/dependency-resolver.py`) performs:

1. **Circular Dependency Detection**: Uses DFS to detect cycles
2. **Version Constraint Validation**: Validates semantic version constraints
3. **Dependency Graph Building**: Constructs forward and reverse dependency graphs

### Version Constraints

Supported operators:
- `=` - Exact version
- `>=` - Greater than or equal
- `<=` - Less than or equal
- `>` - Greater than
- `<` - Less than
- `~>` - Pessimistic (e.g., `~>1.2.3` means `>=1.2.3` and `<1.3.0`)
- `^` - Caret (e.g., `^1.2.3` means `>=1.2.3` and `<2.0.0`)

## Index Generation

The index generator (`scripts/generate-index.py`) creates a searchable JSON index:

```json
{
  "version": "1.0.0",
  "last_updated": "2024-01-01T00:00:00Z",
  "total_plugins": 10,
  "plugins": [...],
  "categories": {
    "category1": ["plugin1", "plugin2"]
  }
}
```

## Security Considerations

### Checksums
- Format: `sha256:{64-character hex digest}`
- Used to verify plugin integrity
- Recommended but not required

### Signatures
- Format: `gpg:{base64-encoded signature}`
- Optional GPG signature for authenticity
- Not currently validated automatically

### Repository Verification
- Repository must exist and be accessible
- Repository must not be archived or disabled
- Potionfile must exist at specified path

## Common Patterns

### Adding a New Plugin

1. Create manifest file: `plugins/my-plugin.potion`
2. Follow the schema (see `schema/potion-manifest.schema.json`)
3. Submit PR
4. Automated validation runs
5. After merge, index is auto-generated

### Updating a Plugin

1. Edit existing manifest in `plugins/`
2. Update version number
3. Submit PR
4. Validation ensures backward compatibility

### Handling Dependencies

```yaml
dependencies:
  - name: base-plugin
    version: ">=1.0.0"
  - name: utility-plugin
    version: "~>2.1.0"
```

## Testing

### Manual Testing

```bash
# Test validation script
./scripts/validate-manifest.sh plugins/example.potion

# Test dependency resolver
python3 scripts/dependency-resolver.py plugins/ plugins/example.potion

# Test index generation
python3 scripts/generate-index.py plugins/ test-index.json
```

### CI/CD Testing

All workflows run automatically on:
- Pull requests (validation and security)
- Pushes to main (index generation)

## Error Handling

### Validation Errors

- Schema validation errors show field path and message
- Format errors indicate specific issues
- Repository errors show API response details

### Dependency Errors

- Circular dependencies show the cycle path
- Version conflicts show constraint and actual version
- Missing dependencies list the plugin name

## Best Practices

1. **Naming**: Use lowercase, alphanumeric with hyphens only
2. **Versioning**: Follow semantic versioning (semver.org)
3. **Descriptions**: Be clear and concise (10-500 chars)
4. **Tags**: Use consistent category names
5. **Dependencies**: Specify minimum versions, avoid exact pins
6. **Checksums**: Always provide for security
7. **Testing**: Test locally before submitting PR

## Troubleshooting

### Validation Fails

1. Check schema: `schema/potion-manifest.schema.json`
2. Validate YAML syntax
3. Check required fields
4. Verify format patterns (name, version, URLs)

### Dependency Resolution Fails

1. Check circular dependencies
2. Verify version constraints
3. Ensure dependencies exist in registry
4. Check version format

### Index Generation Fails

1. Check all manifest files are valid
2. Ensure no duplicate plugin names
3. Verify YAML parsing

## Integration with Potions

The Potions CLI will:
1. Fetch `index.json` from this registry
2. Search for plugins by name/tag
3. Resolve dependencies
4. Fetch plugin repositories
5. Verify checksums
6. Install plugins

## Contributing

See `CONTRIBUTING.md` for detailed contribution guidelines.

## Resources

- [JSON Schema Specification](https://json-schema.org/)
- [Semantic Versioning](https://semver.org/)
- [Homebrew Formulae](https://github.com/Homebrew/homebrew-core)
- [RubyGems Guides](https://guides.rubygems.org/)

## Questions?

- Check existing manifests in `plugins/` for examples
- Review schema in `schema/potion-manifest.schema.json`
- Check GitHub Actions logs for validation details

