---
name: setmac-release-ops
description: Manage setmac releases, semantic-release versioning, signing, notarization, and packaged app hotfixes. Use when working on GitHub Actions release workflows, changelog/version bumps, DMG or standalone CLI artifacts, Gatekeeper issues, or launch failures in shipped builds.
---

# Setmac Release Ops

## Use this skill when

- the user asks to cut `canary`, `beta`, or stable releases
- a release workflow or semantic-release config needs changes
- signing, notarization, or Gatekeeper behavior is involved
- the shipped app crashes or behaves differently than `swift run`
- AI instructions for release work need updating

## Core rules

- Use Conventional Commits.
- Keep one logical change per commit.
- Do not hand-edit release version numbers.
- Default to `canary` or `beta` unless the user explicitly asks for stable.

## Release model

- `canary` -> `vX.Y.Z-canary.N`
- `beta` -> `vX.Y.Z-beta.N`
- stable -> manual `Release Stable` workflow from `main`

## Required outputs

- `dist/Setmac.dmg`
- `cli/dist/setmac-cli`

## Validation checklist

Run the smallest relevant set:

```bash
uv run semantic-release --noop version
just release-dry-canary
just release-dry-beta
NEW_VERSION="9.99.99-test" bash scripts/release-build.sh
just release-verify
```

## Packaging and signing notes

- Release builds must go through `scripts/release-build.sh`.
- Packaged apps must include SwiftPM resource bundles from `.build/release/*.bundle`.
- Shipped resources should load from `Bundle.main`.
- Ad-hoc signing is acceptable as a fallback, but note that Gatekeeper may still block downloads until Apple notarization secrets are configured.

## Reference

Read `docs/ai-maintainer-playbook.md` for the full release and hotfix workflow.
