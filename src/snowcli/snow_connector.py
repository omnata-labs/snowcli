from __future__ import annotations

import contextlib

import click
from click.exceptions import ClickException
import logging
import os

from pathlib import Path
from typing import Optional, Dict

import snowflake.connector
import snowcli.cli.common.snow_cli_global_context
from snowflake.connector import SnowflakeConnection
from snowflake.connector.errors import ForbiddenError, DatabaseError

from snowcli.config import cli_config, get_default_connection
from snowcli.exception import SnowflakeConnectionError, InvalidConnectionConfiguration

log = logging.getLogger(__name__)
TEMPLATES_PATH = Path(__file__).parent / "sql"
ENCRYPTED_PKCS8_PK_HEADER = b"-----BEGIN ENCRYPTED PRIVATE KEY-----"
UNENCRYPTED_PKCS8_PK_HEADER = b"-----BEGIN PRIVATE KEY-----"


def connect_to_snowflake(temporary_connection: bool = False, connection_name: Optional[str] = None, **overrides) -> SnowflakeConnection:  # type: ignore

    if not temporary_connection:
        connection_name = (
            connection_name if connection_name is not None else get_default_connection()
        )
        connection_parameters = cli_config.get_connection(connection_name)
    else:
        connection_parameters = {}

    if overrides:
        connection_parameters.update(
            {k: v for k, v in overrides.items() if v is not None}
        )

    connection_parameters = _update_connection_details_with_private_key(
        connection_parameters
    )

    try:
        # Whatever output is generated when creating connection,
        # we don't want it in our output. This is particularly important
        # for cases when external browser and json format are used.
        with contextlib.redirect_stdout(None):
            return snowflake.connector.connect(
                application=_find_command_path(),
                **connection_parameters,
            )
    except ForbiddenError as err:
        raise SnowflakeConnectionError(err)
    except DatabaseError as err:
        raise InvalidConnectionConfiguration(err.msg)


def _update_connection_details_with_private_key(connection_parameters: Dict):
    if "private_key_path" in connection_parameters:
        if connection_parameters.get("authenticator") == "SNOWFLAKE_JWT":
            private_key = _load_pem_to_der(connection_parameters["private_key_path"])
            connection_parameters["private_key"] = private_key
            del connection_parameters["private_key_path"]
        else:
            raise ClickException(
                "Private Key authentication requires authenticator set to SNOWFLAKE_JWT"
            )
    return connection_parameters


def _find_command_path():
    ctx = click.get_current_context(silent=True)
    if ctx:
        # Example: SNOWCLI.WAREHOUSE.STATUS
        return ".".join(["SNOWCLI", *ctx.command_path.split(" ")[1:]]).upper()
    return "SNOWCLI"


def _load_pem_to_der(private_key_path: str) -> bytes:
    """
    Given a private key file path (in PEM format), decode key data into DER
    format
    """
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.serialization import Encoding
    from cryptography.hazmat.primitives.serialization import NoEncryption
    from cryptography.hazmat.primitives.serialization import PrivateFormat
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    with open(private_key_path, "rb") as f:
        private_key_pem = f.read()

    private_key_passphrase = os.getenv("PRIVATE_KEY_PASSPHRASE", None)
    if (
        private_key_pem.startswith(ENCRYPTED_PKCS8_PK_HEADER)
        and private_key_passphrase is None
    ):
        raise ClickException(
            "Encrypted private key, you must provide the"
            "passphrase in the environment variable PRIVATE_KEY_PASSPHRASE"
        )

    if not private_key_pem.startswith(
        ENCRYPTED_PKCS8_PK_HEADER
    ) and not private_key_pem.startswith(UNENCRYPTED_PKCS8_PK_HEADER):
        raise ClickException(
            "Private key provided is not in PKCS#8 format. Please use correct format."
        )

    if private_key_pem.startswith(UNENCRYPTED_PKCS8_PK_HEADER):
        private_key_passphrase = None

    private_key = load_pem_private_key(
        private_key_pem,
        str.encode(private_key_passphrase)
        if private_key_passphrase is not None
        else private_key_passphrase,
        default_backend(),
    )

    return private_key.private_bytes(
        encoding=Encoding.DER,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )
