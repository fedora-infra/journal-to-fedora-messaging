# SPDX-FileCopyrightText: Contributors to the Fedora Project
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import logging
import os
from shutil import which

from twisted.internet import interfaces, protocol, reactor
from zope.interface import implementer


LOGGER = logging.getLogger(__name__)


@implementer(interfaces.IPushProducer)
class JournalReader:

    def __init__(self, config):
        self.config = config
        self._command = self.config.get("journalctl_command", ["journalctl"])[:]
        self._command.extend(["--follow", "--output", "json", "--since", "now"])
        self.consumer = None
        self._protocol = None

    def resumeProducing(self):
        if self.consumer is None:
            raise RuntimeError("No consumer to produce to")
        self._protocol = JournalProtocol(self.consumer)
        reactor.spawnProcess(
            self._protocol, which(self._command[0]), args=self._command, env=os.environ
        )

    def stopProducing(self):
        self._protocol.transport.signalProcess("TERM")
        self._protocol.transport.loseConnection()


class JournalProtocol(protocol.ProcessProtocol):
    def __init__(self, consumer: interfaces.IConsumer):
        self._consumer = consumer
        self._delimiter = b"\n"
        self._buffer = b""

    def connectionMade(self):
        self.transport.closeStdin()

    def outReceived(self, data):
        lines = (self._buffer + data).split(self._delimiter)
        self._buffer = lines.pop(-1)
        for line in lines:
            try:
                self._consumer.write(json.loads(line))
            except json.decoder.JSONDecodeError as e:
                LOGGER.warning(f"journalctl did not produce JSON! {e}")

    def errReceived(self, data):
        LOGGER.warning(f"journalctl wrote to stderr: {data.decode()}")

    def outConnectionLost(self):
        LOGGER.debug("journalctl stopped producing output")

    def processExited(self, reason):
        LOGGER.info("journalctl exited with status %s", reason.value.exitCode)

    def processEnded(self, reason):
        LOGGER.info("journalctl ended with status %s", reason.value.exitCode)
