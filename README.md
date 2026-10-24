# setmac

Idempotent macOS setup automator. Reinstall all your dev tools, apps, and configs after a fresh format — one click or one command.

## What it does

- Installs every tool in the manifest in dependency order: Command Line Tools (headless, no dialog), Rosetta, Homebrew, then everything else
- Language runtimes (Node, Bun, Go) through [mise](https://mise.jdx.dev), App Store apps through [mas](https://github.com/mas-cli/mas)
- Applies your macOS settings (Dock, Finder, Dark mode, trackpad) from `tools.json`, writing only what differs
- Checks what's already installed and skips it, so a re-run resumes where the last one stopped
- A failed tool skips the tools that depend on it; each run ends with a summary and a **Retry Failed** button
- Restores dotfiles last, with timestamped backups in `~/.config/setmac-backup/`
- Asks for the admin password once per run, in a native sheet, and shares it with every installer
- Lists the manual steps left after installing (permissions to grant, App Store sign-in)
- Native SwiftUI app with Liquid Glass UI on macOS Tahoe; Python CLI backend does the work

## Architecture

```
setmac/
├── Sources/          # SwiftUI macOS app
├── cli/              # Python CLI (uv + click)
├── Resources/
│   ├── tools.json    # Single source of truth — all tools defined here
│   └── configs/      # Captured dotfiles
├── scripts/          # Build, bundle, DMG scripts
├── justfile          # All commands
└── Package.swift     # SPM config
```

Both the GUI and CLI read from the same `tools.json` manifest. The SwiftUI app spawns the CLI via `Process`, reads structured JSON output, and updates the UI in real-time.

## Quick start

```bash
# Run the GUI
just dev

# Or use the CLI directly
cd cli && uv sync
uv run setmac status          # Check what's installed
uv run setmac install all     # Install everything
uv run setmac configs capture # Save current dotfiles
uv run setmac configs apply   # Restore dotfiles on fresh Mac
uv run setmac brewfile        # Print a Brewfile, for plain `brew bundle`
```

## Requirements

- macOS 26 (Tahoe) — for SwiftUI Liquid Glass
- Xcode (for Swift SDK, not the IDE)
- [uv](https://docs.astral.sh/uv/) — Python package manager
- Python 3.12+

## Admin password flow

Installers run without a terminal, so `sudo` uses the `SUDO_ASKPASS` helper the CLI sets up for each run:

1. The first time any installer needs admin, the CLI emits `auth_required`
2. The app shows a native password sheet (the terminal prompts instead when run by hand)
3. The CLI checks the password with `sudo -S -v`, asks again if it is wrong, and keeps it in memory for the rest of the run
4. Every later `sudo` (Homebrew, `.pkg` casks, `softwareupdate`, `mas`) gets it from the helper over a private unix socket; it is never written to disk

`"requires_admin": true` in tools.json marks tools that will ask.

## tools.json

Every tool is defined in `Resources/tools.json` with:

- **id** — unique identifier
- **category** — essentials, cli-tools, applications, languages, standalone, configs, system
- **check** — how to verify it's installed (command, path, or version check). Brew, mise, mas and defaults tools are checked by their own method.
- **install** — `brew_formula`, `brew_cask`, `mise` (`node@lts`), `mas` (App Store id), `defaults`, `script`, or `custom`
- **defaults** / **restart** — for the `defaults` method: `{domain, key, type, value}` settings and apps to restart after a change
- **post_install** — a manual step to show after install
- **depends_on** — tools that must be installed first
- **configs** — associated dotfiles to capture/restore

The manifest is designed to be extensible. Future plan: host your own `tools.json` and share setups.

## Commands (just)

```
just dev             # Build and run in debug mode
just build           # Build debug binary
just status          # Check install status of all tools
just capture-configs # Capture current system configs
just apply-configs   # Apply bundled configs to system
just bundle          # Create .app bundle with embedded CLI
just dmg             # Create DMG for distribution
just                 # List all recipes
```

## Releases

Releases are automated with [python-semantic-release](https://python-semantic-release.readthedocs.io/).

- **Canary**: Push to `canary` to publish `vX.Y.Z-canary.N`
- **Beta**: Push to `beta` to publish `vX.Y.Z-beta.N`
- **Stable**: Run the `Release Stable` workflow manually from `main`
- **Version bumps**: Use Conventional Commits (`feat:`, `fix:`, etc.). semantic-release owns the version number.

### Signing and notarization

Release builds now do the following:

- ad-hoc sign the standalone `setmac-cli`
- ad-hoc sign `Setmac.app` and the DMG by default
- automatically switch to Developer ID signing when these GitHub secrets are configured:
  - `APPLE_SIGNING_IDENTITY`
  - `APPLE_CERTIFICATE_P12_BASE64`
  - `APPLE_CERTIFICATE_PASSWORD`
  - `APPLE_ID`
  - `APPLE_APP_SPECIFIC_PASSWORD`
  - `APPLE_TEAM_ID`
- automatically notarize and staple the DMG when the Apple secrets are present

Ad-hoc signing makes the bundle structurally valid, but it does **not** satisfy Gatekeeper on a downloaded build. Until the Apple signing secrets are configured, users should expect to use the workaround below.

### Gatekeeper workaround

If you open a non-notarized build and macOS reports the app as damaged or blocked, move it to `/Applications` and run:

```bash
xattr -cr /Applications/Setmac.app
```

You can also Control-click the app and choose `Open`. This is only a temporary workaround for older unsigned releases; the proper fix is signed and notarized builds.

## Maintainer docs

- Release and hotfix playbook: `docs/ai-maintainer-playbook.md`
- Persistent Cursor rule: `.cursor/rules/release-policy.mdc`
- Project skill for AI release work: `.cursor/skills/setmac-release-ops/SKILL.md`
- Agent guidance: `CLAUDE.md`

## Tools included

**Essentials**: Xcode CLT, Homebrew
**CLI**: git, gh, neovim, tmux, fzf, bat, eza, fd, ripgrep, starship, lazygit, btop, fastfetch, yazi, tree-sitter, gnupg, openssh, imagemagick
**Apps**: Cursor, Claude Code, Ghostty, Raycast, Hammerspoon, Rectangle, Karabiner Elements
**Languages**: Go, Node, Python, LuaJIT, Bun, NVM
**Standalone**: Oh My Zsh, TPM, LazyVim, Pier

## License

MIT
