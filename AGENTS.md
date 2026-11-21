# Potions Shelf contributor guide

Potions Shelf is a GitHub catalog of plugin metadata. Potions fetches plugin code from the repository in each entry. A listing does not make that code trusted: Potions resolves a Git revision and requires the user to approve unverified repositories before it runs plugin hooks or loads shell configuration.

## Author workflow

- Create plugins with `potions plugin create <name>`.
- Shell-only plugins consist of the generated manifest and `config/init.zsh`.
- Optional executable `install.sh`, `uninstall.sh`, `activate.sh`, and `deactivate.sh` hooks run with the user's permissions through Bash.
- Validate and test through `potions plugin validate ./<name>` and `potions plugin install ./<name>`.
- Generate one catalog entry with `python scripts/create-entry.py ./my-plugin OWNER/my-plugin@vX.Y.Z` (after activating the documented virtual environment). Include `@vX.Y.Z` only for an existing release tag. Keep filename and name equal.
- Never claim self-verification. An author-supplied checksum is not an independent trust check.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the manifest example and submission steps. The schema and validation scripts define accepted catalog fields. Workflows validate changes and generate searchable catalog metadata. Do not execute code from contributed plugin repositories in CI.

## Compatibility

The consumer is the current Potions plugin manager. Its required plugin fields are `name`, `version`, `description`, `author`, and `potions_min_version` in the plugin's own manifest. Shell configuration is read from `config/*.zsh` and `config/*.sh`. Setup hooks are optional. The Shelf `.potion` file is catalog metadata and is distinct from a plugin repository's manifest.

## Security triage contract

Active catalog entries require `reviewed_commit`, a full lowercase Git SHA. The source verifier resolves refs, checks this SHA, and performs bounded static source triage without execution. Keep checks fail closed on unsupported content and scan budgets. New source revisions need fresh triage. Never fabricate human approvals or suppress findings with contributor metadata. Use SECURITY.md for reporting and no-hook incident containment.
