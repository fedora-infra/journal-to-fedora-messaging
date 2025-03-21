# SPDX-FileCopyrightText: Contributors to the Fedora Project
#
# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import logging

from fedora_messaging.api import twisted_publish
from fedora_messaging.exceptions import ConnectionException, PublishReturned
from fedora_messaging.message import get_class
from twisted.internet import defer


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


class MessageSender:
    def __init__(self, config):
        self.config = config

    def validate_config(self):
        if not self.config.get("logs", []):
            LOGGER.warning("No log defined in the configuration, nothing will be published")
        for log in self.config.get("logs", []):
            if not log["schema"]:
                raise ValueError(f"No schema defined in the configuration for: {log!r}")
            if not log.get("filters", []):
                LOGGER.warning(
                    f"No filters defined in the configuration for: {log!r}. "
                    "This will match every log entry."
                )

    def _get_schema(self, content: dict):
        for log in self.config["logs"]:
            if _matches(log, content):
                return get_class(log["schema"])
        return None

    def send(self, content: dict):
        schema = self._get_schema(content)
        if schema is None:
            LOGGER.debug("Unmatched log: %r", content)
            return defer.succeed(None)

        LOGGER.debug("Republishing %r", content)
        message = schema(body=_get_body(content))

        def _log_errors(failure):
            if failure.check(PublishReturned):
                LOGGER.warning(
                    f"Fedora Messaging broker rejected message {message.id}: {failure.value}"
                )
            elif failure.check(ConnectionException):
                LOGGER.warning(f"Error sending message {message.id}: {failure.value}")
            else:
                LOGGER.error(f"Unknown error publishing message {message.id}: {failure.value}")

        deferred = twisted_publish(message)
        deferred.addErrback(_log_errors)
        return deferred.asFuture(asyncio.get_running_loop())
