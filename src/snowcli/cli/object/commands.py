from __future__ import annotations

import typer

from snowcli.cli.common.decorators import global_options_with_connection
from snowcli.cli.common.flags import DEFAULT_CONTEXT_SETTINGS
from snowcli.cli.object.manager import ObjectManager
from snowcli.cli.constants import ObjectType
from snowcli.output.decorators import with_output
from snowcli.output.types import QueryResult

from snowcli.cli.object.stage.commands import app as stage_app

app = typer.Typer(
    name="object",
    context_settings=DEFAULT_CONTEXT_SETTINGS,
    help="Manages Snowflake objects like warehouses and stages",
)
app.add_typer(stage_app)  # type: ignore

NameArgument = typer.Argument(None, help="Name of the object")
ObjectArgument = typer.Argument(None, help="Type of object")
LikeOption = typer.Option(
    "%%",
    "--like",
    "-l",
    help='Regular expression for filtering the functions by name. For example, `list --like "my%"` lists all functions in the **dev** (default) environment that begin with “my”.',
)


@app.command()
@with_output
@global_options_with_connection
def show(
    object_type: ObjectType = ObjectArgument,
    like: str = LikeOption,
    **options,
):
    "Lists all available Snowflake objects of given type"
    return QueryResult(ObjectManager().show(object_type, like))


@app.command()
@with_output
@global_options_with_connection
def drop(
    object_type: ObjectType = ObjectArgument, object_name: str = NameArgument, **options
):
    "Drops Snowflake object of given name and type"
    return QueryResult(ObjectManager().drop(object_type, object_name))


@app.command()
@with_output
@global_options_with_connection
def describe(
    object_type: ObjectType = ObjectArgument, object_name: str = NameArgument, **options
):
    "Provides description of an object of given type"
    return QueryResult(ObjectManager().describe(object_type, object_name))
