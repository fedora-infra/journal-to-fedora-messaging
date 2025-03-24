# SPDX-FileCopyrightText: Contributors to the Fedora Project
#
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from fedora_messaging.api import twisted_publish
from fedora_messaging.exceptions import ConnectionException, PublishReturned
from fedora_messaging.message import get_class, Message
from twisted.internet import defer, interfaces, reactor
from twisted.python.failure import Failure
from zope.interface import implementer


LOGGER = logging.getLogger(__name__)

PRUNE_FROM_LOG = (
    "_MACHINE_ID",
    # Those are metadata fields: https://systemd.io/JOURNAL_EXPORT_FORMATS/
    "__CURSOR",
    "__SEQNUM",
    "__SEQNUM_ID",
    "__MONOTONIC_TIMESTAMP",
)


def _matches(log_def, content):
    for key, value in log_def.get("filters", []).items():
        if key not in content:
            return False
        if content[key] != value:
            return False
    return True


def _get_body(content: dict):
    body = content.copy()
    for key in PRUNE_FROM_LOG:
        if key in body:
            del body[key]
    return body


@implementer(interfaces.IConsumer)
class MessageSender:
    def __init__(self, config):
        self._config = config
        self._producer = None

    def validate_config(self):
        if not self._config.get("logs", []):
            LOGGER.warning("No log defined in the configuration, nothing will be published")
        for log in self._config.get("logs", []):
            if not log.get("schema"):
                raise ValueError(f"No schema defined in the configuration for: {log!r}")
            if get_class(log["schema"]) == Message:
                raise ValueError(f"The schema {log['schema']} is not installed")
            if not log.get("filters", []):
                LOGGER.warning(
                    f"No filters defined in the configuration for: {log!r}. "
                    "This will match every log entry."
                )

    def _get_schema(self, content: dict):
        for log in self._config["logs"]:
            if _matches(log, content):
                return get_class(log["schema"])
        return None

    def registerProducer(self, producer, streaming):
        self._producer = producer
        producer.consumer = self

    def unregisterProducer(self):
        self._producer.consumer = None
        self._producer = None

    def write(self, data: dict):
        schema = self._get_schema(data)
        if schema is None:
            # LOGGER.debug("Unmatched log: %r", data)
            return defer.succeed(None)

        message = schema(body=_get_body(data))

        LOGGER.debug("Publishing message %s on %s: %r", message.id, message.topic, message.body)

        timeout = self._config.get("publish_timeout", 30)

        def _log_errors(failure: Failure):
            if failure.check(PublishReturned):
                LOGGER.warning(
                    f"Fedora Messaging broker rejected message {message.id}: {failure.value}"
                )
            elif failure.check(ConnectionException):
                LOGGER.warning(f"Error sending message {message.id}: {failure.value}")
            elif failure.check(defer.TimeoutError):
                LOGGER.warning(
                    f"Timeout sending message {message.id} on {message.topic} after {timeout}s"
                )
            else:
                LOGGER.error(
                    f"Unknown error publishing message {message.id}: "
                    f"{failure.value} ({failure.type})"
                )
                LOGGER.error(failure.getTraceback())

        def _log_success(_result):
            LOGGER.info(f"Published message {message.id} on {message.topic}")

        deferred = twisted_publish(message)
        deferred.addTimeout(timeout, reactor)
        deferred.addCallbacks(_log_success, _log_errors)
        return deferred
