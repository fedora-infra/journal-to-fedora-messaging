# SPDX-FileCopyrightText: Contributors to the Fedora Project
#
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner

from journal_to_fedora_messaging import cli


@pytest.fixture
def config_file():
    return Path(__file__).parent.parent.joinpath("fedora-messaging.toml.example")


@pytest.fixture
def disable_reactor_run():
    with mock.patch("journal_to_fedora_messaging.cli.reactor.run") as run:
        yield run


@pytest.fixture(autouse=True)
def disable_log_mangling():
    with mock.patch("journal_to_fedora_messaging.cli.fm_config.setup_logging"):
        yield


@pytest.fixture
def mocked_sender():
    sender = mock.Mock()
    with mock.patch("journal_to_fedora_messaging.cli.MessageSender") as sender_class:
        sender_class.return_value = sender
        yield sender_class


@pytest.fixture
def mocked_reader():
    reader = mock.Mock()
    with mock.patch("journal_to_fedora_messaging.cli.JournalReader") as reader_class:
        reader_class.return_value = reader
        yield reader_class


def test_cli(mocked_sender, mocked_reader, disable_reactor_run):
    runner = CliRunner()
    result = runner.invoke(cli.main)
    mocked_sender.assert_called()
    mocked_sender.return_value.validate_config.assert_called_once()
    mocked_sender.return_value.registerProducer.assert_called_once_with(
        mocked_reader.return_value, True
    )
    mocked_reader.return_value.resumeProducing.assert_called_once()
    print(result.output)
    assert result.exit_code == 0


def test_cli_absent_config():
    runner = CliRunner()
    result = runner.invoke(cli.main, ["-c", "/does/not/exist"])
    assert result.exit_code == 2
    assert result.output.endswith("Error: Invalid value: /does/not/exist is not a file\n")


def test_cli_bad_config():
    runner = CliRunner()
    result = runner.invoke(cli.main, ["-c", __file__])
    assert result.exit_code == 2
    assert "Error: Invalid value: Configuration error: Failed to parse" in result.output


def test_cli_config_file(config_file, mocked_sender, mocked_reader, disable_reactor_run):
    runner = CliRunner()
    with mock.patch("journal_to_fedora_messaging.cli.JournalToFedoraMessagingService") as service:
        result = runner.invoke(cli.main, ["-c", config_file.as_posix()])
    expected_conf = {
        "journalctl_command": ["journalctl"],
        "logs": [
            {
                "schema": "journal_to_fedora_messaging_messages.foo:FooV1",
                "filters": {"SYSLOG_IDENTIFIER": "foo"},
            },
            {
                "schema": "journal_to_fedora_messaging_messages.bar:BarV1",
                "filters": {"SYSLOG_IDENTIFIER": "bar"},
            },
        ],
    }
    service.assert_called_once_with(expected_conf)
    assert result.exit_code == 0


def test_cli_stop_service(mocked_sender, mocked_reader):
    service = cli.JournalToFedoraMessagingService(None)
    service.stopService()
    mocked_reader.return_value.stopProducing.assert_called_once()
    mocked_sender.return_value.unregisterProducer.assert_called_once()
