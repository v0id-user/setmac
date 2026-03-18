"""Main CLI entry point."""

import click

from rig import __version__
from rig.commands.install import install_cmd
from rig.commands.status import status_cmd
from rig.commands.configs import configs_cmd


@click.group()
@click.version_option(__version__, prog_name="rig")
def main():
    """Rig — macOS setup automator."""
    pass


main.add_command(install_cmd, "install")
main.add_command(status_cmd, "status")
main.add_command(configs_cmd, "configs")
