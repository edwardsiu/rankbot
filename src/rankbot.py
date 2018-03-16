import logging
import logging.handlers

import asyncio
#from src import commands
import discord
import hashids


class Isperia(discord.Client):
    def __init__(self, token):
        super().__init__()
        self.token = token
        self.commands = ['help', 'log', 'register']
        self.MAX_MSG_LEN = 2000
        self.hasher = hashids.Hashids(salt="cEDH league")
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

        if text[0] != '!':
            return

        cmd = text.split()[0][1:]
        """if cmd in self.commands:
            cmd_to_run = getattr(commands, cmd)
            result = cmd_to_run(msg)
            if result:
                await self.say(str(result), msg.channel)"""
        if cmd == "help":
            await self.help(msg)
        elif cmd == "log":
            await self.log(msg)
        elif cmd == "register":
            await self.register(msg)
        else:
            await self.invalid_msg(msg)

    async def help(self, msg):
        await self.say("You called the help command.", msg.channel)

    async def register(self, msg):
        # check if user is already registered
        user = msg.author
        await self.say("Registered {} to the cEDH league".format(
                user.mention), msg.channel)

    async def log(self, msg):
        winner = msg.author
        losers = msg.mentions
        """if len(losers) != 3:
            await self.say("There must be exactly 4 players to log a result.",
                            msg.channel)
            return

        if (winner in losers) or (len(losers) != len(set(losers))):
            await self.say("Duplicate players are not allowed.",
                            msg.channel)
            return"""

        # generate a unique game_id
        game_id = self.hasher.encode(int(msg.id))
        # create a pending game record in the database for players
        # send pm to each user to confirm result
        for user in losers:
            msg_text = ("Confirm game loss against **{}**?\n".format(
                    winner.name)
                    +   "To **confirm** this record, say: "
                    +   "```!confirm {}```\n".format(game_id)
                    +   "To **deny** this record, say: "
                    +   "```!deny {}```".format(game_id))
            await self.say(msg_text, user)

    async def confirm(self, msg):
        pass

    async def deny(self, msg):
        pass
