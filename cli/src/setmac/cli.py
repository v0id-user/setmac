"""Main CLI entry point."""

import click

from setmac import __version__
from setmac.commands.install import install_cmd
from setmac.commands.status import status_cmd
from setmac.commands.configs import configs_cmd
from setmac.commands.brewfile import brewfile_cmd
from setmac.commands.profile import profile_cmd


@click.group()
@click.version_option(__version__, prog_name="setmac")
@click.option(
    "--profile", "profile_spec", metavar="SPEC",
    help="Profile to use: a starter name or a profile directory. Defaults to SETMAC_PROFILE, "
    "then the one chosen with `profile use`, then minimal.",
)
@click.pass_context
def main(ctx: click.Context, profile_spec: str | None):
    """setmac — macOS setup automator."""
    ctx.obj = {"profile": profile_spec}


main.add_command(install_cmd, "install")
main.add_command(status_cmd, "status")
main.add_command(configs_cmd, "configs")
main.add_command(brewfile_cmd, "brewfile")
main.add_command(profile_cmd, "profile")
