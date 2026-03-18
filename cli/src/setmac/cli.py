"""Main CLI entry point."""

import click

from setmac import __version__
from setmac.commands.install import install_cmd
from setmac.commands.status import status_cmd
from setmac.commands.configs import configs_cmd


@click.group()
@click.version_option(__version__, prog_name="setmac")
def main():
    """setmac — macOS setup automator."""
    pass


main.add_command(install_cmd, "install")
main.add_command(status_cmd, "status")
main.add_command(configs_cmd, "configs")
