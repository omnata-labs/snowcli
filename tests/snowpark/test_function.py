import contextlib
import os
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from textwrap import dedent
from unittest import mock

from tests.testing_utils.fixtures import *


@mock.patch("snowflake.connector.connect")
@mock.patch("snowcli.cli.snowpark.function.commands.snowpark_package")
@mock.patch("snowcli.cli.snowpark.function.commands.TemporaryDirectory")
def test_create_function(
    mock_tmp_dir, mock_package_create, mock_connector, runner, mock_ctx
):
    tmp_dir = TemporaryDirectory()
    mock_tmp_dir.return_value = tmp_dir

    ctx = mock_ctx()
    mock_connector.return_value = ctx
    with NamedTemporaryFile(suffix=".py") as fh:
        result = runner.invoke(
            [
                "snowpark",
                "function",
                "create",
                "--name",
                "functionName",
                "--file",
                fh.name,
                "--handler",
                "main.py:app",
                "--return-type",
                "table(variant)",
                "--input-parameters",
                "(a string, b number)",
                "--overwrite",
            ]
        )

    assert result.exit_code == 0, result.output
    assert ctx.get_queries() == [
        "create stage if not exists deployments comment='deployments managed by snowcli'",
        f"put file://{tmp_dir.name}/{Path(fh.name).name} @deployments/functionnamea_string_b_number"
        f" auto_compress=false parallel=4 overwrite=True",
        dedent(
            """\
            create or replace function functionName(a string, b number)
            returns table(variant)
            language python
            runtime_version=3.8
            imports=('@deployments/functionnamea_string_b_number/app.zip')
            handler='main.py:app'
            packages=()
            """
        ),
    ]
    mock_package_create.assert_called_once_with("ask", True, "ask")


@mock.patch("snowflake.connector.connect")
@mock.patch("snowcli.cli.snowpark.function.commands.snowpark_package")
@mock.patch("snowcli.cli.snowpark_shared.tempfile.TemporaryDirectory")
def test_update_function(
    mock_tmp_dir,
    mock_package_create,
    mock_connector,
    runner,
    mock_ctx,
    snapshot,
    temp_dir,
):
    tmp_dir = TemporaryDirectory()
    mock_tmp_dir.return_value = tmp_dir

    ctx = mock_ctx()
    mock_connector.return_value = ctx
    (Path(temp_dir) / "requirements.snowflake.txt").write_text("foo=1.2.3\nbar>=3.0.0")

    app = Path(temp_dir) / "app.py"
    app.touch()

    result = runner.invoke_with_config(
        [
            "snowpark",
            "function",
            "update",
            "--name",
            "functionName",
            "--file",
            str(app),
            "--handler",
            "main.py:app",
            "--return-type",
            "table(variant)",
            "--input-parameters",
            "(a string, b number)",
            "--replace-always",
        ]
    )

    assert result.exit_code == 0, result.output
    assert ctx.get_queries() == [
        dedent(
            f"""\
use role MockRole;
use warehouse MockWarehouse;
use database MockDatabase;
use schema MockSchema;
desc FUNCTION functionName(string, number);"""
        ),
        dedent(
            f"""\
use role MockRole;
use warehouse MockWarehouse;
use database MockDatabase;
use schema MockSchema;


create stage if not exists MockDatabase.MockSchema.deployments comment='deployments managed by snowcli';


put file://{tmp_dir.name}/{app.name} @MockDatabase.MockSchema.deployments/functionnamea_string_b_number auto_compress=false parallel=4 overwrite=True;"""
        ),
        dedent(
            f"""\
use role MockRole;
use warehouse MockWarehouse;
use database MockDatabase;
use schema MockSchema;
CREATE OR REPLACE  FUNCTION functionName(a string, b number)
         RETURNS table(variant)
         LANGUAGE PYTHON
         RUNTIME_VERSION=3.8
         IMPORTS=('@MockDatabase.MockSchema.deployments/functionnamea_string_b_number/app.zip')
         HANDLER='main.py:app'
         PACKAGES=('foo=1.2.3','bar>=3.0.0');
describe function functionName(string, number);"""
        ),
    ]
    mock_package_create.assert_called_once_with("ask", True, "ask")


@mock.patch("snowflake.connector.connect")
def test_execute_function(mock_connector, runner, mock_ctx):
    ctx = mock_ctx()
    mock_connector.return_value = ctx
    result = runner.invoke(
        [
            "snowpark",
            "function",
            "execute",
            "--function",
            "functionName(42, 'string')",
        ]
    )

    assert result.exit_code == 0, result.output
    assert ctx.get_query() == "select functionName(42, 'string')"


@mock.patch("snowflake.connector.connect")
def test_describe_function_from_signature(mock_connector, runner, mock_ctx):
    ctx = mock_ctx()
    mock_connector.return_value = ctx
    result = runner.invoke(
        [
            "snowpark",
            "function",
            "describe",
            "--function",
            "functionName(int, string, variant)",
        ]
    )

    assert result.exit_code == 0, result.output
    assert ctx.get_query() == "describe function functionName(int, string, variant)"


@mock.patch("snowflake.connector.connect")
def test_describe_function_from_name(mock_connector, runner, mock_ctx):
    ctx = mock_ctx()
    mock_connector.return_value = ctx
    result = runner.invoke(
        [
            "snowpark",
            "function",
            "describe",
            "--name",
            "functionName",
            "--input-parameters",
            "(int, string, variant)",
        ]
    )

    assert result.exit_code == 0, result.output
    assert ctx.get_query() == "describe function functionName(int, string, variant)"


@mock.patch("snowflake.connector.connect")
def test_list_function(mock_connector, runner, mock_ctx):
    ctx = mock_ctx()
    mock_connector.return_value = ctx
    result = runner.invoke(
        [
            "snowpark",
            "function",
            "list",
            "--like",
            "foo_bar%",
        ]
    )

    assert result.exit_code == 0, result.output
    assert ctx.get_query() == "show user functions like 'foo_bar%'"


@mock.patch("snowflake.connector.connect")
def test_drop_function_from_signature(mock_connector, runner, mock_ctx):
    ctx = mock_ctx()
    mock_connector.return_value = ctx
    result = runner.invoke(
        [
            "snowpark",
            "function",
            "drop",
            "--function",
            "functionName(int, string, variant)",
        ]
    )

    assert result.exit_code == 0, result.output
    assert ctx.get_query() == "drop function functionName(int, string, variant)"


@mock.patch("snowflake.connector.connect")
def test_drop_function_from_name(mock_connector, runner, mock_ctx):
    ctx = mock_ctx()
    mock_connector.return_value = ctx
    result = runner.invoke(
        [
            "snowpark",
            "function",
            "drop",
            "--name",
            "functionName",
            "--input-parameters",
            "(int, string, variant)",
        ]
    )

    assert result.exit_code == 0, result.output
    assert ctx.get_query() == "drop function functionName(int, string, variant)"