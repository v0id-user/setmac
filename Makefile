APP_NAME     := Setmac
BUNDLE_ID    := com.v0id.setmac
VERSION      := 1.0.0
BUILD_DIR    := .build
RELEASE_DIR  := dist
APP_BUNDLE   := $(RELEASE_DIR)/$(APP_NAME).app
CLI_DIR      := cli

# ─── Development ──────────────────────────────────────────────

.PHONY: dev
dev: ## Build and run in debug mode
	swift run

.PHONY: build
build: ## Build debug binary
	swift build

.PHONY: clean
clean: ## Clean all build artifacts
	swift package clean
	rm -rf $(RELEASE_DIR)
	rm -rf $(CLI_DIR)/dist $(CLI_DIR)/build

# ─── Release ──────────────────────────────────────────────────

.PHONY: release
release: ## Build optimized release binary
	swift build -c release

.PHONY: bundle
bundle: release cli-build ## Create .app bundle with embedded CLI
	@bash scripts/bundle.sh

.PHONY: dmg
dmg: bundle ## Create DMG for distribution
	@bash scripts/dmg.sh

# ─── CLI ──────────────────────────────────────────────────────

.PHONY: cli-setup
cli-setup: ## Set up Python CLI dev environment
	cd $(CLI_DIR) && uv sync

.PHONY: cli-dev
cli-dev: ## Run CLI in dev mode
	cd $(CLI_DIR) && uv run setmac --help

.PHONY: cli-build
cli-build: ## Build standalone CLI binary with PyInstaller
	@bash scripts/build-cli.sh

# ─── Status & Configs ─────────────────────────────────────

.PHONY: status
status: ## Check install status of all tools
	cd $(CLI_DIR) && uv run setmac status

.PHONY: capture-configs
capture-configs: ## Capture current system configs into bundle
	cd $(CLI_DIR) && uv run setmac configs capture

.PHONY: apply-configs
apply-configs: ## Apply bundled configs to system
	cd $(CLI_DIR) && uv run setmac configs apply

# ─── Icon ─────────────────────────────────────────────────────

.PHONY: icon
icon: ## Generate .icns from icon.png (1024x1024)
	@bash scripts/generate-icon.sh

# ─── Utilities ────────────────────────────────────────────────

.PHONY: format
format: ## Format Swift source files
	swift format --in-place --recursive Sources/

.PHONY: loc
loc: ## Count lines of code
	@echo "Swift:"; find Sources -name '*.swift' | xargs wc -l | tail -1
	@echo "Python:"; find cli/src -name '*.py' | xargs wc -l | tail -1

.PHONY: tree
tree: ## Show project structure
	@tree -I '.build|.venv|__pycache__|dist|build|.git' --dirsfirst

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
