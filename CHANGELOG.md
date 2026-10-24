# CHANGELOG

<!-- version list -->

## v2.0.0 (2026-10-24)

### Bug Fixes

- Split CLI output on newline bytes so a split character never drops a line
  ([`dff0ccf`](https://github.com/v0id-user/setmac/commit/dff0ccfa34a1ba79869a821be3b39b3356c4e98a))

- Stop shipping the maintainer's old dotfiles in the app and CLI
  ([`ecae76b`](https://github.com/v0id-user/setmac/commit/ecae76b188327d6c4891ffe263f18f703777dffa))

### Chores

- Add classify-tools.py to sort manifest tools into catalog or review
  ([`8dee9e7`](https://github.com/v0id-user/setmac/commit/8dee9e7d467793df8909236711ff4635770e0e9f))

- Remove the maintainer's old dotfiles from the public repo
  ([`37adfa0`](https://github.com/v0id-user/setmac/commit/37adfa05c2a13645134f96e1dd52364d7297e125))

### Continuous Integration

- Delete Xcode on the end to end runner to free disk
  ([`44b355a`](https://github.com/v0id-user/setmac/commit/44b355aaeddf741c5ba3b702fa2127697d01dab9))

- Let gitleaks skip the scanner's test fixtures
  ([`0fcfb36`](https://github.com/v0id-user/setmac/commit/0fcfb36dbe854e97c58903dbeaa3346265f5d977))

- Make the CI and e2e workflows read-only
  ([`8bcc68e`](https://github.com/v0id-user/setmac/commit/8bcc68e9ce520b664e82239628518ba83ed37a80))

- Pin the CI and e2e workflow actions to commit SHAs
  ([`eb84044`](https://github.com/v0id-user/setmac/commit/eb84044f3839192b9695336ad61421dae747bce0))

- Push release commits with a deploy key instead of the Actions token
  ([`0b864b9`](https://github.com/v0id-user/setmac/commit/0b864b982c7074275f89ece4b37fde431e1040f9))

- Run the end to end test on starter profiles, weekly and for releases
  ([`14f5b03`](https://github.com/v0id-user/setmac/commit/14f5b036b379f18f685ddb8cb51ace185d4bb8cc))

- Sign release commits and tags with a CI-only GPG subkey
  ([`5f02b78`](https://github.com/v0id-user/setmac/commit/5f02b78c1642704dcec8177c60bd1c723920894b))

### Documentation

- Describe git profiles, review and trust
  ([`3fdc825`](https://github.com/v0id-user/setmac/commit/3fdc825f59194ec1eed674baac307555c71d479d))

- Describe opt-in dotfiles, backups, capture and the scanner
  ([`b33ea47`](https://github.com/v0id-user/setmac/commit/b33ea477648bfd9a48e6c5bd47599173e16d7aa0))

- Describe profile export
  ([`ae9d75a`](https://github.com/v0id-user/setmac/commit/ae9d75a6acdb658d5dd88bb4d5a6e0e403b2c0fb))

- Describe profiles, starters and the neutral catalog
  ([`5496593`](https://github.com/v0id-user/setmac/commit/5496593f350ba1286d3905ae9324f6b604d58773))

- Describe signed CI releases and the release environment
  ([`a391928`](https://github.com/v0id-user/setmac/commit/a3919288c29623c2888c83063ec959139e4700dd))

- Describe the app's profile flow and the new events
  ([`efc435a`](https://github.com/v0id-user/setmac/commit/efc435a95936361ef1a391c2ed38687cf1a9c7e3))

- Describe the end to end workflow
  ([`1a9f4c2`](https://github.com/v0id-user/setmac/commit/1a9f4c21113ebac151a55e093a9adf5218cfa0a5))

- Describe the protocol fixture, data-driven categories and load errors
  ([`5331b84`](https://github.com/v0id-user/setmac/commit/5331b84b59ad308438305aa866229f3bd50df2f1))

- List the catalog's new tools
  ([`003a45c`](https://github.com/v0id-user/setmac/commit/003a45c6d3e580f7e5b7b3706fa62afa26339525))

- Say plainly what the Actions bypass on main skips
  ([`5f1391d`](https://github.com/v0id-user/setmac/commit/5f1391d99eb1290f8c4535abfe491bf5ddc2b2b2))

### Features

- Add DevOps CLIs, apps, Rust and editor extensions
  ([`684a859`](https://github.com/v0id-user/setmac/commit/684a85931edd936aebde55ea0bb612c753d58d5e))

- Install the tools a profile picks from a neutral catalog
  ([`0c8a0fb`](https://github.com/v0id-user/setmac/commit/0c8a0fbc69fe67ac0f12ec9892af1128f4761472))

- Profile screen, review before trust, first-run choice and per-file dotfiles in the app
  ([`bd69c14`](https://github.com/v0id-user/setmac/commit/bd69c14580babecea43971740ba2e24140ffdd9d))

- Show the active profile's tools in the app
  ([`e1e8af2`](https://github.com/v0id-user/setmac/commit/e1e8af2a78ee274140421ed54f433adc2dceea70))

- Show why the manifest failed to load and keep tools in undefined categories
  ([`d04c97e`](https://github.com/v0id-user/setmac/commit/d04c97e98f7fc3152f1fdec29af1d57d7ae3cdd8))

- Use pnpm, CocoaPods, Watchman, kubectl, Helm and yq in the starters
  ([`fc3d609`](https://github.com/v0id-user/setmac/commit/fc3d609554817500ee117e9a47d29b09419c36cb))

- **cli**: Add the JSON events the app needs for profiles and dotfiles
  ([`0463e5d`](https://github.com/v0id-user/setmac/commit/0463e5da09a1e8584c61aa019849b3ad74b2fb43))

- **cli**: Export an old all-in-one setup into a private profile folder
  ([`35c2d9e`](https://github.com/v0id-user/setmac/commit/35c2d9e8c7136856cbaf1c86c9c5792ec4f2e69e))

- **cli**: Load profiles from git and run them only after review and trust
  ([`cc0861e`](https://github.com/v0id-user/setmac/commit/cc0861e65f6542af0298597204ec3fb949ab9099))

- **cli**: Make dotfiles opt-in per file, with a diff, backups and restore
  ([`b230639`](https://github.com/v0id-user/setmac/commit/b2306390d70785c515bf223aaa0eb9d69f68ff9c))

- **cli**: Scan dotfiles for secrets and personal data
  ([`fa9e455`](https://github.com/v0id-user/setmac/commit/fa9e45539cfc15623bc3ca7a45834604affbf82a))

### Refactoring

- Keep the e2e branch's personal tools out of the catalog
  ([`edc7066`](https://github.com/v0id-user/setmac/commit/edc70660575358b268f1dfc5ff6f87cd092213d9))

### Testing

- Scan all of Resources for personal data now that no dotfiles ship
  ([`7b0a0c6`](https://github.com/v0id-user/setmac/commit/7b0a0c6daf6570d9dd6b09e62940c62e6ea39e3a))

- **cli**: Pin every JSON-line event with a golden fixture
  ([`9c690ec`](https://github.com/v0id-user/setmac/commit/9c690ec7f1ad5576e9878422c5ce83f327560864))


## v1.3.0 (2026-10-24)

### Bug Fixes

- Build AppIcon.icns at bundle time and fail when the icon is missing
  ([`73fc725`](https://github.com/v0id-user/setmac/commit/73fc725d03f1cd05f6e24211af23d5817c46cb65))

- Seed the icon grain so draw-icon.swift is reproducible
  ([`31a1e87`](https://github.com/v0id-user/setmac/commit/31a1e8784ae421dae5ff9be248eb661d9131320f))

- **cli**: Reinstall a cask brew lists when its app is missing
  ([`5209f88`](https://github.com/v0id-user/setmac/commit/5209f8851075ec9707f1505f24617b759a433c2d))

- **cli**: Trust check.path for brew casks so an interrupted install is not reported installed
  ([`5d7a8bb`](https://github.com/v0id-user/setmac/commit/5d7a8bb4f07648650c179a6053894b797e113a2c))

### Chores

- Add editorconfig matching the repo's indentation
  ([`d55340d`](https://github.com/v0id-user/setmac/commit/d55340d6d928f3afdfb010636557cbfcbbc1fb5f))

- Check the app icon in release-verify, including inside the DMG
  ([`caff881`](https://github.com/v0id-user/setmac/commit/caff8815e38c8fd498a72bd1054e7e747a8f4326))

- Ignore secrets, agent worktrees and generated icons
  ([`8b0c3d0`](https://github.com/v0id-user/setmac/commit/8b0c3d02aafe9735edc1dfa88055a82f1b47142b))

### Continuous Integration

- Scan for secrets with gitleaks, add lefthook hooks and dependabot
  ([`d3611ec`](https://github.com/v0id-user/setmac/commit/d3611ec5c0963d04314c5d0e5eb0ee0f628f8cf4))

### Documentation

- Add security policy, contributing guide, code of conduct and GitHub templates
  ([`8a1c9d1`](https://github.com/v0id-user/setmac/commit/8a1c9d1ab3e5492d1cf1fd86c502c615268e47d3))

- Describe the icon pipeline
  ([`b081726`](https://github.com/v0id-user/setmac/commit/b0817268adc87ce52059d7f5a67a9a175773f818))

- Describe the skipped event, cask path check, dry run and validator
  ([`0955206`](https://github.com/v0id-user/setmac/commit/09552067f0ce0ac9e8c563c7e9b40961dd60a24e))

- Drop stale tool counts and home path, fold .cursorrules into CLAUDE.md
  ([`d769c81`](https://github.com/v0id-user/setmac/commit/d769c81798da4018f098fdb2b8dd04105d762848))

### Features

- Add the sprout app icon
  ([`a199224`](https://github.com/v0id-user/setmac/commit/a199224730f57e898367781a46192c1a324e1167))

- Show the app icon in the Dock under swift run and in About
  ([`222033b`](https://github.com/v0id-user/setmac/commit/222033bfdd9a11b55b12061b5a7c1a3d0d93c72f))

- **cli**: Enforce requires_admin with an up-front password check and a needs_admin skip
  ([`0819045`](https://github.com/v0id-user/setmac/commit/0819045d75149d056dcc27c071ca74ff29cfe12b))

- **cli**: Validate manifests with structured problems
  ([`e5a2c97`](https://github.com/v0id-user/setmac/commit/e5a2c97d8efbef526bb32fbbbc9129ac9fa0c2cb))


## v1.2.0 (2026-10-23)

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
