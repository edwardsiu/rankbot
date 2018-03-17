import logging
import logging.handlers

import asyncio
from src import status_codes as stc
import discord
import hashids
from pymongo import MongoClient, DESCENDING

class Isperia(discord.Client):
    def __init__(self, token, mongodb_host, mongodb_port):
        super().__init__()
        self.token = token
        self.commands = [
            'help', 'log', 'register', 'unregister', 'confirm', 'deny',
            'describe', 'score', 'reset', 'top']
        self.MAX_MSG_LEN = 2000
        self.admin = "asm"
        self.hasher = hashids.Hashids(salt="cEDH league")
        self.logger = logging.getLogger('discord')
        self.logger.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler(
            filename='discord.log', encoding='utf-8', mode='w',
            backupCount=1, maxBytes=1000000)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        self.logger.addHandler(handler)
        self.db = MongoClient(mongodb_host, mongodb_port).rankdb

    async def on_ready(self):
        self.logger.info('Logged in as {}'.format(self.user.name))

    async def say(self, msg, channel):
        if len(msg) > self.MAX_MSG_LEN:
            self.logger.info("Split message into two")
            await self.say(msg[:self.MAX_MSG_LEN], channel)
            await self.say(msg[self.MAX_MSG_LEN:], channel)
            return

        self.logger.info("Saying: {}".format(msg).encode("ascii", "ignore"))
        await self.send_typing(channel)
        await self.send_message(channel, msg)

    async def on_message(self, msg):
        if msg.author == self.user:
            return
        text = msg.content

        if not text or text[0] != '!':
            return

        cmd = text.split()[0][1:]
        if cmd not in self.commands:
            await self.help(msg)
            return

        if cmd == "help":
            await self.help(msg)
        elif cmd == "log":
            await self.log(msg)
        elif cmd == "register":
            await self.register(msg)
        elif cmd == "unregister":
            await self.unregister(msg)
        elif cmd == "confirm":
            await self.confirm(msg)
        elif cmd == "deny":
            await self.deny(msg)
        elif cmd == "score":
            await self.score(msg)
        elif cmd == "describe":
            await self.describe(msg)
        elif cmd == "reset":
            await self.reset(msg)
        elif cmd == "top":
            await self.top(msg)

    async def help(self, msg):
        user = msg.author
        if len(msg.content.split()) == 1:
            await self.say(
                ("Commands:\n"
                 +   "```!help        -   show command list\n"
                 +   "!register    -   register to the cEDH league\n"
                 +   "!log         -   log a match result, type '!help log' for more info\n"
                 +   "!confirm     -   confirm a match result\n"
                 +   "!deny        -   dispute a match result\n"
                 +   "!score       -   check your league points\n"
                 +   "!describe    -   league stats```",
                 +   "!top         -   see the top players in the league```"),
                user)
        else:
            await self.say(("To log a match result, type: \n"
                            + "```!log @player1 @player2 @player3```\n"
                            + "where players are the losers of the match, and the "
                            + "winner is the user calling the log command.\n"
                            + "There must be exactly 3 losers to log the match."),
                           user)

    async def register(self, msg):
        # check if user is already registered
        user = msg.author
        members = self.db.members
        if not members.find_one({"user_id": user.id}):
            data = {
                "user": user.name,
                "user_id": user.id,
                "points": 0
            }
            members.insert_one(data)
            await self.say("Registered {} to the cEDH league".format(
                user.mention), msg.channel)
        else:
            await self.say("{} is already registered".format(user.mention), msg.channel)

    async def unregister(self, msg):
        user = msg.author
        members = self.db.members
        if not members.find_one_and_delete({"user_id": user.id}):
            await self.say("{} is not previously registered".format(
                user.mention), msg.channel)
        else:
            await self.say("{} has been unregistered from the cEDH league".format(
                user.mention), msg.channel)

    async def log(self, msg):
        winner = msg.author
        losers = msg.mentions
        players = [winner] + losers
        members = self.db.members
        # verify that all players are registered players
        for user in players:
            if not members.find_one({"user_id": user.id}):
                await self.say("{} is not a registered player".format(
                    user.mention), msg.channel)
                return

        if len(losers) != 3:
            await self.say("There must be exactly 4 players to log a result.",
                           msg.channel)
            return

        if (winner in losers) or (len(losers) != len(set(losers))):
            await self.say("Duplicate players are not allowed.",
                           msg.channel)
            return

        # generate a unique game_id
        game_id = self.hasher.encode(int(msg.id))
        # create a pending game record in the database for players
        pending_record = {
            "game_id": game_id,
            "status": stc.PENDING,
            "winner": winner.id,
            "losers": {u.id: stc.UNCONFIRMED for u in losers}
        }
        matches = self.db.matches
        matches.insert_one(pending_record)
        # send pm to each user to confirm result
        for user in losers:
            msg_text = ("Confirm game loss against **{}**?\n".format(winner.name)
                        +   "To **confirm** this record, say: \n"
                        +   "```!confirm {}```\n".format(game_id)
                        +   "To **deny** this record, say: \n"
                        +   "```!deny {}```".format(game_id))
            await self.say(msg_text, user)

    async def confirm(self, msg):
        if len(msg.content.split()) < 2:
            await self.say("Please include the game id to confirm", msg.channel)
            return

        user = msg.author
        game_id = msg.content.split()[1]
        matches = self.db.matches
        pending_game = matches.find_one({"game_id": game_id})
        if not pending_game:
            await self.say("No matching game id found", msg.channel)
            return
        if pending_game["losers"][user.id] == stc.UNCONFIRMED:
            matches.update_one(
                {"game_id": game_id},
                {
                    "$set": {
                        "losers.{}".format(user.id): stc.CONFIRMED
                    }
                }
            )
            await self.say("Confirmed match result", msg.channel)
            self.check_match_status(game_id)
        else:
            await self.say("You have already confirmed this match", msg.channel)

    def check_match_status(self, game_id):
        matches = self.db.matches
        pending_game = matches.find_one({"game_id": game_id})
        losers = pending_game["losers"]
        for player in losers:
            if losers[player] == stc.UNCONFIRMED:
                return
        # all players have confirmed the result
        matches.update_one(
            {"game_id": game_id},
            {
                "$set": {
                    "status": stc.ACCEPTED
                }
            }
        )
        self.update_winner(pending_game["winner"])
        self.update_losers(pending_game["losers"])

    def update_winner(self, winner):
        members = self.db.members
        members.update_one(
            {"user_id": winner},
            {
                "$inc": {
                    "points": 3
                }
            }
        )

    def update_losers(self, losers):
        members = self.db.members
        for loser in losers:
            members.update_one(
                {"user_id": loser},
                {
                    "$inc": {
                        "points": -1
                    }
                }
            )

    async def deny(self, msg):
        if len(msg.content.split()) < 2:
            await self.say("Please include the game id to deny", msg.channel)
            return

        user = msg.author
        game_id = msg.content.split()[1]
        matches = self.db.matches
        pending_game = matches.find_one({"game_id": game_id})
        if not pending_game:
            await self.say("No matching game id found", msg.channel)
            return
        if pending_game["status"] == stc.ACCEPTED:
            await self.say("Cannot deny a confirmed match", msg.channel)
            return
        if pending_game["status"] == stc.PENDING:
            matches.update_one(
                {"game_id": game_id},
                {
                    "$set": {
                        "status": stc.DISPUTED
                    }
                }
            )
            if pending_game["losers"][user.id] == stc.CONFIRMED:
                matches.update_one(
                    {"game_id": game_id},
                    {
                        "$set": {
                            "losers.{}".format(user.id): stc.UNCONFIRMED
                        }
                    }
                )
        await self.say("This match has been marked as **disputed**",
                       msg.channel)

    async def score(self, msg):
        if len(msg.content.split() < 2):
            users = [msg.author]
        else:
            users = msg.mentions
        members = self.db.members
        for user in users:
            member = members.find_one({"user_id": user.id})
            await self.say("{} has {} points".format(
                user.mention, member["points"]), msg.channel)

    async def describe(self, msg):
        matches = self.db.matches
        num_accepted_matches = matches.count({"status": stc.ACCEPTED})
        num_pending_matches = matches.count({"status": stc.PENDING})
        num_disputed_matches = matches.count({"status": stc.DISPUTED})
        members = self.db.members
        num_members = members.count()
        await self.say(
            ("There are {} registered players in the cEDH league\n".format(
                num_members)
             + "Confirmed match results: {}\n".format(num_accepted_matches)
             + "Pending match results: {}\n".format(num_pending_matches)
             + "Disputed match results: {}".format(num_disputed_matches)),
            msg.channel)

    async def reset(self, msg):
        if msg.author.name != self.admin:
            return
        members = self.db.members
        matches = self.db.matches
        members.update_many({}, {
            "$set": {
                "points": 0
            }
        })
        matches.delete_many({})
        await self.say(
            ("All registered players have had their score reset to 0 and "
             + "all match records have been cleared."), msg.channel)

    async def top(self, msg):
        members = self.db.members
        topMembers = members.find(limit=10, sort=[('points', DESCENDING)])
        await self.say("Top Players:\n {}".format(
            ["{}. {} with {} points".format(ix + 1, member.user, member['points'])
             for ix, member in enumerate(topMembers)]
        ), msg.channel)
