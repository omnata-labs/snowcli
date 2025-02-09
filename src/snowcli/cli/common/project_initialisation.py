from __future__ import annotations

import os
import shutil

from typer import Typer, Argument
from pathlib import Path

from snowcli.output.types import MessageResult, CommandResult
import importlib


def _create_project_template(template_name: str, project_directory: str):
    shutil.copytree(
        Path(importlib.util.find_spec("templates").origin).parent / template_name,  # type: ignore
        project_directory,
        dirs_exist_ok=True,
    )


def add_init_command(app: Typer, project_type: str, template: str):
    from snowcli.output.decorators import with_output
    from snowcli.cli.common.decorators import global_options

    @app.command()
    @with_output
    @global_options
    def init(
        project_name: str = Argument(
            f"example_{project_type.lower()}",
            help=f"Name of the {project_type} project you want to create.",
        ),
        **options,
    ) -> CommandResult:
        _create_project_template(template, project_directory=project_name)
        return MessageResult(f"Initialized the new project in {project_name}/")

    init.__doc__ = (
        f"Initializes this directory with a sample set "
        f"of files for creating a {project_type} project."
    )

    return init
