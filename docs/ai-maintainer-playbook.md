# AI Maintainer Playbook

This doc is the shared human + AI reference for release work, packaging hotfixes, and GitHub Actions changes in `setmac`.

## Core rules

- Use Conventional Commits.
- Keep one logical change per commit.
- Let semantic-release own version bumps.
- Default to prereleases on `canary` or `beta`.
- Only publish stable when the user explicitly asks.

## Release channels

- `canary` -> auto-publishes `vX.Y.Z-canary.N`
- `beta` -> auto-publishes `vX.Y.Z-beta.N`
- `main` -> stable only through the manual `Release Stable` workflow

## Artifact contract

- GUI app DMG: `dist/Setmac.dmg`
- Standalone CLI: `cli/dist/setmac-cli`
- Release builds run through `scripts/release-build.sh`

## Admin and config UX

- **Admin prompt**: Tools with `requires_admin: true` in tools.json emit `auth_required`. The app shows a native password sheet and forwards the password via stdin. The CLI uses it once to prime `sudo`, then keeps the installer running as the normal user.
- **Config visibility**: The Dotfiles screen shows real status (bundled, on disk, installed, missing) for each config. `configs list` emits `config_status` JSON lines.
- **Navigation**: Sidebar "Dotfiles" is the config management screen; "Configs" category under Tools lists config-only tools.

## Local validation

Run these before pushing release-related changes:

```bash
uv run semantic-release --noop version
just release-dry-canary
just release-dry-beta
NEW_VERSION="9.99.99-test" bash scripts/release-build.sh
just release-verify
```

## Signing and notarization

- Releases are ad-hoc signed by default.
- Full signing/notarization activates automatically when these secrets exist:
  - `APPLE_SIGNING_IDENTITY`
  - `APPLE_CERTIFICATE_P12_BASE64`
  - `APPLE_CERTIFICATE_PASSWORD`
  - `APPLE_ID`
  - `APPLE_APP_SPECIFIC_PASSWORD`
  - `APPLE_TEAM_ID`
- If secrets are missing, include the Gatekeeper workaround in release/install notes:

```bash
xattr -cr /Applications/Setmac.app
```

## Packaging gotchas

- Packaged apps must include SwiftPM resource bundles from `.build/release/*.bundle`.
- Shipped apps should load `tools.json` from `Bundle.main`, not only dev-time paths.
- If a release crashes immediately on launch and the stack mentions `Bundle.module`, inspect the packaged app contents first.

## AI source of truth

- Rule: `.cursor/rules/release-policy.mdc`
- Skill: `.cursor/skills/setmac-release-ops/SKILL.md`
- Agent guidance: `CLAUDE.md`
