# Contributing to Potions Shelf

Add one catalog manifest for a Potions plugin repository. Keep the entry small so maintainers can review it and users can identify the source easily.

## Before submitting

1. Create the plugin using `potions plugin create <name>`.
2. Add your shell configuration in `config/init.zsh` and optional setup hooks only when needed.
3. Test locally with `potions plugin validate ./<name>` and `potions plugin install ./<name>`.
4. Publish the source repository on GitHub. Use a release tag when you want users to install a named version.
5. Generate `plugins/<name>.potion` from your scaffold and GitHub owner/repository. Add `@v0.1.0` only when that tag exists and you want catalog installs to select it.
6. Run `bash scripts/validate-manifest.sh plugins/my-plugin.potion`, then open a pull request.

## Generate the catalog entry

Set up the script dependencies in a virtual environment once, then run the helper with the published GitHub owner/repository. It reads your scaffold and creates `plugins/<name>.potion` for you.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/create-entry.py ./my-plugin your-github-name/my-plugin@v0.1.0
```

Omit `@v0.1.0` when you want installs to follow the repository default branch. Include it only when that release tag exists. The helper copies the Potions plugin name, version, description, author and optional license into catalog metadata, checks the generated entry against the catalog schema, and refuses to overwrite an existing file.

A minimal catalog entry looks like this:

```yaml
name: my-plugin
version: "0.1.0"
description: "A short description of what the plugin adds"
author: "your-github-name"
repository: "https://github.com/your-github-name/my-plugin"
license: "MIT"
tags:
  - shell
```

Only add optional fields supported by the catalog schema and backed by the repository. Do not set `verified: true` yourself. Do not add a checksum and describe it as proof of safety. A checksum controlled by the plugin publisher does not independently authenticate that publisher or make its code safe.

## Local validation

Install the repository's Python requirements, then validate the manifest:

```sh
python3 -m pip install -r requirements.txt
bash scripts/validate-manifest.sh plugins/my-plugin.potion
```

The pull request workflow also validates changed manifests and checks the linked GitHub repository. Review any checks before requesting review.

## User trust and security

A catalog listing makes a plugin discoverable. It is not a security certification. Potions installs code from the listed GitHub repository, resolves the requested ref to a commit, and asks users to approve an unverified repository before running its hooks or loading its shell configuration. Scripted installation requires the user to pass `--trust` explicitly after reviewing the repository.

Plugin setup hooks execute with the user's account permissions. Keep them short and idempotent, quote paths, and back up user files before changing them. Avoid credentials, remote shell-pipe installers, and unexplained binary downloads. Document any external changes and how users can undo them.

## Pull request review

A submission should have one clear owner, a reachable repository, a matching plugin name, accurate metadata, and code that works with the current Potions plugin format. The maintainer review considers the source and its installation behavior. Automated scans are aids for review and cannot establish that arbitrary shell code is harmless.
