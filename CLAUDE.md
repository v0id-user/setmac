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
├── tools.json         # Tool manifest (~38 tools)
├── configs/           # Captured dotfiles
└── Assets.xcassets    # App icon

scripts/               # build-cli.sh, bundle.sh, generate-icon.sh, dmg.sh
```

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
{"type": "status|progress|log|error|complete", "tool": "tool-id", "message": "...", "status": "installed|not_installed", "version": "1.0"}
```
Thread-safe via `threading.Lock()` in `output.py`.

### CLIBridge.swift
- Dev mode: spawns `uv run --project cli setmac <args>`
- Bundle mode: runs embedded `Contents/MacOS/setmac-cli <args>`
- Uses `readabilityHandler` + `terminationHandler` (not async iteration)
- Sets rich PATH for subprocess tools (homebrew, cargo, bun, etc.)

### Logging
Uses `os.Logger` with subsystem `com.v0id.setmac`. Categories: CLIBridge, ManifestLoader, ContentView, InstallState, CategoryDetail, ConfigsView. View with:
```bash
log stream --predicate 'subsystem == "com.v0id.setmac"' --level debug
```

### No hardcoded tools
Everything is data-driven from `tools.json`. No tool names hardcoded in Swift or Python. Only `custom` install method needs dedicated installer code.

## Git Commit Convention

```
commit(type): message
```

Types: `feat`, `fix`, `refactor`, `chore`, `docs`, `style`, `test`, `ci`

## Development Rules

- No Xcode IDE — use CLI (`swift build`, `swift run`) and VS Code
- SPM only — no .xcodeproj
- macOS 26+ (Tahoe) with Liquid Glass UI
- `Window` not `WindowGroup` (single-window app)
- Python CLI uses `uv` for dependency management
