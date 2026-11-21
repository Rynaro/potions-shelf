# Pending catalog entries

These records are retained here while their linked repositories are made compatible with the current Potions plugin manager. `plugins/` remains empty so search does not advertise entries that are not ready to install.

- `Rynaro/orchid-flask` already contains shell configuration and setup hooks. Add a root `.potion` or `plugin.potions.json` with the required Potions fields, validate and install it locally, then generate a fresh shelf entry. This replaces the legacy checksum field with the repository and release users can review.
- `Rynaro/potions-plugin-hello-world` needs a root plugin manifest and an implementation, such as `config/init.zsh` for a shell-only plugin. For this repository name, Potions removes the leading `potions-` and installs the plugin as `plugin-hello-world`. Use that name in its manifest and regenerate the entry as `plugins/plugin-hello-world.potion`.

A catalog listing makes an entry discoverable. It does not certify the code. Potions asks users to approve unverified repositories and runs plugin hooks and shell configuration with their account permissions.
