# Potions Shelf

Potions Shelf is a public catalog for [Potions](https://github.com/Rynaro/potions) plugins. Anyone can write a plugin, share it from a GitHub repository, or propose it for the catalog. Shelf maintainers review what appears in search. You decide which code runs on your machine.

## Use a plugin

If someone shares a GitHub repository with you, you can install it directly, including from your own fork. Replace `OWNER/REPO` and the tag with the publisher’s details.

```sh
potions plugin install OWNER/REPO@v1.2.3
```

For a community plugin, Potions displays the resolved commit for approval. Review that revision before accepting. Its hooks and shell configuration run with your account permissions. A maintainer can move a tag, so check the commit again when updating.

Open **Plugins** in Potions Desk or run `potions plugin` to manage what you have installed. Try the hello-world example through catalog search and run its command in a new Zsh session.

```sh
potions plugin search shell
potions plugin install plugin-hello-world
```

Open a new Zsh session and run:

```sh
hello-world
```

For a direct tagged installation, use `potions plugin install Rynaro/potions-plugin-hello-world@v1.0.0`. Potions displays the resolved commit for approval.

The `word-navigation` plugin adds Zsh word movement bindings for Ctrl+Left/Right and terminal-specific Alt+F/B sequences. Inspect it and install the standalone release from the Shelf, then open a new Zsh session.

```sh
potions plugin info word-navigation
potions plugin install word-navigation
```

If Potions already manages a bundled copy, add `--force` to switch deliberately to the Shelf source. Replacement preserves its disabled state. [Word navigation source and usage](https://github.com/Rynaro/potions-word-navigation)

The Shelf is community maintained. Anyone can propose an entry and join its public review. Users choose which plugin and revision to trust. The older Orchid record and its restoration steps are in [pending](pending/README.md).

## Build a plugin locally

Start in the directory where you keep your projects. This example adds one command to the generated shell configuration.

```sh
potions plugin create hello
printf '%s\n' 'alias potions-hello="echo Hello from Potions"' >> ./hello/config/init.zsh
potions plugin validate ./hello
potions plugin install ./hello
```

Open a new shell and run `potions-hello`. Local installs link to your project, so you can edit the file and try again in another shell. A shell-only plugin needs the manifest and `config/init.zsh`. When you want to share it, publish the contents of `hello/` at the root of a public GitHub repository. People can install it directly at that point. [Potions plugin authoring guide](https://github.com/Rynaro/potions/blob/main/plugins/CREATING_PLUGINS.md)

## List it on the Shelf

1. Fork this repository and clone your fork next to your plugin checkout, so that `potions-shelf/` and `hello/` are siblings.
2. From the root of your Shelf fork, run the commands below. Replace `OWNER` with the plugin’s GitHub owner. Include the tag only if you have published it. Omitting it selects the default branch.
3. Commit the generated `plugins/<plugin-name>.potion` entry and `index.json` to a branch in your fork and open a pull request against this repository’s `main` branch. The helper updates both files. If you edit the entry afterward, regenerate the index with `python scripts/generate-index.py plugins index.json` before committing.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/create-entry.py ../hello OWNER/hello@v1.2.3
./scripts/validate-manifest.sh plugins/hello.potion
```

The helper copies the metadata from your plugin and records its checkout HEAD as `reviewed_commit`, the exact revision submitted for triage. Publish that commit before submitting. For a checkout copy without Git metadata, pass `--reviewed-commit FULL_SHA`. CI checks the entry against the public repository, reads the plugin manifest at the selected commit, and compares the name and version. It inspects files without executing the plugin. Maintainers review the proposed entry, the source, and the results. [Contribution guide](CONTRIBUTING.md)

## Take part in review

Anyone can comment on an open submission. If you tried a plugin, include the operating system, Potions version, and plugin revision you tested. Report missing or incorrect catalog information on the Shelf. For a bug in the plugin’s behavior, use the plugin repository’s issue tracker. [Open submissions](https://github.com/Rynaro/potions-shelf/pulls) · [Shelf issues](https://github.com/Rynaro/potions-shelf/issues)

## Security and suspicious packages

Shelf maintainers make a best-effort assessment of listed plugin sources to reduce the risk of malicious code reaching users. CI checks the recorded commit, inspects source files, and pauses listings that need security review. Reviews and static scans can miss harmful behavior. Plugin code runs with your account permissions.

The registry's triage covers its listed sources and revisions. Authors and users are responsible for independently distributed plugins installed directly from GitHub, local paths, or other catalogs. Shelf maintainers do not accept responsibility for the security or behavior of those installations.

Report any suspicious listed package. Use [private vulnerability reporting](https://github.com/Rynaro/potions-shelf/security/advisories/new) for sensitive details, or the [public package report form](https://github.com/Rynaro/potions-shelf/issues/new?template=suspicious-package.yml) for nonsensitive concerns. If you have already installed it, follow the clean-shell containment instructions in the [security policy](SECURITY.md) before running lifecycle hooks.
