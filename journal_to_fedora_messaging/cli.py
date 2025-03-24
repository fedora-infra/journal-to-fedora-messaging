# SPDX-FileCopyrightText: Contributors to the Fedora Project
#
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import os

import click
from twisted.internet import asyncioreactor, error


try:
    asyncioreactor.install()
except error.ReactorAlreadyInstalledError:
    # The tests install a reactor before importing this module
    from twisted.internet import reactor

    if not isinstance(reactor, asyncioreactor.AsyncioSelectorReactor):
        raise

from fedora_messaging.api import _init_twisted_service
from fedora_messaging.config import conf as fm_config
from fedora_messaging.exceptions import ConfigurationException
from twisted.application import service
from twisted.internet import reactor

from .journal import JournalReader
from .sender import LogMessageConsumer


LOGGER = logging.getLogger(__name__)


@click.command()
@click.option("-c", "--config", envvar="FEDORA_MESSAGING_CONF", help="Configuration file")
def main(config):
    if config:
        if not os.path.isfile(config):
            raise click.exceptions.BadParameter(f"{config} is not a file")
        try:
            fm_config.load_config(config_path=config)
        except ConfigurationException as e:
            raise click.exceptions.BadParameter(str(e)) from e
    fm_config.setup_logging()

    conf = fm_config["consumer_config"]
    bridge_service = JournalToFedoraMessagingService(conf)
    reactor.callWhenRunning(bridge_service.startService)
    _init_twisted_service()
    reactor.run()


class JournalToFedoraMessagingService(service.Service):

    def __init__(self, config):
        self._consumer = LogMessageConsumer(config)
        self._producer = JournalReader(config)

    def startService(self):
        self._consumer.registerProducer(self._producer, True)
        self._producer.resumeProducing()

    def stopService(self):
        self._producer.stopProducing()
        self._consumer.unregisterProducer()
