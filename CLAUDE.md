# setmac

macOS developer environment installer — automates reinstalling all dev tools, apps, and configs after a fresh format.

## Architecture

- **SwiftUI macOS app** (SPM, macOS 26+) — native sidebar UI, streams live status/logs
- **Python CLI backend** (`uv` + `click`) — does all actual installing via subprocess
- **Shared `Resources/tools.json` manifest** — single source of truth for both GUI and CLI
- SwiftUI spawns CLI via `Process`, reads JSON-line stdout, updates UI in real-time

## Project Structure

```
Sources/               # SwiftUI app (SPM target: "Setmac")
├── App/               # SetmacApp.swift, ContentView.swift
├── Models/            # InstallState.swift, ToolManifest.swift
├── Navigation/        # SidebarItem, SidebarView, DetailView
├── Views/             # OverviewView, CategoryDetailView, ToolCardView, etc.
└── Services/          # CLIBridge.swift, ManifestLoader.swift

cli/                   # Python CLI (uv project: "setmac-cli")
├── src/setmac/
│   ├── cli.py         # click entry point
│   ├── output.py      # JSON-line protocol (thread-safe)
│   ├── registry.py    # Loads tools.json, dependency graph
│   ├── commands/      # install, status, configs
│   └── installers/    # brew, script, custom dispatchers

Resources/
├── tools.json         # Tool manifest
├── configs/           # Captured dotfiles
├── icon.png           # App icon source (1024x1024, drawn by scripts/draw-icon.swift)
└── Assets.xcassets    # Accent color

scripts/               # build-cli.sh, bundle.sh, draw-icon.swift, generate-icon.sh, dmg.sh
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
{"type": "status|progress|log|error|complete|skipped|auth_required|config_status|summary", "tool": "tool-id", "message": "...", "status": "installed|not_installed", "version": "1.0"}
```
Thread-safe via `threading.Lock()` in `output.py`.

- **auth_required**: Sent at most once per run (it is cached after that): up front when a `requires_admin` tool still needs installing and `sudo -n true` fails, otherwise the first time an installer calls `sudo -A` (for example when a terminal's cached sudo ticket passed the up-front check, but installers run without that tty). The app shows the password sheet and writes the password to stdin. The CLI verifies it with `sudo -S -v`, re-asks on a wrong password, and caches it for the run. Installers reach it through `SUDO_ASKPASS` (`cli/src/setmac/askpass.py`), so scripts call `sudo -A`.
- **skipped**: `{"type": "skipped", "tool": "tool-id", "status": "needs_admin"}`, sent right after the `error` line for a `requires_admin` tool that was not attempted because the password was refused or cancelled. The `error` line carries the message; the tool is also in the summary's `failed` list.
- **summary**: Last line of an install run: `{"type": "summary", "message": "...", "failed": ["tool-id"]}`. The CLI exits 2 when anything failed, so the app treats exit 2 as a normal result, not a crash.
- **config_status**: Emitted by `configs list` for bundled/system/missing status.

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
- A tool whose dependency failed is skipped, not attempted. `install all` applies dotfiles last, skipping configs of failed tools.
- Tests: `cd cli && uv run pytest`.

### Logging
Uses `os.Logger` with subsystem `com.v0id.setmac`. Categories: CLIBridge, ManifestLoader, ContentView, InstallState, CategoryDetail, ConfigsView. View with:
```bash
log stream --predicate 'subsystem == "com.v0id.setmac"' --level debug
```

### No hardcoded tools
Everything is data-driven from `tools.json`. No tool names hardcoded in Swift or Python. Only `custom` install method needs dedicated installer code.

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
- **Signed release commits and tags**: every release job runs in the protected `release` environment (maintainer approval; branches `main`, `canary`, `beta`). `scripts/ci-signing-key.sh` imports a signing-only subkey of the maintainer's GPG key from the environment secrets `RELEASE_GPG_PRIVATE_KEY` and `RELEASE_GPG_PASSPHRASE` and checks it signs before semantic-release runs. semantic-release commits as `commit_author` in `pyproject.toml` (also the committer), whose email must be verified on the key owner's GitHub account. The `main` ruleset lets GitHub Actions bypass the PR rule so the release commit can be pushed; the commit itself must still be signed.
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
