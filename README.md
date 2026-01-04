# Potions Plugin Registry

A reliable, secure, and auditable plugin registry for the [Potions](https://github.com/Rynaro/potions) system, hosted entirely on GitHub.

## Overview

The Potions Plugin Registry provides a centralized, open-source registry for Potions plugins. All plugins are defined using manifest files (`.potion` format) and validated through automated GitHub Actions workflows.

### Core Values

- **Security**: Comprehensive automated security checks for all plugins
- **Reliability**: 100% automated validation with zero manual steps
- **Easy to Use**: Simple manifest format, clear documentation
- **Auditability**: All operations visible in GitHub, no hidden processes

## Features

- ✅ Manifest-based plugin definitions (YAML format)
- ✅ Automated validation and security scanning
- ✅ Dependency resolution and validation
- ✅ Searchable plugin index
- ✅ GitHub-native (no external services)
- ✅ Comprehensive security checks

## Registry Structure

```
potions-shelf/
├── plugins/              # Plugin manifest files
├── index.json            # Generated plugin index
├── schema/               # JSON schema for validation
└── scripts/              # Validation and generation scripts
```

## Quick Start

### For Plugin Users

The Potions CLI will automatically use this registry to discover and install plugins. No additional setup required.

### For Plugin Developers

1. **Create a manifest file** in `plugins/`:
   ```yaml
   name: my-plugin
   version: "1.0.0"
   description: "A useful plugin"
   author: "yourname"
   repository: "https://github.com/yourname/my-plugin"
   ```

2. **Validate locally**:
   ```bash
   ./scripts/validate-manifest.sh plugins/my-plugin.potion
   ```

3. **Submit a Pull Request**

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## Manifest Format

Plugin manifests use YAML format with the following structure:

```yaml
name: plugin-name
version: "1.2.3"
description: "Plugin description"
author: "Author Name"
repository: "https://github.com/user/repo"
license: "MIT"
tags: ["category1", "category2"]

# Optional fields
homepage: "https://plugin-website.com"
dependencies:
  - name: other-plugin
    version: ">=1.0.0"
checksum: "sha256:abc123..."
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the complete format reference.

## Validation

All plugin manifests are automatically validated on PR submission:

- ✅ Schema validation (JSON Schema)
- ✅ Format validation (name, version, URLs)
- ✅ Repository verification
- ✅ Potionfile existence check
- ✅ Dependency resolution
- ✅ Security scanning

## Security

The registry performs comprehensive security checks:

1. **Repository Verification**: Ensures repositories exist and are accessible
2. **Checksum Validation**: Verifies plugin integrity
3. **Dependency Validation**: Checks for circular dependencies and version conflicts
4. **Security Scanning**: Checks for known vulnerabilities

## Index

The registry maintains an automatically-generated `index.json` file that provides:

- Complete plugin metadata
- Searchable categories
- Dependency information
- Version information

The index is updated automatically when plugins are added or modified.

## Workflows

### Validate Plugin
Runs on PRs that modify plugin manifests:
- Validates schema and format
- Checks dependencies
- Verifies repository accessibility

### Security Scan
Runs on PRs and pushes to main:
- Repository verification
- Potionfile checks
- Checksum validation
- Security advisory checks

### Generate Index
Runs on pushes to main:
- Generates `index.json` from all manifests
- Commits and pushes updated index

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:

- How to submit a plugin
- Manifest format reference
- Validation requirements
- Best practices

## Documentation

- **[AGENTS.md](AGENTS.md)**: Comprehensive guide for AI tools and developers
- **[CONTRIBUTING.md](CONTRIBUTING.md)**: Contribution guidelines and manifest format
- **[Schema](schema/potion-manifest.schema.json)**: JSON schema for manifests

## Inspiration

This registry is inspired by:

- [Homebrew](https://github.com/Homebrew/homebrew-core) - Formula-based package management
- [RubyGems](https://rubygems.org/) - Gem specification and dependency resolution

## License

This registry is open source. Individual plugins maintain their own licenses as specified in their manifests.

## Support

- **Issues**: [GitHub Issues](https://github.com/Rynaro/potions-shelf/issues)
- **Potions Project**: [https://github.com/Rynaro/potions](https://github.com/Rynaro/potions)

## Status

🚧 **Under Development** - The registry is actively being developed. Check back soon for updates!

