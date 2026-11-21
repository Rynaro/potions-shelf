# Pending catalog entries

The following legacy record is retained while its upstream repository is made compatible with the current Potions plugin manager. The first compatible package is now available at `plugins/plugin-hello-world.potion`.

- `Rynaro/orchid-flask` already contains shell configuration and setup hooks. Add a root `.potion` or `plugin.potions.json` with the required Potions fields, validate and install it locally, then generate a fresh shelf entry. This replaces the legacy checksum field with the repository and release users can review.

A catalog listing makes an entry discoverable. It does not certify the code. Potions asks users to approve unverified repositories and runs plugin hooks and shell configuration with their account permissions.
