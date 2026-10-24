# setmac

macOS developer environment installer — automates reinstalling all dev tools, apps, and configs after a fresh format.

## Architecture

- **SwiftUI macOS app** (SPM, macOS 26+) — native sidebar UI, streams live status/logs
- **Python CLI backend** (`uv` + `click`) — does all actual installing via subprocess
- **Public catalog `Resources/tools.json` + profiles** — a profile (`Resources/profiles/<name>/profile.json` or the user's own folder) picks catalog tools and adds its own; the CLI merges them and the app shows the CLI's merged list
- SwiftUI spawns CLI via `Process`, reads JSON-line stdout, updates UI in real-time

## Project Structure

```
Sources/               # SwiftUI app (SPM target: "Setmac")
├── App/               # SetmacApp.swift, ContentView.swift
├── Models/            # InstallState.swift, ToolManifest.swift
├── Navigation/        # SidebarItem, SidebarView, DetailView
├── Views/             # OverviewView, CategoryDetailView, ToolCardView, etc.
└── Services/          # CLIBridge.swift, ManifestLoader.swift (decode error text, devRepoRoot)

cli/                   # Python CLI (uv project: "setmac-cli")
├── src/setmac/
│   ├── cli.py         # click entry point
│   ├── output.py      # JSON-line protocol (thread-safe)
│   ├── registry.py    # Merged manifest, dependency graph, get_registry(ctx)
│   ├── profile.py     # Profile resolution, loading, merging with the catalog
│   ├── gitprofile.py  # Git profiles: clone, pin (lock), content hash
│   ├── trust.py       # Trust store and the review text
│   ├── scanner.py     # Secret and personal-data scanner for dotfiles
│   ├── validate.py    # Manifest and config-path rules (structured problems)
│   ├── commands/      # install, status, configs, brewfile, profile
│   └── installers/    # brew, script, custom dispatchers

Resources/
├── tools.json         # Public tool catalog (no dotfiles, no personal tools)
├── profiles/          # Starter profiles: minimal, web, backend, mobile
├── configs/           # Old dotfiles, unused and unbundled; deleted after the private profile exists
├── icon.png           # App icon source (1024x1024, drawn by scripts/draw-icon.swift)
└── Assets.xcassets    # Accent color

scripts/               # build-cli.sh, bundle.sh, draw-icon.swift, generate-icon.sh, dmg.sh, classify-tools.py
```

### App icon
`Resources/icon.png` is the only committed icon. `scripts/bundle.sh` turns it into `Contents/Resources/AppIcon.icns` (via `generate-icon.sh`, standard 10-image iconset) and fails if it is missing. `Info.plist` names it with `CFBundleIconFile` only: there is no `Assets.car` because Command Line Tools have no `actool`. Under `swift run` the app sets its Dock icon from the SwiftPM copy of `icon.png`. `just verify-icon` checks a bundle; `release-verify` runs it on the app and inside the DMG.

## Key Commands

Uses `just` (not `make`) as the command runner.

```bash
just dev               # Clean build + run with live os.log streaming
just build             # swift build (incremental)
just release           # swift build -c release
just bundle            # .app bundle with embedded CLI + configs
just status            # CLI: check all tool statuses
just capture-configs   # CLI: snapshot current dotfiles
just                   # List all available recipes
```

## Critical Conventions

### CLI binary naming
The bundled CLI binary is named `setmac-cli` (NOT `setmac`) to avoid case-insensitive APFS collision with the GUI binary `Setmac`. This applies to:
- `CLIBridge.swift` — looks for `setmac-cli`
- `scripts/build-cli.sh` — PyInstaller outputs `setmac-cli`
- `scripts/bundle.sh` — copies `setmac-cli` into .app bundle

### JSON-line protocol
CLI stdout emits one JSON object per line:
```json
{"type": "status|progress|log|error|complete|skipped|auth_required|config_status|summary|manifest|profile_error", "tool": "tool-id", "message": "...", "status": "installed|not_installed", "version": "1.0"}
```
Thread-safe via `threading.Lock()` in `output.py`.

- **auth_required**: Sent at most once per run (it is cached after that): up front when a `requires_admin` tool still needs installing and `sudo -n true` fails, otherwise the first time an installer calls `sudo -A` (for example when a terminal's cached sudo ticket passed the up-front check, but installers run without that tty). The app shows the password sheet and writes the password to stdin. The CLI verifies it with `sudo -S -v`, re-asks on a wrong password, and caches it for the run. Installers reach it through `SUDO_ASKPASS` (`cli/src/setmac/askpass.py`), so scripts call `sudo -A`.
- **skipped**: `{"type": "skipped", "tool": "tool-id", "status": "needs_admin"}`, sent right after the `error` line for a `requires_admin` tool that was not attempted because the password was refused or cancelled. The `error` line carries the message; the tool is also in the summary's `failed` list.
- **summary**: Last line of an install run: `{"type": "summary", "message": "...", "failed": ["tool-id"]}`. The CLI exits 2 when anything failed, so the app treats exit 2 as a normal result, not a crash.
- **config_status**: Emitted by `configs list` for bundled/system/missing status (kept for the app until it uses `configs`).
- **configs**: `{"type": "configs", "configs": [{id, tool, source, target, is_dir, status}]}` from `configs list --json`; status is missing, identical or differs.
- **manifest**: `{"type": "manifest", "profile": "web", "manifest": {...tools.json shape...}}` from `profile show --json`. The app loads its tool list this way at launch and on Retry.
- **profile_error**: `{"type": "profile_error", "profile": "...", "message": "...", "problems": [{code, tool_id, field, message}]}` when the active profile cannot be used, followed by a plain `error` line without a tool. The CLI exits 3.
- `cli/tests/fixtures/protocol.jsonl` pins the exact line of every event type (`test_protocol.py`). Add event types or fields; never rename or drop them.

### CLIBridge.swift
- Dev mode: runs `cli/.venv/bin/setmac` directly (bypasses `uv` to avoid GUI hangs). Falls back to `uv run --frozen` if venv not set up.
- Bundle mode: runs embedded `Contents/MacOS/setmac-cli <args>`
- Uses `readabilityHandler` + `terminationHandler` (not async iteration)
- Sets rich PATH for subprocess tools (homebrew, cargo, bun, etc.)
- Uses a Pipe for stdin (not null) so `providePassword` can inject admin when auth_required is received.
- Install commands have no timeout; status and config listings time out after 120 s. `cancel()` sends SIGTERM, and the CLI stops its installer's whole process group.
- All views run commands through `InstallState.run`, which allows one command at a time and answers password requests.

### Install methods
`brew_formula`, `brew_cask`, `mise` (target like `node@lts`, checked with `mise where`), `mas` (App Store id), `defaults` (a `defaults` list of `{domain, key, type, value}`, written only when different), `script`/`custom`, and `config` (applied by the configs step).

### Install checks
- `brew_formula` tools count as installed only when `brew list` shows them. A fresh Mac's stub `/usr/bin/git`, `python3` and `ssh` pass `command -v`, so `check.command` is ignored for formulae.
- `brew_cask` tools with a `check.path` count as installed only when that path exists (an interrupted cask install is still listed by brew). Without a path, `brew list` or `check.command` decides. A cask brew lists but whose path is missing is fixed with `brew reinstall --cask`.
- `install --dry-run` prints each status, what would be installed, and which tools need the admin password, and changes nothing.
- `cli/src/setmac/validate.py` holds the manifest rules (known method, required fields, unique ids, known deps, no cycles). `Registry` refuses to load a manifest with any problem; `validation_problems()` returns them as `{code, tool_id, field, message}`.
- A tool whose dependency failed is skipped, not attempted. `install all` never applies dotfiles; `--with-configs` does, last, skipping configs of failed tools (asks per file, or `--yes`). `--no-configs` is a hidden no-op for old scripts.
- Tests: `cd cli && uv run pytest`.

### Logging
Uses `os.Logger` with subsystem `com.v0id.setmac`. Categories: CLIBridge, ContentView, InstallState, CategoryDetail, ConfigsView. View with:
```bash
log stream --predicate 'subsystem == "com.v0id.setmac"' --level debug
```

### Profiles
- Active profile: `--profile <spec>` (global option), then `SETMAC_PROFILE`, then the pointer file `~/Library/Application Support/setmac/active-profile` (written by `profile use`), then `minimal`. A spec is a starter name, an absolute/`~` path, or a git URL with an optional `#ref`.
- Git profiles (`gitprofile.py`): cloned with the system git (no prompts without a TTY), cached under `~/Library/Application Support/setmac/profiles/<slug>/<sha>/`, pinned by `profile.lock.json` (url, ref, sha, content hash). A moved branch changes nothing until `profile update`; a tampered cache or a different `#ref` is an error.
- Trust (`trust.py`): non-starter profiles must be trusted for their exact content (dir path or url+sha, plus a SHA-256 of every file) in `trust.json`. `get_registry(ctx, require_trust=True)` is used by every command that runs profile code: install (including `--dry-run`), status (check commands are shell) and configs apply/capture. `profile show`, `review`, `validate`, `brewfile` and `configs list` do not need trust. Untrusted → `profile_error` with code `untrusted_profile`, exit 3.
- `profile review` prints every install/check command verbatim, flags download-and-run (`curl | sh`), and lists dotfile locations, `sensitive_ok`, admin tools, taps and notes. `profile trust` / `update` confirm on a TTY or need `--hash <content hash>`.
- `extends`: a bare name is a starter; a path inside the profile folder needs a slash (`./base`) and must resolve inside it (no symlink escape); at most 3 levels, no cycles, no `..`.
- Merge: root profile first; `tools.add`/`remove` pick catalog ids, `custom_tools` add the profile's own (a catalog id clash is an error), `overrides` patch a tool (nested objects merge one level). Dependencies are pulled in; removing one that a selected tool needs is an error. `defaults`-method tools are in only when `macos_defaults.enabled`.
- Every command gets its registry from `get_registry(ctx)` in `registry.py`; never build `Registry()` from the catalog in a command.
- Config fields keep their old meaning: `source` is the file on the Mac (`~/...`), `target` is its copy under the profile's `configs_dir`. `validate.py` refuses paths outside home (symlinks resolved), `..`, and the sensitive locations unless listed in `sensitive_ok`.
- Tests: `tests/test_profile.py` (resolution, merging, config paths, neutrality of `Resources/`) and `tests/test_gitprofile.py` (a local repo as the remote: pinning, trust, update, tampering).

### Dotfiles (`commands/configs.py`, `scanner.py`)
- Only from the active profile (`Tool.configs_root`); there is no global configs folder. A config's id is its `target`.
- `apply [--only ids] [--yes] [--dry-run]`: confirm per file on a TTY, else `--yes` is required. Replaced files are moved (never followed if symlinks) to `~/.config/setmac-backup/<time>/` with `manifest.json`; `restore <time|latest> [--only]` backs up the current state, restores, and removes files the apply created. Backup folder names never repeat.
- `capture [ids] [--accept-medium]`: only into a local profile folder (not a starter, a git checkout, or a clone of the public repo); stages with `.setmacignore` + `~/.config/setmac/ignore`, scans, and writes nothing if anything blocks.
- Scanner: high (GitHub/OpenAI/Anthropic/Slack/AWS tokens, private keys, JWTs, assigned secrets) always blocks; medium (emails, `/Users/<name>`, `*.local|lan|internal`, high-entropy strings) blocks capture unless accepted. `apply` blocks on high only. Allow with `.setmac-scan-allow` (`rule-id:path-glob`). Findings show a redacted snippet, never the value.
- `Resources/configs` is the maintainer's old dotfiles, no longer read or bundled; it is deleted once the private profile holds them.

### No hardcoded tools
Everything is data-driven from `tools.json`. No tool names hardcoded in Swift or Python. Only `custom` install method needs dedicated installer code.

Sidebar categories come from the manifest's optional `categories` list (`id`, `name`, `icon`, `color`, `order`), else the built-in set in `ToolManifest.swift`. Tools in a category nobody defined show under **Other**, never disappear. A manifest that fails to load shows its error (file and JSON path) with a Retry button instead of an empty sidebar.

## Git Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/) for semantic-release:

```
feat: add new feature
fix: resolve bug
chore: maintenance
```

Types: `feat`, `fix`, `refactor`, `chore`, `docs`, `style`, `test`, `ci`. Use `feat!:` or `fix!:` for breaking changes.

One logical change per commit: group related edits (all release pipeline files in one `feat`, all doc updates in one `docs`). Every commit and tag is GPG-signed.

## Release Pipeline
- **Persistent rule**: Also follow `.cursor/rules/release-policy.mdc` as the project source of truth for release, versioning, signing, and Gatekeeper workaround policy.
- **Project skill**: Use `.cursor/skills/setmac-release-ops/SKILL.md` when working on releases, packaging hotfixes, signing/notarization, or shipped-build failures.
- **Playbook**: Use `docs/ai-maintainer-playbook.md` for the shared human + AI release workflow and validation checklist.
- **Canary**: Push to `canary` → publishes `vX.Y.Z-canary.N` once the maintainer approves the run
- **Beta**: Push to `beta` → publishes `vX.Y.Z-beta.N` once the maintainer approves the run
- **Stable**: Manual only — run "Release Stable" workflow from Actions, default ref `main`. Never auto-release stable.
- **Versioning**: semantic-release is source of truth. Do not manually bump versions.
- **Branch setup**: Create `canary` and `beta` from `main` if missing: `git checkout -b canary main && git push -u origin canary` (same for beta).
- **Signing**: Release builds go through `scripts/release-build.sh`, sign artifacts by default, and only notarize when Apple signing secrets are configured.
- **Signed release commits and tags**: every release job runs in the protected `release` environment (maintainer approval; branches `main`, `canary`, `beta`). `scripts/ci-signing-key.sh` imports a signing-only subkey of the maintainer's GPG key from the environment secrets `RELEASE_GPG_PRIVATE_KEY` and `RELEASE_GPG_PASSPHRASE` and checks it signs before semantic-release runs. semantic-release commits as `commit_author` in `pyproject.toml` (also the committer), whose email must be verified on the key owner's GitHub account. The release commit is pushed straight to `main` over SSH with the `RELEASE_DEPLOY_KEY` deploy key (`actions/checkout` `ssh-key`, plus `ignore_token_for_push` in `pyproject.toml`); deploy keys are the `main` ruleset's only bypass actor, because GitHub Actions cannot be one on a personal account. The bypass skips every `main` rule, including required signatures, so the signing check in `ci-signing-key.sh` is what keeps release commits signed. Keep the release deploy key the repo's only deploy key.
- **Local release (fallback)**: `UV_PYTHON=3.14 uv run semantic-release version --no-push --no-vcs-release` signs with the maintainer's own key; push the release commit through a PR, then the tag, then `gh release create`.
- **User notes**: If a release is only ad-hoc signed, include the Gatekeeper workaround in release/install notes.

## Development Rules

- No Xcode IDE — use CLI (`swift build`, `swift run`) and VS Code
- SPM only — no .xcodeproj
- macOS 26+ (Tahoe) with Liquid Glass UI
- `Window` not `WindowGroup` (single-window app; `WindowGroup` opens duplicate windows)
- Python CLI uses `uv` for dependency management

### Don't

- Don't use `/usr/bin/env` to find `uv` (GUI apps get a minimal PATH)
- Don't use `bytes.lines` async iteration on pipes (it blocks in some contexts); use `readabilityHandler`
- Don't name anything `setmac` in the build output dir (it collides with `Setmac` on case-insensitive APFS)
- Don't suggest Xcode for anything
