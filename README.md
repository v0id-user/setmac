# Rig

Idempotent macOS setup automator. Reinstall all your dev tools, apps, and configs after a fresh format — one click or one command.

## What it does

- Installs ~40 developer tools in dependency order (Xcode CLT -> Homebrew -> everything else)
- Checks what's already installed and skips it (idempotent)
- Captures and restores dotfiles/configs (zshrc, tmux, neovim, ghostty, etc.)
- Native SwiftUI app with Liquid Glass UI on macOS Tahoe
- Python CLI backend that does the actual work

## Architecture

```
rig/
├── Sources/          # SwiftUI macOS app
├── cli/              # Python CLI (uv + click)
├── Resources/
│   ├── tools.json    # Single source of truth — all tools defined here
│   └── configs/      # Captured dotfiles
├── scripts/          # Build, bundle, DMG scripts
├── Makefile          # All commands
└── Package.swift     # SPM config
```

Both the GUI and CLI read from the same `tools.json` manifest. The SwiftUI app spawns the CLI via `Process`, reads structured JSON output, and updates the UI in real-time.

## Quick start

```bash
# Run the GUI
make dev

# Or use the CLI directly
cd cli && uv sync
uv run rig status          # Check what's installed
uv run rig install all     # Install everything
uv run rig configs capture # Save current dotfiles
uv run rig configs apply   # Restore dotfiles on fresh Mac
```

## Requirements

- macOS 26 (Tahoe) — for SwiftUI Liquid Glass
- Xcode (for Swift SDK, not the IDE)
- [uv](https://docs.astral.sh/uv/) — Python package manager
- Python 3.12+

## tools.json

Every tool is defined in `Resources/tools.json` with:

- **id** — unique identifier
- **category** — essentials, cli-tools, applications, languages, standalone
- **check** — how to verify it's installed (command, path, or version check)
- **install** — how to install it (brew formula, brew cask, script, or custom)
- **depends_on** — tools that must be installed first
- **configs** — associated dotfiles to capture/restore

The manifest is designed to be extensible. Future plan: host your own `tools.json` and share setups.

## Makefile targets

```
make dev             # Build and run in debug mode
make build           # Build debug binary
make status          # Check install status of all tools
make capture-configs # Capture current system configs
make apply-configs   # Apply bundled configs to system
make bundle          # Create .app bundle with embedded CLI
make dmg             # Create DMG for distribution
make help            # Show all targets
```

## Tools included

**Essentials**: Xcode CLT, Homebrew
**CLI**: git, gh, neovim, tmux, fzf, bat, eza, fd, ripgrep, starship, lazygit, btop, fastfetch, yazi, tree-sitter, gnupg, openssh, imagemagick
**Apps**: Cursor, Claude Code, Ghostty, Raycast, Hammerspoon, Rectangle, Karabiner Elements
**Languages**: Go, Node, Python, LuaJIT, Bun, NVM
**Standalone**: Oh My Zsh, TPM, LazyVim, Pier

## License

MIT
