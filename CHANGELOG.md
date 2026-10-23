# CHANGELOG

<!-- version list -->

## v1.2.0-canary.1 (2026-10-23)

### Bug Fixes

- Capture configs outside the app bundle in packaged builds
  ([`35f97e3`](https://github.com/v0id-user/setmac/commit/35f97e3482abafece82580c4269d990ce3db8167))

- Find dev resources from the source location
  ([`af06140`](https://github.com/v0id-user/setmac/commit/af061407396fa01f17de807f95b45dc9d83b6de3))

- Install Command Line Tools without the GUI dialog
  ([`7687dcf`](https://github.com/v0id-user/setmac/commit/7687dcfb48891835591d4776a287aee8aa9404f8))

- Install Pier from its release DMG
  ([`0769513`](https://github.com/v0id-user/setmac/commit/076951349faac5c00538a5a19efcd192a84695df))

- Let app installs run to completion and add Cancel
  ([`bf02b5f`](https://github.com/v0id-user/setmac/commit/bf02b5f129c8d814c50939274f6aeb2535d47c56))

- Let brew pkg casks reach the admin password
  ([`127bf6f`](https://github.com/v0id-user/setmac/commit/127bf6f0627bb698d703a411ba9d0fface3d6f0e))

- Let canary and beta releases build
  ([`acef73d`](https://github.com/v0id-user/setmac/commit/acef73dc45b4cd2865e1d513738d1606e58a258b))

- Make CLI installs truthful, streamed and cancellable
  ([`b1e65ed`](https://github.com/v0id-user/setmac/commit/b1e65edd49f5a7478a0a64e1fa2bdbf09b2391c5))

- Put Homebrew on PATH in the bundled zshrc
  ([`104483e`](https://github.com/v0id-user/setmac/commit/104483e44872314d114df70677b9456056c31d31))

### Chores

- Build Info.plist from Resources and drop PyInstaller strip
  ([`9f1d3bc`](https://github.com/v0id-user/setmac/commit/9f1d3bc2b04a7e6c451c20c6fa5c05d613da03d5))

### Continuous Integration

- Add an end to end install test on a stripped macOS runner
  ([`b8937f6`](https://github.com/v0id-user/setmac/commit/b8937f63f695ef9d0e1d920b0719b9b04be1e000))

### Documentation

- Add revival plan and update CLI protocol notes
  ([`0a9ae39`](https://github.com/v0id-user/setmac/commit/0a9ae3937e4cbfff3edc516bebd3f23e0a70c2bb))

- Describe phase 2 and 3 changes
  ([`718097b`](https://github.com/v0id-user/setmac/commit/718097b602daa2a6665be0a057f5c577f25e928b))

### Features

- Add mise, mas and macOS settings install methods
  ([`e9d745a`](https://github.com/v0id-user/setmac/commit/e9d745a5a58e418f8c57219a559eec60c6b0ff88))

- Export the manifest as a Brewfile
  ([`c849fc5`](https://github.com/v0id-user/setmac/commit/c849fc5e3ee6937e26e96ba6d857c60544d69374))

- Manage runtimes with mise and add App Store apps and macOS settings
  ([`a994846`](https://github.com/v0id-user/setmac/commit/a99484660a0e3952a72b911c08fd8bd9190d9bed))

- Retry failed tools and list manual setup steps
  ([`ca29ed8`](https://github.com/v0id-user/setmac/commit/ca29ed83d0c43828bd6a8d4a3b23920fd459835b))

### Testing

- Add CLI tests and run them in CI
  ([`325000c`](https://github.com/v0id-user/setmac/commit/325000c54c3493e456521352cc435ce22ab8a210))

- Run the askpass helper test only on macOS
  ([`7c79125`](https://github.com/v0id-user/setmac/commit/7c79125cd4396113616a7edc95283089540b952a))


## v1.1.1 (2026-03-18)

### Bug Fixes

- Keep Homebrew installer running as user
  ([`101298e`](https://github.com/v0id-user/setmac/commit/101298e735dbd33f1b128d06a581ff2060a74986))

### Documentation

- Clarify non-root Homebrew auth flow
  ([`d5898f5`](https://github.com/v0id-user/setmac/commit/d5898f5634a884157e3cabd363316521446b329f))


## v1.1.0 (2026-03-18)

### Documentation

- Add AI maintainer playbook
  ([`2726731`](https://github.com/v0id-user/setmac/commit/2726731fd18eb300e98d7b6415c95586ce7a3cac))

- Add project skill for release operations
  ([`53656a4`](https://github.com/v0id-user/setmac/commit/53656a4d1ca50c9476aba822e966dd1b6a339762))

- Document admin prompt and config visibility UX
  ([`b6fd54a`](https://github.com/v0id-user/setmac/commit/b6fd54a9109a2dabdecb32a0bb3d75a091a829ee))

- Persist release policy for AI agents
  ([`5bd984d`](https://github.com/v0id-user/setmac/commit/5bd984d4ced2f3d2a59ed3b2453709376f0083ed))

### Features

- Add admin password prompt, config visibility, and tooltips
  ([`f26ce5e`](https://github.com/v0id-user/setmac/commit/f26ce5e5c6af5ee1dd9a74ab336cda41dee27cd5))


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
