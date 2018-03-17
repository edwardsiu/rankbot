import logging
import logging.handlers

import asyncio
from src import status_codes as stc
import discord
import hashids
from pymongo import MongoClient

class Isperia(discord.Client):
    def __init__(self, token, mongodb_host, mongodb_port):
        super().__init__()
        self.token = token
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

        if not text or text[0] != '!':
            return

        cmd = text.split()[0][1:]
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
        elif cmd == "pending":
            await self.pending(msg)
        elif cmd == "status":
            await self.status(msg)
        else:
            await self.help(msg) 

    async def help(self, msg):
        user = msg.author
        if (len(msg.content.split()) == 1):
            await self.say(
                ("Commands:\n"
            +   "```!help        -   show command list\n"
            +   "!register    -   register to the cEDH league\n"
            +   "!log         -   log a match result, type '!help log' for more info\n"
            +   "!confirm     -   confirm a match result\n"
            +   "!deny        -   dispute a match result\n"
            +   "!score       -   check your league points\n"
            +   "!describe    -   league stats```"),
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
                "name": user.name,
                "user_id": user.id,
                "points": 0,
                "pending": [],
                "accepted": 0,
                "disputed": []
            }
            result = members.insert_one(data)
            await self.say("Registered {} to the cEDH league".format(
                user.mention), msg.channel)
        else:
            await self.say("{} is already registered".format(user.mention),
                msg.channel)

    async def unregister(self, msg):
        user = msg.author
        members = self.db.members
        if not members.find_one_and_delete({"user_id": user.id}):
            await self.say("{} is not previously registered".format(
                user.mention), msg.channel)
        else:
            await self.say(
                "{} has been unregistered from the cEDH league".format(
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

        if len(losers) != 1:
            await self.say("There must be exactly 4 players to log a result.",
                            msg.channel)
            return

        game_id = self.create_pending_game(msg, winner, players)
        await self.say(
            ("Match has been logged and awaiting confirmation from "
            + ("{} "*len(losers) + "\n").format(*[u.mention for u in losers])
            + "```game id: {}```".format(game_id)), msg.channel)
        

        msg_text = ("Confirm game loss against **{}**?\n".format(winner.name)
                +   "To **confirm** this record, say: \n"
                +   "```!confirm {}```\n".format(game_id)
                +   "To **deny** this record, say: \n"
                +   "```!deny {}```".format(game_id))
        await self.say(msg_text, msg.channel)

    def create_pending_game(self, msg, winner, players):
        # generate a unique game_id
        game_id = self.hasher.encode(int(msg.id))
        # create a pending game record in the database for players
        pending_record = {
            "game_id": game_id,
            "status": stc.PENDING,
            "winner": winner.id,
            "players": {u.id: stc.UNCONFIRMED for u in players}
        }
        pending_record["players"][winner.id] = stc.CONFIRMED
        matches = self.db.matches
        result = matches.insert_one(pending_record)
        members = self.db.members
        for player in players:
            members.update_one(
                {"user_id": player.id},
                {
                "$push": {
                    "pending": game_id
                }
                }
            )
        return game_id

    async def confirm(self, msg):
        if len(msg.content.split()) < 2:
            await self.say("Please include the game id to confirm", 
                msg.channel)
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
            await self.say("Received confirmation from {}".format(
                user.mention), msg.channel)
            await self.check_match_status(game_id, msg.channel)
        else:
            await self.say("You have already confirmed this match", msg.channel)

    async def check_match_status(self, game_id, channel):
        matches = self.db.matches
        pending_game = matches.find_one({"game_id": game_id})
        players = pending_game["players"]
        for player in players:
            if players[player] == stc.UNCONFIRMED:
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
        self.update_score(pending_game)
        members = self.db.members
        for player in players:
            members.update_one(
                {"user_id": user_id},
                {
                    "$inc": {"accepted": 1},
                    "$pull": {"pending": game_id}
                }
            )
        await self.say("Match {} has been confirmed".format(game_id), channel)

    def update_score(self, match):
        members = self.db.members
        for player in match["players"]:
            if player == match["winner"]:
                members.update_one(
                {"user_id": match["winner"]},
                {
                    "$inc": {"points": 3}
                }
                )
            else:
                members.update_one(
                {"user_id": player},
                {
                    "$inc": {"points": -1}
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
                    "$set": {"status": stc.DISPUTED}
                }
            )
            if pending_game["players"][user.id] == stc.CONFIRMED:
                matches.update_one(
                    {"game_id": game_id},
                    {
                        "$set": {
                            "players.{}".format(user.id): stc.UNCONFIRMED
                        }
                    }
                )
        await self.say("This match has been marked as **disputed**",
            msg.channel)

    async def score(self, msg):
        if (len(msg.content.split()) < 2):
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
        +   "Confirmed match results: {}\n".format(num_accepted_matches)
        +   "Pending match results: {}\n".format(num_pending_matches)
        +   "Disputed match results: {}".format(num_disputed_matches)),
            msg.channel)

    async def pending(self, msg):
        user = msg.author
        matches = self.db.matches
        members = self.db.members
        player = members.find_one({"user_id": user.id})
        if len(player["pending"]) == 0:
            await self.say("You have no pending match records.", msg.channel)
            return
        pending_list = "List of matches awaiting confirmation:\n"
        for game_id in player["pending"]:
            pending_list += "```{}```\n".format(game_id)
        await self.say(pending_list, msg.channel)

    async def status(self, msg):
        if (len(msg.content.split()) < 2):
            await self.say("Please include a game id", msg.channel)
            return
        game_id = msg.content.split()[1]
        matches = self.db.matches
        match = matches.find_one({"game_id": game_id})
        if not match:
            await self.say("No match found for game id {}".format(game_id),
                    msg.channel)
            return
        members = self.db.members
        winner = members.find_one({"user_id": match["winner"]})
        players = [members.find_one({"user_id": player_id}) for player_id
            in match["players"]]
        status_text = ("```Game id: {}\n".format(match["game_id"])
                +   "Status: {}\n".format(match["status"])
                +   "Winner: {}\n".format(winner["name"])
                +   "Players:\n"
        )
        for player in players:
            status_text += "    {}: {}\n".format(
                player["name"],
                match["players"][player["user_id"]])
        status_text += "Status: {}".format(match["status"])
        await self.say(status_text, msg.channel)

    async def reset(self, msg):
        if msg.author.name != self.admin:
            return
        members = self.db.members
        matches = self.db.matches
        members.update_many({},
            {
                "$set": {
                    "points": 0
                }
            }
        )
        matches.delete_many({})
        await self.say(
            ("All registered players have had their score reset to 0 and "
        +   "all match records have been cleared."), msg.channel)
