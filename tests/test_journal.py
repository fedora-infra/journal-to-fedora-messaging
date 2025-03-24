# SPDX-FileCopyrightText: Contributors to the Fedora Project
#
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import mock

import pytest
import pytest_twisted
from twisted.internet import defer, reactor

from journal_to_fedora_messaging.journal import JournalReader


def sleep(duration=1):
    d = defer.Deferred()
    reactor.callLater(duration, d.callback, None)
    return d


@pytest_twisted.inlineCallbacks
def test_journal(config):
    reader = JournalReader(config)
    reader._command = ["bash", "-c", 'for i in `seq 10`; do echo \'{"dummy": "dummy"}\'; done']
    consumer = mock.Mock()
    reader.consumer = consumer
    reader.resumeProducing()
    yield sleep()
    assert consumer.write.call_count == 10
    for call in consumer.write.call_args_list:
        assert call[0] == ({"dummy": "dummy"},)


def test_journal_no_consumer(config):
    reader = JournalReader(config)
    with pytest.raises(RuntimeError):
        reader.resumeProducing()


@pytest_twisted.inlineCallbacks
def test_journal_stop(config):
    reader = JournalReader(config)
    reader._command = [
        "bash",
        "-c",
        'while true; do echo \'{"dummy": "dummy"}\'; sleep 0.1; done',
    ]
    consumer = mock.Mock()
    reader.consumer = consumer
    reader.resumeProducing()
    yield sleep()
    reader.stopProducing()
    assert consumer.write.call_count > 5
    # it should be around 10
    assert consumer.write.call_count < 20


@pytest_twisted.inlineCallbacks
def test_journal_not_json(config):
    reader = JournalReader(config)
    reader._command = ["echo", "dummy"]
    consumer = mock.Mock()
    reader.consumer = consumer
    reader.resumeProducing()
    yield sleep()
    consumer.write.assert_not_called()


@pytest_twisted.inlineCallbacks
def test_journal_stderr(config, caplog):
    reader = JournalReader(config)
    reader._command = ["bash", "-c", "echo dummy > /dev/stderr"]
    consumer = mock.Mock()
    reader.consumer = consumer
    reader.resumeProducing()
    yield sleep()
    consumer.write.assert_not_called()
    assert caplog.messages == ["journalctl wrote to stderr: dummy\n"]
