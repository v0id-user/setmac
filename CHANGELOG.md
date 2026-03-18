# CHANGELOG

<!-- version list -->

## v1.0.2 (2026-03-18)

### Bug Fixes

- Include packaged resources needed at app launch
  ([`d0cbfde`](https://github.com/v0id-user/setmac/commit/d0cbfde71fdd7265a874d85953b72885acc9050d))


## v1.0.1 (2026-03-18)

### Bug Fixes

- Move Apple secret checks into workflow steps
  ([`9061281`](https://github.com/v0id-user/setmac/commit/90612811213b1852d63a67eca796361b3815da6c))

- Sign release artifacts and support notarization
  ([`8802d8d`](https://github.com/v0id-user/setmac/commit/8802d8d422306d4052cc0b653e65695135449157))

### Chores

- Add local release dry-run and verification recipes
  ([`3be2ef1`](https://github.com/v0id-user/setmac/commit/3be2ef1f5f6ff838d647cbd096ff189198cd301a))

### Continuous Integration

- Split releases into canary beta and stable workflows
  ([`04b8405`](https://github.com/v0id-user/setmac/commit/04b840505e953c34a39e2309818153b961d38aa8))

### Documentation

- Document prerelease policy and Gatekeeper workaround
  ([`e4cd175`](https://github.com/v0id-user/setmac/commit/e4cd175c49f37b9877d7d6c74961bd0632590596))


## v1.0.0 (2026-03-18)

- Initial Release

## Unreleased

### Bug Fixes

- Bypass uv run in dev mode, fix pipe deadlock
  ([`5e5285e`](https://github.com/v0id-user/setmac/commit/5e5285e47d689d0f24fd5a4bc2b5f12eae1f8b93))

- Capture stderr, add timeout, fix log privacy, handle log type
  ([`281ece1`](https://github.com/v0id-user/setmac/commit/281ece103c35eb358608516df0cdab984749a730))

- Harden dev status streaming against pipe stalls
  ([`7315ee0`](https://github.com/v0id-user/setmac/commit/7315ee049097a3105d0944936110163885b914ef))

- Rename bundled CLI binary to setmac-cli to fix APFS case collision
  ([`060e49e`](https://github.com/v0id-user/setmac/commit/060e49eb79a52879d77bdd96d15831c442fa5cf9))

- Use VERSION from env in bundle.sh, fix dmg.sh error message
  ([`03632c1`](https://github.com/v0id-user/setmac/commit/03632c18fd8b75227bd2d055ee8c8c8791642087))

### Chores

- Gitignore PyInstaller spec files
  ([`3d793a0`](https://github.com/v0id-user/setmac/commit/3d793a0d5eff1d450482e2f6a871db04dfcc1bf1))

- Update LICENSE copyright holder
  ([`68401de`](https://github.com/v0id-user/setmac/commit/68401dea82de21253f3bbfc1a4c6cf633c8c6a55))

### Code Style

- Set default sidebar width to 240pt
  ([`157baaa`](https://github.com/v0id-user/setmac/commit/157baaaae4b89b0d8dbd5577fa760431d821f615))

### Continuous Integration

- Add release workflow for stable and beta
  ([`a269eb5`](https://github.com/v0id-user/setmac/commit/a269eb51cdcaba1b880fbbfb7bf20f16495d3aec))

### Documentation

- Add CLAUDE.md and .cursorrules with project conventions
  ([`7cdd2b8`](https://github.com/v0id-user/setmac/commit/7cdd2b8a6f789bef1cbdea6c1d9e1f328ac6acd6))

- Update CLIBridge dev mode docs to reflect venv bypass
  ([`da2938a`](https://github.com/v0id-user/setmac/commit/da2938aca6372043cc828a788b52688fa432b4b4))

- Update README and rules for releases and conventional commits
  ([`3d647ff`](https://github.com/v0id-user/setmac/commit/3d647ffcef3a470fed65697b5994a2dc2dcbc44f))

### Features

- Add os.Logger across all app paths for runtime debugging
  ([`6572697`](https://github.com/v0id-user/setmac/commit/6572697c646ca823a4e2f764beeabbcbab4d9f3a))

- Add semantic-release pipeline with changelog and release recipes
  ([`8ce8d3f`](https://github.com/v0id-user/setmac/commit/8ce8d3f80a3addd66d82e0ca98207c8a31c6344e))

- Stream os.log alongside app in make dev
  ([`fb2af9b`](https://github.com/v0id-user/setmac/commit/fb2af9ba2fac36090a84fdb5145b7cf9b31375b7))

### Refactoring

- Read app version from bundle at runtime
  ([`e82f05d`](https://github.com/v0id-user/setmac/commit/e82f05db85a210588d35aca9e5dc6a4e9c398908))

- Replace Makefile with justfile
  ([`b1530e3`](https://github.com/v0id-user/setmac/commit/b1530e3c507b95cd874fb04778cc52314cc02238))
