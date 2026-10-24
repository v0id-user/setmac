"""Installers, keyed by the `install.method` value in tools.json."""

# Install methods the CLI knows how to run, and the install fields each one needs.
# The validator rejects any other method, so adding one here means adding its
# installer in base.py too.
METHODS: dict[str, tuple[str, ...]] = {
    "brew_formula": ("target",),
    "brew_cask": ("target",),
    "mise": ("target",),
    "mas": ("target",),
    "defaults": (),
    "script": (),
    "custom": (),
    "config": (),
}

# Methods whose installed check comes from the method itself, not check.command/path.
SELF_CHECKING = frozenset({"brew_formula", "brew_cask", "mise", "mas", "defaults"})
