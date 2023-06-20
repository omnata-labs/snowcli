from __future__ import annotations

from pathlib import Path
from typing import Optional

import click
import logging
import toml

from snowcli.snow_connector import SnowflakeConnector
from snowcli.connection_config import ConnectionConfigs

log = logging.getLogger(__name__)
snowflake_connection: SnowflakeConnector


class AppConfig:
    def __init__(self):
        self.path = self._find_app_toml()
        if self.path:
            self.config = toml.load(self.path)
        else:
            self.path = Path.cwd().joinpath("app.toml")
            self.config = {}

    def _find_app_toml(self):
        config_file_path_from_cli: Optional[str] = (
            click.get_current_context().find_root().params.get("configuration_file")
        )
        if config_file_path_from_cli:
            return Path(config_file_path_from_cli).absolute()

        # Find first app.toml by traversing parent dirs up to home dir
        p = Path.cwd()
        while not any(p.glob("app.toml")) and p != p.home():
            p = p.parent

        if p == p.home():
            return None
        else:
            return next(p.glob("app.toml"))

    def save(self):
        with open(self.path, "w") as f:
            toml.dump(self.config, f)


def connect_to_snowflake(connection: Optional[str] = None, **overrides):  # type: ignore
    global snowflake_connection
    cfg = AppConfig()
    connection_configs = ConnectionConfigs(
        snowsql_config_path=cfg.config.get("snowsql_config_path")
    )

    # If there's no user-provided connection then read
    # the one specified by configuration file
    connection_name = connection or cfg.config.get("snowsql_connection_name")
    connection_config = connection_configs.get_connection(connection_name)
    snowflake_connection = SnowflakeConnector(connection_config, overrides=overrides)


def is_auth():
    cfg = AppConfig()
    if "snowsql_config_path" not in cfg.config:
        log.info("You must login first with `snow login`")
        return False
    return True
