import typer

from snowcli.cli.common.decorators import global_options_with_connection
from snowcli.cli.common.flags import DEFAULT_CONTEXT_SETTINGS, identifier_argument
from snowcli.cli.snowpark.procedure_coverage.manager import (
    ProcedureCoverageManager,
    ReportOutputOptions,
)
from snowcli.output.decorators import with_output
from snowcli.output.types import MessageResult, SingleQueryResult, CommandResult

app: typer.Typer = typer.Typer(
    name="coverage",
    context_settings=DEFAULT_CONTEXT_SETTINGS,
    help="Generate coverage report for Snowflake procedure.",
)

OutputFormatOption = typer.Option(
    ReportOutputOptions.html,
    "--output-format",
    case_sensitive=False,
    help="The format to use when saving the coverage report locally",
)

StoreAsCommandOption = typer.Option(
    False,
    "--store-as-comment",
    help="In addition to the local report, saves the percentage coverage (a decimal value) as a comment on the stored procedure so that a coverage threshold can be easily checked for a number of procedures.",
)


@app.command(
    "report",
    help="Generate a code coverage report by downloading and combining reports from the stage",
)
@with_output
@global_options_with_connection
def procedure_coverage_report(
    identifier: str = identifier_argument(
        "procedure", "hello(number int, name string)"
    ),
    output_format: ReportOutputOptions = OutputFormatOption,
    store_as_comment: bool = StoreAsCommandOption,
    **options,
):
    message = ProcedureCoverageManager().report(
        identifier=identifier,
        output_format=output_format,
        store_as_comment=store_as_comment,
    )

    return MessageResult(message)


@app.command(
    "clear",
    help="Delete the code coverage reports from the stage, to start the measuring process over",
)
@with_output
@global_options_with_connection
def procedure_coverage_clear(
    identifier: str = identifier_argument(
        "procedure", "hello(number int, name string)"
    ),
    **options,
) -> CommandResult:
    cursor = ProcedureCoverageManager().clear(identifier=identifier)
    return SingleQueryResult(cursor)
