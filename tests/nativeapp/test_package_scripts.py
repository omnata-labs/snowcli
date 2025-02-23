from pathlib import Path
import pytest
from unittest import mock
from textwrap import dedent

from snowcli.cli.nativeapp.manager import (
    NativeAppManager,
    MissingPackageScriptError,
    InvalidPackageScriptError,
)

from tests.project.fixtures import *
from tests.testing_utils.fixtures import *
from snowflake.connector import ProgrammingError

NATIVEAPP_MODULE = "snowcli.cli.nativeapp.manager"
NATIVEAPP_MANAGER_EXECUTE_QUERIES = (
    f"{NATIVEAPP_MODULE}.NativeAppManager._execute_queries"
)
NATIVEAPP_MANAGER_EXECUTE_QUERY = f"{NATIVEAPP_MODULE}.NativeAppManager._execute_query"
CLI_GET_CONNECTION = (
    "snowcli.cli.common.sql_execution.snow_cli_global_context_manager.get_connection"
)


@mock.patch(NATIVEAPP_MANAGER_EXECUTE_QUERIES)
@mock.patch(NATIVEAPP_MANAGER_EXECUTE_QUERY)
@mock.patch(CLI_GET_CONNECTION)
@pytest.mark.parametrize(
    "project_definition_files,expected_call",
    [
        ("napp_project_1", "use warehouse MockWarehouse"),
        ("napp_project_with_pkg_warehouse", "use warehouse myapp_pkg_warehouse"),
    ],
    indirect=["project_definition_files"],
)
def test_package_scripts(
    mock_conn,
    mock_execute_query,
    mock_execute_queries,
    project_definition_files,
    expected_call,
):
    mock_conn.return_value = MockConnectionCtx()
    working_dir: Path = project_definition_files[0].parent
    native_app_manager = NativeAppManager(str(working_dir))
    native_app_manager._apply_package_scripts()
    assert mock_execute_query.mock_calls == [
        mock.call(expected_call),
    ]
    assert mock_execute_queries.mock_calls == [
        mock.call(
            dedent(
                f"""\
                    -- package script (1/2)

                    create schema if not exists myapp_pkg_polly.my_shared_content;
                    grant usage on schema myapp_pkg_polly.my_shared_content
                      to share in application package myapp_pkg_polly;
                """
            )
        ),
        mock.call(
            dedent(
                f"""\
                    -- package script (2/2)

                    create or replace table myapp_pkg_polly.my_shared_content.shared_table (
                      col1 number,
                      col2 varchar
                    );
                    grant select on table myapp_pkg_polly.my_shared_content.shared_table
                      to share in application package myapp_pkg_polly;
                """
            )
        ),
    ]


@mock.patch(NATIVEAPP_MANAGER_EXECUTE_QUERIES)
@pytest.mark.parametrize("project_definition_files", ["napp_project_1"], indirect=True)
def test_missing_package_script(mock_execute, project_definition_files):
    working_dir: Path = project_definition_files[0].parent
    native_app_manager = NativeAppManager(str(working_dir))
    with pytest.raises(MissingPackageScriptError):
        (working_dir / "002-shared.sql").unlink()
        native_app_manager._apply_package_scripts()

    # even though the second script was the one missing, nothing should be executed
    assert mock_execute.mock_calls == []


@mock.patch(NATIVEAPP_MANAGER_EXECUTE_QUERIES)
@pytest.mark.parametrize("project_definition_files", ["napp_project_1"], indirect=True)
def test_invalid_package_script(mock_execute, project_definition_files):
    working_dir: Path = project_definition_files[0].parent
    native_app_manager = NativeAppManager(str(working_dir))
    with pytest.raises(InvalidPackageScriptError):
        second_file = working_dir / "002-shared.sql"
        second_file.unlink()
        second_file.write_text("select * from {{ package_name")
        native_app_manager._apply_package_scripts()

    # even though the second script was the one missing, nothing should be executed
    assert mock_execute.mock_calls == []


@mock.patch(NATIVEAPP_MANAGER_EXECUTE_QUERIES)
@pytest.mark.parametrize("project_definition_files", ["napp_project_1"], indirect=True)
def test_undefined_var_package_script(mock_execute, project_definition_files):
    working_dir: Path = project_definition_files[0].parent
    native_app_manager = NativeAppManager(str(working_dir))
    with pytest.raises(InvalidPackageScriptError):
        second_file = working_dir / "001-shared.sql"
        second_file.unlink()
        second_file.write_text("select * from {{ abc }}")
        native_app_manager._apply_package_scripts()

    assert mock_execute.mock_calls == []


@mock.patch(NATIVEAPP_MANAGER_EXECUTE_QUERIES)
@mock.patch(NATIVEAPP_MANAGER_EXECUTE_QUERY)
@mock.patch(CLI_GET_CONNECTION)
@pytest.mark.parametrize("project_definition_files", ["napp_project_1"], indirect=True)
def test_package_scripts_w_missing_warehouse_exception(
    mock_conn,
    mock_execute_query,
    mock_execute_queries,
    project_definition_files,
    mock_cursor,
):
    mock_conn.return_value = MockConnectionCtx()
    mock_execute_query.return_value = mock_cursor(["row"], [])
    mock_execute_queries.side_effect = ProgrammingError(
        msg="No active warehouse selected in the current session.", errno=606
    )

    working_dir: Path = project_definition_files[0].parent
    native_app_manager = NativeAppManager(str(working_dir))

    with pytest.raises(ProgrammingError) as err:
        native_app_manager._apply_package_scripts()

    assert "Please provide a warehouse for the active session role" in err.value.msg


@mock.patch(NATIVEAPP_MANAGER_EXECUTE_QUERY)
@mock.patch(CLI_GET_CONNECTION)
@pytest.mark.parametrize("project_definition_files", ["napp_project_1"], indirect=True)
def test_package_scripts_w_warehouse_access_exception(
    mock_conn,
    mock_execute_query,
    project_definition_files,
):
    mock_conn.return_value = MockConnectionCtx()
    mock_execute_query.side_effect = ProgrammingError(
        msg="Object does not exist, or operation cannot be performed.", errno=2043
    )

    working_dir: Path = project_definition_files[0].parent
    native_app_manager = NativeAppManager(str(working_dir))

    with pytest.raises(ProgrammingError) as err:
        native_app_manager._apply_package_scripts()

    assert "Please grant usage privilege on warehouse to this role." in err.value.msg
