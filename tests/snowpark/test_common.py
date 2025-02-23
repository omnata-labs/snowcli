import pytest

from typing import Tuple

from tests.testing_utils.fixtures import (
    test_data,
    temp_dir,
    correct_requirements_snowflake_txt,
)
from snowcli.cli.snowpark.common import (
    _sql_to_python_return_type_mapper,
    _convert_resource_details_to_dict,
    _get_snowflake_packages_delta,
)


def test_get_snowflake_packages_delta(temp_dir, correct_requirements_snowflake_txt):
    anaconda_package = test_data.requirements[-1]

    result = _get_snowflake_packages_delta(anaconda_package)

    assert result == test_data.requirements[:-1]


def test_convert_resource_details_to_dict():
    resource_details = [
        ("packages", "{'name': 'my-awesome-package','version': '1.2.3'}"),
        ("handler", "handler_function"),
    ]

    assert _convert_resource_details_to_dict(resource_details) == {
        "packages": {"name": "my-awesome-package", "version": "1.2.3"},
        "handler": "handler_function",
    }


@pytest.mark.parametrize(
    "argument",
    [
        ("NUMBER(38,0)", "int"),
        ("TIMESTAMP_NTZ(9)", "datetime"),
        ("TIMESTAMP_TZ(9)", "datetime"),
        ("VARCHAR(16777216)", "string"),
        ("FLOAT", "float"),
        ("ARRAY", "array"),
    ],
)
def test_sql_to_python_return_type_mapper(argument: Tuple[str, str]):
    assert _sql_to_python_return_type_mapper(argument[0]) == argument[1]
