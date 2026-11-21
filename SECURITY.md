# Registry security

Potions Shelf maintainers make a best-effort assessment of listed plugin code to reduce the risk of malicious changes reaching users. Plugins run with the user's account permissions. Static checks and review can miss harmful behavior, and a listing provides no guarantee that code is safe.

The Shelf's triage applies to sources and revisions listed in this registry. Authors and users are responsible for plugins installed directly from GitHub, local paths, or other catalogs. Potions Shelf maintainers do not accept responsibility for the security or behavior of those independently distributed plugins.

## Report a suspicious package

Report every suspicious package listed in the Shelf, even when you are unsure whether it is malicious. Include its catalog name, repository, affected revision, and a short description or file location. You can find the installed revision in `Potionfile.lock`. You do not need to run suspicious code to make a report.

Use [private vulnerability reporting](https://github.com/Rynaro/potions-shelf/security/advisories/new) for credentials, personal data, exploitable vulnerabilities, or details that could put users at risk. For nonsensitive concerns, use the [suspicious-package form](https://github.com/Rynaro/potions-shelf/issues/new?template=suspicious-package.yml). Keep secrets and working exploit code out of public issues.

If you suspect an installed plugin, avoid its lifecycle commands because its deactivate or uninstall hooks can also run code. Start a clean shell with `zsh -f`, keep the source unexecuted, and move the exact installed directory or link outside the loader's plugin directory. Replace `PACKAGE_NAME` with the installed package name. This preserves files for investigation without invoking plugin hooks.

```sh
zsh -f
plugin_root="${POTIONS_HOME:-$HOME/.potions}"
quarantine_dir=$(umask 077; mktemp -d "$plugin_root/quarantine.XXXXXX")
mv "$plugin_root/plugins/PACKAGE_NAME" "$quarantine_dir/PACKAGE_NAME"
```

Open a fresh shell after containment. Existing sessions may still hold functions or processes loaded by the plugin. Check its external changes and restore affected files from trusted backups as appropriate. Preserve sensitive evidence privately.

## Triage before listing and on updates

Each entry contains `reviewed_commit`, the exact source revision submitted for triage. The entry helper reads the plugin checkout's `HEAD`, or accepts an explicit full SHA with `--reviewed-commit`. This field identifies the assessed code. It records no claim that a person has approved it.

CI resolves the selected GitHub tag or branch and requires it to match that SHA. It inspects every tracked source blob from the same Git tree without executing plugin code. The scan flags command-like network access, dynamic execution, privilege changes, credential access, persistence, destructive operations, and private-key material. Findings identify either high-risk behavior or a required manual review. Both pause listing until resolved; ordinary mentions in prose and fixed shell handoffs such as `exec zsh` pass. Unsupported binary content, file modes, or exceeded scan budgets block the check so partially inspected sources cannot receive a clean result.

The scan is deliberately conservative and may flag examples or legitimate operations. A failed result pauses listing. The author and maintainer review the locations and simplify or remove the behavior before resubmitting a revision. Authors cannot suppress findings in a catalog entry. If essential behavior cannot pass the current checks, maintainers can keep the entry pending while improving the checks through a separately reviewed code change. Community distribution directly from its repository remains available.

Maintainers review the source and installation behavior before merging. They inspect hooks, dependencies, network destinations, data access, privileges, persistence, reversibility, and unexpected changes since the previous revision. A new commit needs fresh triage. Review PRs against their final head. The protected-main workflow requires the `validate` and `verify-sources` checks on pull requests. Both checks also run for documentation changes and merge-queue candidates. Catalog changes include their deterministic `index.json` in the same pull request. The publication workflow verifies that committed index with read-only permissions, so it needs no bot exception to branch protection. Repository administrators manage the required checks and review rules.

Clients that enforce `reviewed_commit` compare the fetched commit before installation hooks run. Potions 2.18.0 predates this enforcement and resolves the repository ref independently. Upgrade Potions to obtain registry commit enforcement. Direct and local plugins always require the user's own source review.

## Recheck and respond

Publication reruns source triage and verifies that the committed index matches its catalog entries. A daily read-only GitHub Actions audit rechecks every active source, detecting moved refs and new availability problems. The workflow records expected and resolved commits and finding locations in a JSON artifact retained for 30 days. Reports omit contributed code and secrets. Failed workflows need maintainer attention through the repository's Actions notifications.

For a report or failed audit, maintainers establish the affected package and commit, preserve the report and workflow evidence, and investigate without running the suspected code. If the package could harm users, remove its manifest from `plugins/`, move a safe catalog record and redacted status to `pending/`, keep sensitive evidence and reports private, regenerate `index.json`, and merge that quarantine promptly. Communicate affected revisions and recovery guidance using a security advisory when appropriate. Coordinate a fix with the author and run fresh triage before restoring the listing.

A failed audit itself does not remove an index entry or disable installed plugins. Quarantine prevents discovery and future registry installs after clients refresh their cache. Users with an affected installation need to follow the clean-shell quarantine steps above and start fresh sessions. A plugin's external changes may need additional recovery.
