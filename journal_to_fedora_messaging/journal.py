# SPDX-FileCopyrightText: Contributors to the Fedora Project
#
# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import json
import logging


LOGGER = logging.getLogger(__name__)


class JournalReader:

    def __init__(self, config):
        self.config = config
        self._command = self.config.get("journalctl", ["journalctl"])[:]
        self._command.extend(["--follow", "--output", "json"])
        self._proc = None

    async def read(self):
        self._proc = await asyncio.create_subprocess_exec(
            *self._command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
        )

        while not self._proc.stdout.at_eof():
            content = await self._proc.stdout.readline()
            if not content:
                break
            yield json.loads(content)

        LOGGER.info("journalctl stopped producing output")
        await self._proc.wait()
        LOGGER.info("journalctl exited with status %s", self._proc.returncode)

    async def stop(self):
        if self._proc is None:
            return
        self._proc.terminate()
        await self._proc.wait()
