# SPDX-FileCopyrightText: Contributors to the Fedora Project
#
# SPDX-License-Identifier: GPL-3.0-or-later

from functools import cache
from pathlib import Path

from pydantic_settings import BaseSettings


DEFAULT_CONFIG_FILE = _config_file = (
    "/etc/journal-to-fedora-messaging/journal-to-fedora-messaging.cfg"
)
TOP_DIR = Path(__file__).parent


class Config(BaseSettings):
    pass


@cache
def get_config() -> Config:
    return Config(_env_file=_config_file)


def set_config_file(path: str) -> None:
    global _config_file
    _config_file = path
    get_config.cache_clear()
