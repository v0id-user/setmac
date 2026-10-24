# setmac

Idempotent macOS setup automator. Reinstall all your dev tools, apps, and configs after a fresh format — one click or one command.

## What it does

- Installs the tools your **profile** picks from a public catalog, in dependency order: Command Line Tools (headless, no dialog), Homebrew, then everything else
- Starter profiles (`minimal`, `web`, `backend`, `mobile`) or your own profile directory with your own tools and dotfiles
- Language runtimes (Node, Bun, Go) through [mise](https://mise.jdx.dev), App Store apps through [mas](https://github.com/mas-cli/mas)
- Applies macOS settings (Dock, Finder, Dark mode, trackpad) only when your profile turns them on, writing only what differs
- Checks what's already installed and skips it, so a re-run resumes where the last one stopped
- A failed tool skips the tools that depend on it; each run ends with a summary and a **Retry Failed** button
- Restores your profile's dotfiles last, with timestamped backups in `~/.config/setmac-backup/` (the public catalog ships none)
- Asks for the admin password once per run, in a native sheet, and shares it with every installer
- Lists the manual steps left after installing (permissions to grant, App Store sign-in)
- Native SwiftUI app with Liquid Glass UI on macOS Tahoe; Python CLI backend does the work

## Architecture

```
setmac/
├── Sources/          # SwiftUI macOS app
├── cli/              # Python CLI (uv + click)
├── Resources/
│   ├── tools.json    # The public tool catalog
│   ├── profiles/     # Starter profiles: minimal, web, backend, mobile
│   └── configs/      # Old bundled dotfiles (moving to private profiles)
├── scripts/          # Build, bundle, DMG scripts
├── justfile          # All commands
└── Package.swift     # SPM config
```

The CLI merges the active profile with the catalog; the app asks the CLI for that list (`setmac-cli profile show --json`) and shows exactly the tools the CLI installs. The SwiftUI app spawns the CLI via `Process`, reads structured JSON output, and updates the UI in real-time.

## Quick start

```bash
# Run the GUI
just dev

# Or use the CLI directly
cd cli && uv sync
uv run setmac profile list    # Starter profiles and the active one
uv run setmac profile use web # Choose a profile (or a path to your own)
uv run setmac status          # Check what's installed
uv run setmac install all --dry-run  # See what would be installed
uv run setmac install all     # Install the profile's tools
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

## Profiles

A profile is a folder with a `profile.json`. setmac uses, in order: `--profile <spec>`, the `SETMAC_PROFILE` environment variable, the profile chosen with `setmac profile use`, then `minimal`. A spec is a starter name, an absolute or `~` path, or a git URL with an optional `#branch`, `#tag` or `#sha` (for example `git@github.com:you/setmac-profile.git`).

```json
{
  "schema": 1,
  "name": "me",
  "extends": "web",
  "tools": { "add": ["neovim", "tmux"], "remove": ["bun"] },
  "custom_tools": [ { "id": "my-app", "name": "My App", "check": { "path": "/Applications/My App.app" }, "install": { "method": "brew_cask", "target": "my-app" } } ],
  "overrides": { "git": { "post_install": "Run gh auth login" } },
  "configs_dir": "configs",
  "macos_defaults": { "enabled": false }
}
```

- `extends`: a starter name, or a path inside the profile folder (`./base`). At most 3 levels.
- `tools.add` / `tools.remove`: catalog tool ids. Dependencies come along; removing one that another tool needs is an error.
- `custom_tools`: your own tools, in the catalog's format. They may not reuse a catalog id; use `overrides` to change a catalog tool.
- `configs` on your tools: `source` is the file on the Mac (`~/...`), `target` is its copy under `configs_dir`. `~/.ssh`, `~/.gnupg`, `~/.aws`, `~/Library/LaunchAgents` and `~/.config/gh` are refused unless listed in `sensitive_ok`.
- `setmac profile validate <spec>` lists every problem; `setmac profile show <spec>` lists the tools.

### Review and trust

A profile you didn't get from setmac can run any shell command, so setmac runs nothing from it until you have reviewed it:

```bash
setmac profile review <spec>   # every install command, check, dotfile, admin tool and note, verbatim
setmac profile trust <spec>    # trust exactly this content (asks; or pass --hash <content hash>)
```

Trust covers the exact files reviewed: editing a local profile, or a new commit in a git profile, needs a new review. A git profile is cloned with your own git credentials and pinned to one commit on first use; `setmac profile update <spec>` shows what changed and moves the pin only after you confirm. Starters are always trusted.

## tools.json

The public catalog. Every tool is defined in `Resources/tools.json` with:

- **id** — unique identifier
- **category** — essentials, cli-tools, applications, languages, standalone, configs, system
- **check** — how to verify it's installed (command, path, or version check). Brew, mise, mas and defaults tools are checked by their own method.
- **install** — `brew_formula`, `brew_cask`, `mise` (`node@lts`), `mas` (App Store id), `defaults`, `script`, or `custom`
- **defaults** / **restart** — for the `defaults` method: `{domain, key, type, value}` settings and apps to restart after a change
- **post_install** — a manual step to show after install
- **depends_on** — tools that must be installed first
- **configs** — dotfiles to capture/restore (profiles only; the catalog ships none)

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

The catalog (profiles pick from it):

**Essentials**: Xcode CLT, Rosetta, Homebrew, mise, mas
**CLI**: git, gh, neovim, tmux, just, fzf, bat, eza, fd, jq, ripgrep, starship, lazygit, btop, fastfetch, yazi, tree-sitter, gnupg, openssh, imagemagick
**Apps**: Cursor, Claude Code, Ghostty, Raycast, Rectangle, Keynote, Pages, Numbers
**Languages**: Go, Node, Python, uv, LuaJIT, Bun
**Standalone**: Oh My Zsh, TPM
**macOS settings**: Dock, Finder, Dark mode and trackpad defaults (off unless a profile enables them)

## License

MIT
