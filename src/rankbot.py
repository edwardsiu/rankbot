import logging
import logging.handlers

import asyncio
from src import commands
import discord


class Isperia(discord.Client):
    def __init__(self, token):
        super().__init__()
        self.token = token
        self.commands = ['help']
        self.MAX_MSG_LEN = 2000
        self.logger = logging.getLogger('discord')
        self.logger.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler(
            filename='discord.log', encoding='utf-8', mode='w', 
            backupCount=1, maxBytes=1000000)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        self.logger.addHandler(handler)

    async def on_ready(self):
        self.logger.info('Logged in as {}'.format(self.user.name))

    async def say(self, msg, channel):
        if len(msg) > self.MAX_MSG_LEN:
            self.logger.info("Split message into two")
            await self.say(message[:self.MAX_MSG_LEN], channel)
            await self.say(message[self.MAX_MSG_LEN:], channel)
            return

        self.logger.info("Saying: {}".format(msg).encode("ascii", "ignore"))
        await self.send_typing(channel)
        await self.send_message(channel, msg)

    async def on_message(self, msg):
        if msg.author == self.user:
            return
        text = msg.content
        user = msg.author

        if text[0] != '!':
            return

        cmd = text.split()[0][1:]
        if cmd in self.commands:
            cmd_to_run = getattr(commands, cmd)
            result = cmd_to_run(text)
            if result:
                await self.say(str(result), msg.channel)

