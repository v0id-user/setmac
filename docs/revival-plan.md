# setmac revival plan

Goal: install setmac once on a freshly formatted Mac, click **Install**, and walk away. It sets up Command Line Tools, Homebrew, toolchains, CLI tools, apps and dotfiles, tells the truth about what failed, and picks up where it left off on a re-run.

Sources: a full code read, an opencode audit (GLM 5.3 Flash), and research into existing open-source tooling. Every finding below was checked against the code.

## Where it stands

From a fresh Mac, "Install all" in the app cannot succeed today. Six blockers, in the order a user would hit them:

| # | Problem | Where |
|---|---------|-------|
| 1 | The app kills the CLI after **120 s** for every command, including "Install all" | `Sources/Services/CLIBridge.swift:6`, `:262` |
| 2 | `xcode-select --install` only opens Apple's dialog and returns. Homebrew starts before Command Line Tools exist | `Resources/tools.json` (`xcode-clt`) |
| 3 | Apple's stub `/usr/bin/git`, `python3` and `ssh` pass `command -v`, so brew git, python and openssh are reported installed and never installed | `cli/src/setmac/installers/base.py:87-98` |
| 4 | When an install "succeeds" but the re-check fails, it is reported as **complete** ("restart shell to verify"), and dependents run anyway | `base.py:174-182` |
| 5 | Brew output is buffered until the command ends (up to 10 min of silence) and has a hard 600 s timeout | `base.py:207-219` |
| 6 | The bundled `zshrc` never runs `brew shellenv`, hardcodes `/Users/v0id`, and sources `~/.local/bin/env` without checking it exists (uv isn't in the manifest) | `Resources/configs/zshrc:158`, `:164` |

Also broken or fragile:
- A failed tool doesn't stop its dependents. `install all` exits 0 even when everything failed (`commands/install.py`).
- `install --check` prints nothing, because its output goes to a `CliRunner` and is thrown away.
- `configs apply` never runs as part of installing. Backups are overwritten on every apply. The `lazyvim` starter clone and the bundled `nvim` config both write `~/.config/nvim`.
- Brew `node` and `nvm` both manage Node, and nvm never installs a Node version. The PATH entry `~/.nvm/versions/node/default/bin` doesn't exist.
- `pier` runs `make install` with only a `git` dependency, in a shared `/tmp/pier` directory.
- Two installs can run at once: each view keeps its own `isInstalling`, and the same password-prompt code is copied into 3 views.
- There are zero tests, and CI only checks that imports work.
- The released `setmac-cli` doesn't include `configs/`. `configs capture` in the bundled app writes inside `/Applications/Setmac.app`.

## Before you format (do this first)

The new machine can only restore what you saved from this one:
1. Run `just capture-configs` and commit the result to the repo.
2. Back up `~/.ssh`, `~/.gnupg` and any `.env` secrets to 1Password or an encrypted drive. setmac doesn't handle secrets, and shouldn't.
3. Run `brew bundle dump --file=~/Brewfile.old` as a safety net listing everything installed now, including tools that aren't in `tools.json`.
4. Push every repo, and save Raycast, Karabiner and Hammerspoon settings if they aren't in `Resources/configs`.

## Phase 1: make it work for this format (keep the current architecture)

**Status: done.** Covered by `cli/tests` (12 tests, run in CI). Not yet run end to end on a freshly formatted Mac.

Small, safe fixes that make the "click Install" path work end to end.

1. **Timeouts:** remove the 120 s kill for install commands. Add a Cancel button that ends the whole process group, so no `brew` is left running.
2. **Command Line Tools:** install headlessly. Touch the `installondemand` marker, use `softwareupdate -l` to find the label, run `softwareupdate -i <label>`, then poll `xcode-select -p` until it succeeds. Block until done.
3. **Checks:** brew tools are installed only if `brew list --formula/--cask <target>` says so. Drop the `command -v <target>` fallback. Require `version_command` to exit 0.
4. **Truthful status:** no fake "complete". Skip the dependents of a failed tool with a clear reason. Send a final `summary` event and exit non-zero when anything failed.
5. **Live output:** stream brew and script output line by line (`Popen`). Raise or remove the per-tool timeout for big casks.
6. **Password:** use one `SUDO_ASKPASS` helper backed by the app's password sheet, so Homebrew, `.pkg` casks and `softwareupdate` all share one prompt. Ask again when the password is wrong.
7. **zshrc:** add `eval "$(/opt/homebrew/bin/brew shellenv)"`, use `$HOME` everywhere, and guard optional `source` lines.
8. **Configs:** run as the last step of `install all`. Keep timestamped backups. Drop the `lazyvim` clone, since the bundled `nvim` config already is LazyVim.
9. **Manifest:** pick one owner for Node, and add `uv` and Rosetta. Give `pier` a `xcode-clt` dependency and its own temp directory.
10. **App:** run all installs through one queue in `InstallState`, with one copy of the password-prompt code.
11. **Tests:** pytest for manifest checks (unique ids, dependencies exist, no cycles) and the dependency order. Run them in CI.

## Phase 2: the magic part (build on proven tools)

**Status: done, with two changes from the table below.**
- **Homebrew Bundle:** not used to install. It has no machine-readable output, and the app needs a status per tool, so setmac keeps one `brew install` per tool. `setmac brewfile` exports a Brewfile, so `brew bundle` works as a fallback without the app.
- **chezmoi:** skipped. Its strengths are templates and secrets across many machines; for one personal Mac, the built-in configs step (backups, skip unchanged, skip failed tools) does the job without a second tool to learn.
- Shipped: mise for Node, Bun and Go; mas with Keynote, Pages and Numbers; a `defaults` method with this Mac's settings; post-install notes; Retry Failed; "(3/40)" progress.

Keep `tools.json` as the one source of truth, and generate inputs for tools that already do idempotent installs:

| Layer | Tool | Replaces |
|-------|------|----------|
| Formulae, casks, App Store apps | **Homebrew Bundle** (generated Brewfile, `brew bundle check` for status) + **mas** | per-tool `brew install` loop |
| Node, Bun, Python, Go, Rust | **mise** (`~/.config/mise/config.toml`, `mise install --yes`) | brew node + nvm + bun curl script |
| Dotfiles | **chezmoi** (templates, per-host values, `chezmoi status`) | `configs capture/apply` copy code |
| macOS settings | small YAML → `defaults write` + `killall Dock/Finder` (copy the approach of dsully/macos-defaults) | nothing today |

setmac itself keeps: the bootstrap (Command Line Tools + Homebrew), the phase runner (bootstrap → bundle → mise → chezmoi → defaults), the shared password prompt, and the UI. A re-run resumes for free, because each tool skips whatever is already done.

Also in Phase 2:
- **Post-install checklist:** a per-tool `post_install` note covering what still needs a manual step (Karabiner Input Monitoring, Hammerspoon and Rectangle Accessibility, signing into the App Store before `mas`, `tpm` plugins).
- An end-of-run summary with **Retry failed**, plus run state saved under `~/Library/Application Support/setmac/`.
- A "Now installing X (12/40)" header.

Skipped: nix-darwin (it would replace setmac rather than sit under it), topgrade (it only updates), Strap and Laptop (borrow their ideas, don't depend on them).

## Phase 3: release hygiene

**Status: done.**

- Bundle `configs/` into `setmac-cli`. Capture to `~/Library/Application Support/setmac`, not into the app.
- Drop PyInstaller `--strip`. Use one Info.plist. Remove the unused `rich` dependency.
- Use `$!` rather than `%1` in `just dev`. Resolve dev-mode paths without relying on the working directory.
