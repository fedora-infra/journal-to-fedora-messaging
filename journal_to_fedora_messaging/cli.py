# SPDX-FileCopyrightText: Contributors to the Fedora Project
#
# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import logging
import os

import click
import fedora_messaging

from .journal import JournalReader
from .sender import MessageSender


LOGGER = logging.getLogger(__name__)


@click.command()
@click.option("-c", "--config", envvar="FEDORA_MESSAGING_CONF", help="Configuration file")
def main(config):
    if config:
        if not os.path.isfile(config):
            raise click.exceptions.BadParameter(f"{config} is not a file")
        try:
            fedora_messaging.config.conf.load_config(config_path=config)
        except fedora_messaging.exceptions.ConfigurationException as e:
            raise click.exceptions.BadParameter(str(e)) from e
    fedora_messaging.config.conf.setup_logging()

    # Now start the consumer.
    conf = fedora_messaging.config.conf["consumer_config"]

    sender = MessageSender(conf)
    sender.validate_config()

    reader = JournalReader(conf)

    with asyncio.Runner() as runner:
        try:
            runner.run(run(reader, sender))
        except KeyboardInterrupt:
            click.echo("\rShutting down")
            runner.get_loop().run_until_complete(reader.stop())


async def run(reader, sender):
    async for log in reader.read():
        await sender.send(log)
