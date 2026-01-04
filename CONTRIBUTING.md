# Contributing to Potions Plugin Registry

Thank you for your interest in contributing to the Potions Plugin Registry! This guide will help you submit plugins and contribute to the registry.

## How to Submit a Plugin

### Prerequisites

1. Your plugin must be hosted on GitHub
2. Your plugin repository must contain a `Potionfile` (see Potions documentation)
3. Your plugin must be functional and tested

### Step 1: Create Your Manifest

Create a new file in the `plugins/` directory with the name `{your-plugin-name}.potion`.

**Naming Rules:**
- Use lowercase letters, numbers, and hyphens only
- Must be unique (check existing plugins first)
- Should be descriptive but concise

### Step 2: Fill in Required Fields

```yaml
name: your-plugin-name
version: "1.0.0"
description: "A clear, concise description of what your plugin does (10-500 characters)"
author: "Your Name or GitHub Username"
repository: "https://github.com/yourusername/your-plugin-repo"
```

### Step 3: Add Optional Fields

```yaml
homepage: "https://your-plugin-website.com"  # Optional
license: "MIT"  # SPDX license identifier
tags: ["category1", "category2"]  # Help users discover your plugin
potionfile_path: "Potionfile"  # Path to Potionfile (default: "Potionfile")
min_potions_version: "0.1.0"  # Minimum required Potions version
max_potions_version: "1.0.0"  # Maximum supported Potions version

# Security (highly recommended)
checksum: "sha256:your-sha256-checksum-here"  # SHA256 of plugin release
verified: false  # Set to true after maintainer review

# Dependencies (if any)
dependencies:
  - name: other-plugin
    version: ">=1.0.0"

# Installation configuration
install:
  type: "git"  # git, archive, or script
  path: "/"   # Path within repository
  branch: "main"  # Git branch or tag

# Lifecycle hooks (optional)
hooks:
  pre_install: "scripts/pre-install.sh"
  post_install: "scripts/post-install.sh"
```

### Step 4: Validate Locally

Before submitting, validate your manifest:

```bash
# Validate your manifest
./scripts/validate-manifest.sh plugins/your-plugin-name.potion

# Check dependencies (if you have any)
python3 scripts/dependency-resolver.py plugins/ plugins/your-plugin-name.potion
```

### Step 5: Submit a Pull Request

1. Fork this repository
2. Create a new branch: `git checkout -b add-your-plugin-name`
3. Add your manifest: `git add plugins/your-plugin-name.potion`
4. Commit: `git commit -m "Add plugin: your-plugin-name"`
5. Push: `git push origin add-your-plugin-name`
6. Open a Pull Request

## Manifest Format Reference

### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `name` | string | Unique plugin identifier | `"my-plugin"` |
| `version` | string | Semantic version | `"1.2.3"` |
| `description` | string | Plugin description (10-500 chars) | `"Does something useful"` |
| `author` | string | Author name or GitHub username | `"johndoe"` |
| `repository` | string | GitHub repository URL | `"https://github.com/user/repo"` |

### Optional Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `homepage` | string | Plugin homepage URL | `"https://example.com"` |
| `license` | string | SPDX license identifier | `"MIT"` |
| `tags` | array | Category tags | `["utility", "git"]` |
| `potionfile_path` | string | Path to Potionfile | `"Potionfile"` |
| `min_potions_version` | string | Minimum Potions version | `"0.1.0"` |
| `max_potions_version` | string | Maximum Potions version | `"1.0.0"` |
| `checksum` | string | SHA256 checksum | `"sha256:abc123..."` |
| `signature` | string | GPG signature | `"gpg:..."` |
| `verified` | boolean | Maintainer verification | `false` |
| `dependencies` | array | Plugin dependencies | See below |
| `install` | object | Installation config | See below |
| `hooks` | object | Lifecycle hooks | See below |

### Dependencies

```yaml
dependencies:
  - name: required-plugin
    version: ">=1.0.0"  # Version constraint
```

**Version Constraints:**
- `=1.0.0` - Exact version
- `>=1.0.0` - Greater than or equal
- `<=1.0.0` - Less than or equal
- `>1.0.0` - Greater than
- `<1.0.0` - Less than
- `~>1.2.0` - Pessimistic (>=1.2.0 and <1.3.0)
- `^1.2.0` - Caret (>=1.2.0 and <2.0.0)

### Installation Configuration

```yaml
install:
  type: "git"      # git, archive, or script
  path: "/"        # Path within repository
  branch: "main"   # Git branch or tag (for git type)
```

### Lifecycle Hooks

```yaml
hooks:
  pre_install: "scripts/pre-install.sh"    # Run before installation
  post_install: "scripts/post-install.sh"  # Run after installation
  pre_uninstall: "scripts/pre-uninstall.sh"  # Run before uninstallation
  post_uninstall: "scripts/post-uninstall.sh"  # Run after uninstallation
```

## Validation Process

When you submit a PR, automated checks will:

1. **Schema Validation**: Validates manifest against JSON schema
2. **Format Validation**: Checks name, version, URL formats
3. **Repository Verification**: Ensures repository exists and is accessible
4. **Potionfile Check**: Verifies Potionfile exists at specified path
5. **Dependency Validation**: Checks dependencies exist and versions are valid
6. **Security Scan**: Validates checksums and checks for security issues

All checks must pass before your PR can be merged.

## Updating a Plugin

To update an existing plugin:

1. Edit the manifest file in `plugins/`
2. Update the `version` field
3. Update any other changed fields
4. Submit a PR

**Version Updates:**
- Follow semantic versioning
- Increment appropriately (patch/minor/major)
- Update checksum if plugin code changed

## Best Practices

### Naming
- Use descriptive, lowercase names
- Avoid generic names like "plugin" or "tool"
- Check for existing similar plugins

### Descriptions
- Be clear and concise
- Explain what the plugin does
- Mention key features
- 10-500 characters

### Tags
- Use consistent category names
- 2-5 tags per plugin
- Check existing tags for consistency

### Versioning
- Follow semantic versioning (semver.org)
- Start at 1.0.0 for stable plugins
- Use 0.x.x for development versions

### Dependencies
- Minimize dependencies when possible
- Use version ranges, not exact pins
- Document why dependencies are needed

### Security
- Always provide checksums
- Use SHA256 format
- Keep checksums updated with versions

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and improve
- Follow the project's guidelines

## Getting Help

- Check `AGENTS.md` for technical details
- Review existing plugins in `plugins/` for examples
- Open an issue for questions or problems
- Check GitHub Actions logs if validation fails

## Review Process

1. Automated validation runs on PR creation
2. Maintainers review the plugin
3. Security checks are performed
4. Plugin is verified (if applicable)
5. PR is merged
6. Index is auto-generated

## After Your Plugin is Merged

- Your plugin will appear in `index.json`
- It will be discoverable by Potions users
- You can update it by submitting new PRs
- Keep your repository maintained and accessible

Thank you for contributing to the Potions Plugin Registry!

