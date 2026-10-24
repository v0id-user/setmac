# Contributing to setmac

Thanks for helping. setmac is a SwiftUI app plus a Python CLI that both read `Resources/tools.json`. `CLAUDE.md` describes the architecture and conventions in detail; this file covers how to send a change.

## Setup

```bash
brew install just uv lefthook gitleaks
lefthook install          # gitleaks on commit, CLI tests on push
cd cli && uv sync
```

There is no Xcode project. Build with SwiftPM and the `just` recipes:

```bash
just build                # swift build
just dev                  # build and run with live logs
just bundle               # dist/Setmac.app with the embedded CLI
cd cli && uv run pytest   # CLI tests
```

## Commits

- Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `style:`, `test:`, `ci:`. Use `feat!:` or `fix!:` for breaking changes. Release notes and version numbers come from these messages.
- One logical change per commit.
- Sign your commits (`git config commit.gpgsign true` with a GPG or SSH signing key added to your GitHub account). `main` only accepts signed commits.
- Never edit version numbers by hand. semantic-release owns `pyproject.toml`'s `[tool.setmac].version`, `cli/src/setmac/__init__.py` and `CHANGELOG.md`.

## Pull requests

- Branch from `main` and open the pull request against `main`. Do not target `canary` or `beta`: pushes there publish prereleases.
- Keep pull requests small and focused. Say what changed, why, and how you tested it.
- CI must pass: Swift build, CLI tests, and gitleaks.
- Do not add tool names to Swift or Python code. Everything is data driven from `tools.json`; only the `custom` install method has dedicated code.

## Adding a tool

Add an entry to `Resources/tools.json` with an `id`, `name`, `category`, an `install` block using one of the supported methods (`brew_formula`, `brew_cask`, `mise`, `mas`, `defaults`, `script`, `custom`, `config`), and a `check` block. Set `requires_admin` when the installer needs `sudo`, and `depends_on` for tools that must come first. Run `just status` to see that it is detected.

Tools in the public catalog should be useful to most developers. Personal apps and scripts belong in your own profile, not here.

## Starter profiles

Starter profiles are neutral presets (for example `minimal` or `web`) that pick tools from the catalog. A starter must not contain dotfiles, personal data, or tools that are not already in the catalog. Open an issue first to discuss a new starter.

## Never commit

- Secrets, tokens, keys, or `.env` files.
- Your own dotfiles, home paths (`/Users/<name>`), hostnames, or email addresses.
- Build output (`dist/`, `.build/`, generated `.icns` files).

## Code of conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md). Report security issues as described in [SECURITY.md](SECURITY.md).
