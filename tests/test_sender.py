# SPDX-FileCopyrightText: Contributors to the Fedora Project
#
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
from copy import deepcopy
from unittest import mock

import pytest
import pytest_twisted
from fedora_messaging.exceptions import ConnectionException, PublishReturned
from journal_to_fedora_messaging_messages.ipa import IpaUserAddV1
from twisted.internet import defer

from journal_to_fedora_messaging.sender import MessageSender


@pytest.fixture
def message_user_add():
    return {
        "_SYSTEMD_UNIT": "httpd.service",
        "_SYSTEMD_CGROUP": "/system.slice/httpd.service",
        "_UID": "992",
        "_SYSTEMD_INVOCATION_ID": "342f3dc5aa0a425e93f88c82edaaa162",
        "_SYSTEMD_SLICE": "system.slice",
        "_SELINUX_CONTEXT": "system_u:system_r:httpd_t:s0",
        "CODE_FILE": "/usr/lib/python3.12/site-packages/ipalib/frontend.py",
        "__REALTIME_TIMESTAMP": "1742797896433915",
        "_PID": "9689",
        "_HOSTNAME": "ipa.tinystage.test",
        "SYSLOG_IDENTIFIER": "/mod_wsgi",
        "PRIORITY": "5",
        "IPA_API_COMMAND": "user_add",
        "_COMM": "httpd",
        "_CAP_EFFECTIVE": "0",
        "MESSAGE": '[IPA.API] admin@TINYSTAGE.TEST: user_add: SUCCESS [ldap2_139734790567408] {"uid": "testing", "givenname": "Testing", "sn": "User", "cn": "Testing User", "displayname": "Testing User", "initials": "TU", "gecos": "Testing User", "krbprincipalname": ["testing@TINYSTAGE.TEST"], "random": false, "noprivate": false, "all": false, "raw": false, "version": "2.254", "no_members": false}',
        "CODE_FUNC": "__audit_to_journal",
        "CODE_LINE": "495",
        "_RUNTIME_SCOPE": "system",
        "IPA_API_RESULT": "SUCCESS",
        "_EXE": "/usr/sbin/httpd",
        "_GID": "991",
        "_CMDLINE": '"(wsgi:ipa)     " -DFOREGROUND',
        "_BOOT_ID": "24e0753793004f54b0a4cd1d1c4fbad5",
        "MESSAGE_ID": "6d70f1b493df36478bc3499257cd3b17",
        "_SOURCE_REALTIME_TIMESTAMP": "1742797896433899",
        "IPA_API_ACTOR": "admin@TINYSTAGE.TEST",
        "IPA_API_PARAMS": '{"uid": "testing", "givenname": "Testing", "sn": "User", "cn": "Testing User", "displayname": "Testing User", "initials": "TU", "gecos": "Testing User", "krbprincipalname": ["testing@TINYSTAGE.TEST"], "random": false, "noprivate": false, "all": false, "raw": false, "version": "2.254", "no_members": false}',
        "_TRANSPORT": "journal",
    }


@pytest.fixture
def mocked_publish():
    with mock.patch("journal_to_fedora_messaging.sender.twisted_publish") as mock_twisted_publish:
        mock_twisted_publish.return_value = defer.succeed(None)
        yield mock_twisted_publish


@pytest_twisted.inlineCallbacks
def test_sender_user_add(config, message_user_add, mocked_publish, caplog):
    consumer = MessageSender(config)
    caplog.set_level(logging.INFO)
    yield consumer.write(message_user_add)
    mocked_publish.assert_called_once()
    sent_msg = mocked_publish.call_args[0][0]
    assert isinstance(sent_msg, IpaUserAddV1)
    assert len(caplog.messages) == 1
    assert caplog.messages[0].startswith("Published message ")


def test_sender_consumer_interface(config):
    consumer = MessageSender(config)
    producer = mock.Mock()
    consumer.registerProducer(producer, True)
    assert producer.consumer == consumer
    consumer.unregisterProducer()
    assert producer.consumer is None


def test_sender_validate_config(config, caplog):
    config_orig = deepcopy(config)
    MessageSender(config).validate_config()

    config["logs"][0]["schema"] += ".doesnotexist"
    with pytest.raises(ValueError):
        MessageSender(config).validate_config()

    del config["logs"][0]["schema"]
    with pytest.raises(ValueError):
        MessageSender(config).validate_config()

    config = deepcopy(config_orig)
    config["logs"][0]["filters"] = {}
    MessageSender(config).validate_config()
    assert len(caplog.messages) == 2
    assert caplog.messages[1].startswith("No filters defined in the configuration for")
    assert caplog.records[1].levelname == "WARNING"

    config["logs"] = []
    caplog.clear()
    MessageSender(config).validate_config()
    assert len(caplog.messages) == 1
    assert caplog.messages[0] == "No log defined in the configuration, nothing will be published"
    assert caplog.records[0].levelname == "WARNING"


def test_sender_prune(config, message_user_add, mocked_publish):
    consumer = MessageSender(config)
    message_user_add["_MACHINE_ID"] = "dummy"
    consumer.write(message_user_add)
    mocked_publish.assert_called_once()
    sent_msg = mocked_publish.call_args[0][0]
    assert "_MACHINE_ID" not in sent_msg.body


@pytest.mark.parametrize(
    "exception_class", [PublishReturned, ConnectionException, defer.TimeoutError, ValueError]
)
@pytest_twisted.inlineCallbacks
def test_sender_failure(config, message_user_add, mocked_publish, caplog, exception_class):
    consumer = MessageSender(config)
    mocked_publish.return_value = defer.fail(exception_class())
    yield consumer.write(message_user_add)
    assert len(caplog.messages) == 1
    log_message = caplog.messages[0]
    if exception_class == PublishReturned:
        assert log_message.startswith("Fedora Messaging broker rejected message")
    elif exception_class == ConnectionException:
        assert log_message.startswith("Error sending message")
    elif exception_class == defer.TimeoutError:
        assert log_message.startswith("Timeout sending message")
    else:
        assert log_message.startswith("Unknown error publishing message")


@pytest_twisted.inlineCallbacks
def test_sender_unmatched(config, message_user_add, mocked_publish):
    consumer = MessageSender(config)
    message_user_add["IPA_API_COMMAND"] = "does-not-match"
    yield consumer.write(message_user_add)
    del message_user_add["IPA_API_COMMAND"]
    yield consumer.write(message_user_add)
    mocked_publish.assert_not_called()
