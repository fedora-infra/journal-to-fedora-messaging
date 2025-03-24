# SPDX-FileCopyrightText: Contributors to the Fedora Project
#
# SPDX-License-Identifier: GPL-3.0-or-later


import pytest


@pytest.fixture
def config():
    return {
        "journalctl_command": ["journalctl"],
        "logs": [
            {
                "schema": "journal.ipa.user_add.v1",
                "filters": {
                    "IPA_API_COMMAND": "user_add",
                },
            }
        ],
    }
