import logging
import logging.handlers

import asyncio
import discord
import hashids
from pymongo import MongoClient, DESCENDING
from src import status_codes as stc
from src import utils
import time

class Isperia(discord.Client):
    def __init__(self, token, config):
        super().__init__()
        self.token = token
        self.MAX_MSG_LEN = 2000
        self.client_id = config["client_id"]
        self.super_admins = config["admins"]
        self.league_name = config["league_name"]
        self.players = config["players"]
        self.hasher = hashids.Hashids(salt="cEDH league")
        self.logger = logging.getLogger('discord')
        self.logger.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler(
            filename='discord.log', encoding='utf-8', mode='w',
            backupCount=1, maxBytes=1000000)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        self.logger.addHandler(handler)
        self.db = MongoClient(config["mongodb_host"], config["mongodb_port"]).rankdb
        self.__configure_admins(self.super_admins)

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
        if cmd == "help":
            await self.help(msg)
        elif cmd == "addme":
            await self.addme(msg)
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
        elif cmd == "top":
            await self.top(msg)
        elif cmd == "add_admin":
            await self.add_admin(msg)
        elif cmd == "rm_admin":
            await self.rm_admin(msg)
        elif cmd == "override":
            await self.override(msg)
        elif cmd == "disputed":
            await self.list_disputed(msg)

    async def help(self, msg):
        user = msg.author
        if len(msg.content.split()) == 1:
            await self.say(
                ("Commands:\n"
                 +   "```!help        -   show command list\n\n"
                 +   "!addme       -   get invite link to add Isperia\n\n"
                 +   "!register    -   register to the {}\n\n".format(self.league_name)
                 +   "!log         -   log a match result\n"
                 +   "                 type '!help log' for more info\n\n"
                 +   "!confirm     -   confirm the most recent match result\n"
                 +   "                 or a specified game id\n\n"
                 +   "!deny        -   dispute the most recent match result\n"
                 +   "                 or a specified game id\n\n"
                 +   "!score       -   check your league score card\n\n"
                 +   "!describe    -   league stats\n\n"
                 +   "!top         -   see the top players in the league\n\n"
                 +   "!pending     -   list your pending matches\n\n"
                 +   "!status      -   show the status of a match (must include game id)```"),
                user)
            if self.__is_admin(user):
                await self.say(
                    ("Admin Commands:\n"
                     +   "```!reset       -   reset all points and remove all matches\n\n"
                     +   "!add_admin   -   set all mentioned users to admin\n\n"
                     +   "!rm_admin    -   remove admin privileges to mentioned users\n\n"
                     +   "!disputed    -   list all disputed matches\n\n"
                     +   "!override    -   include game_id and 'accept'\n"
                     +   "                 or 'remove' to resolve dispute```"),
                    user)
        else:
            await self.say(("To log a match result, type: \n"
                            + "```!log @player1 @player2 @player3```\n"
                            + "where players are the losers of the match, and the "
                            + "winner is the user calling the log command.\n"
                            + "There must be exactly {} losers to log the match.".format(
                                self.players-1)),
                           user)

    async def addme(self, msg):
        await self.say("https://discordapp.com/oauth2/authorize?client_id={}&scope=bot&permissions=0".format(
            self.client_id), msg.author)

    async def register(self, msg):
        # check if user is already registered
        user = msg.author
        members = self.db.members
        if not members.find_one({"user_id": user.id}):
            data = {
                "user": user.name,
                "user_id": user.id,
                "points": 1000,
                "pending": [],
                "accepted": 0,
                "wins": 0,
                "losses": 0
            }
            members.insert_one(data)
            await self.say("Registered {} to the {}".format(
                user.mention, self.league_name), msg.channel)
        else:
            await self.say("{} is already registered".format(user.mention), msg.channel)

    async def unregister(self, msg):
        user = msg.author
        members = self.db.members
        if not members.find_one_and_delete({"user_id": user.id}):
            await self.say("{} is not previously registered".format(
                user.mention), msg.channel)
        else:
            await self.say("{} has been unregistered from the {}".format(
                user.mention, self.league_name), msg.channel)

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

        if len(losers) != (self.players-1):
            await self.say("There must be exactly {} players to log a result.".format(
                self.players), msg.channel)
            return

        game_id = self.create_pending_game(msg, winner, players)
        await self.say("Match has been logged and awaiting confirmation from "
            +   ("{} "*len(losers) + "\n").format(*[u.mention for u in losers])
            +   "`game id: {}`\n".format(game_id)
            +   "To **confirm** this record, say: "
            +   "`!confirm {}`\n".format(game_id)
            +   "To **deny** this record, say: "
            +   "`!deny {}`".format(game_id), msg.channel)

    def create_pending_game(self, msg, winner, players):
        # generate a unique game_id
        game_id = utils.generate_game_id(self.hasher, msg.id, self.db.matches)
        # create a pending game record in the database for players
        pending_record = {
            "game_id": game_id,
            "status": stc.PENDING,
            "winner": winner.id,
            "players": {u.id: stc.UNCONFIRMED for u in players},
            "timestamp": time.time()
        }
        pending_record["players"][winner.id] = stc.CONFIRMED
        matches = self.db.matches
        matches.insert_one(pending_record)
        members = self.db.members
        for player in players:
            if player != winner:
                members.update_one(
                    {"user_id": player.id},
                    {
                        "$push": {"pending": game_id}
                    }
                )
        return game_id

    async def confirm(self, msg):
        user = msg.author
        members = self.db.members
        player = members.find_one({"user_id": user.id})
        if not player:
            return
        if not player["pending"]:
            await self.say("You have no pending games to confirm", msg.channel)
            return

        if len(msg.content.split()) < 2:
            game_id = player["pending"][-1]
        else:
            game_id = msg.content.split()[1]

        matches = self.db.matches
        pending_game = matches.find_one({"game_id": game_id})
        if not pending_game:
            await self.say("No matching game id found", msg.channel)
            return
        if user.id not in pending_game["players"]:
            return
        if pending_game["players"][user.id] == stc.UNCONFIRMED:
            matches.update_one(
                {"game_id": game_id},
                {
                    "$set": {
                        "players.{}".format(user.id): stc.CONFIRMED
                    }
                }
            )
            await self.say("Received confirmation from {}".format(
                user.mention), msg.channel)
            members.update_one(
                {"user_id": user.id},
                {
                    "$pull": {"pending": game_id}
                }
            )
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
                "$set": {"status": stc.ACCEPTED}
            }
        )
        members = self.db.members
        delta = utils.update_score(pending_game, members)
        for player in players:
            members.update_one(
                {"user_id": player},
                {
                    "$inc": {"accepted": 1}
                }
            )
        await self.__show_delta(game_id, delta, channel)

    async def __show_delta(self, game_id, delta, channel):
        await self.say("Match {} has been accepted.\n".format(game_id)
                    +  "`{}`".format(", ".join(
                    ["{0}: {1:+}".format(i["player"], i["change"]) for i in delta])), channel)

    async def deny(self, msg):
        user = msg.author
        members = self.db.members
        player = members.find_one({"user_id": user.id})
        if not player:
            return
        if not player["pending"]:
            await self.say("You have no pending games to confirm", msg.channel)
            return

        if len(msg.content.split()) < 2:
            game_id = player["pending"][-1]
        else:
            game_id = msg.content.split()[1]

        matches = self.db.matches
        pending_game = matches.find_one({"game_id": game_id})
        if not pending_game:
            await self.say("No matching game id found", msg.channel)
            return
        if user.id not in pending_game["players"]:
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
                self.reset_to_unconfirmed(game_id, user)
        await self.say("This match has been marked as **disputed**",
                       msg.channel)

    def reset_to_unconfirmed(self, game_id, user):
        matches = self.db.matches
        members = self.db.members
        matches.update_one(
            {"game_id": game_id},
            {
                "$set": {
                    "players.{}".format(user.id): stc.UNCONFIRMED
                }
            }
        )
        members.update_one(
            {"user_id": user.id},
            {
                "$push": {"pending": game_id}
            }
        )

    async def score(self, msg):
        if len(msg.content.split()) < 2:
            users = [msg.author]
        else:
            users = msg.mentions
        members = self.db.members
        for user in users:
            member = members.find_one({"user_id": user.id})
            if not member:
                return
            if not member["accepted"]:
                wl_ratio = 0.0
            else:
                wl_ratio = float(member["wins"])/member["accepted"]
            await self.say(
                "```Player: {}\n".format(user.name)
            +   "Points: {}\n".format(member["points"])
            +   "Wins:   {}\n".format(member["wins"])
            +   "Losses: {}\n".format(member["losses"])
            +   "Win %:  {0:.3f}```".format(100*wl_ratio)
                , msg.channel)

    async def describe(self, msg):
        matches = self.db.matches
        num_accepted_matches = matches.count({"status": stc.ACCEPTED})
        num_pending_matches = matches.count({"status": stc.PENDING})
        num_disputed_matches = matches.count({"status": stc.DISPUTED})
        members = self.db.members
        num_members = members.count()
        await self.say(
            ("There are {} registered players in the {}\n".format(
                num_members, self.league_name)
             + "Confirmed match results: {}\n".format(num_accepted_matches)
             + "Pending match results: {}\n".format(num_pending_matches)
             + "Disputed match results: {}".format(num_disputed_matches)),
            msg.channel)

    async def pending(self, msg):
        user = msg.author
        members = self.db.members
        player = members.find_one({"user_id": user.id})
        if not player:
            return
        if not player["pending"]:
            await self.say("You have no pending match records.", msg.channel)
            return
        pending_list = "List of game ids awaiting confirmation from {}:\n```{}```".format(
            user.mention,
            "\n".join(player["pending"])
        )
        await self.say(pending_list, msg.channel)
        await self.say("To check the status of a pending match, say: `!status game_id`", msg.channel)
        await self.say("To confirm a pending match, say: `!confirm game_id`", msg.channel)
        await self.say("To deny a pending match, say: `!deny game_id`", msg.channel)

    async def status(self, msg):
        if len(msg.content.split()) < 2:
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
        players = [members.find_one({"user_id": player}) for player in match["players"]]
        status_text = ("```Game id: {}\n".format(match["game_id"])
                +   "Status: {}\n".format(match["status"])
                +   "Winner: {}\n".format(winner["user"])
                +   "Players:\n{}".format(
                    "\n".join(
                        ["   {}: {}".format(
                            player["user"], match["players"][player["user_id"]]
                        ) for player in players]
                    )
                )
                +   "```"
        )
        await self.say(status_text, msg.channel)

    async def reset(self, msg):
        if not self.__is_admin(msg.author):
            return
        members = self.db.members
        matches = self.db.matches
        members.update_many({}, {
            "$set": {
                "points": 1000,
                "accepted": 0,
                "pending": [],
                "wins": 0,
                "losses": 0
            }
        })
        matches.delete_many({})
        await self.say(
            ("All registered players have had their scores reset and "
             + "all match records have been cleared."), msg.channel)

    async def top(self, msg):
        members = self.db.members
        topMembers = members.find(limit=10, sort=[('points', DESCENDING)])
        await self.say("Top Players:\n{}".format(
            '\n'.join(["{}. {} with {} points".format(ix + 1, member['user'], member['points'])
             for ix, member in enumerate(topMembers)])
        ), msg.channel)

    def __configure_admins(self, admins):
        admin_col = self.db.admins
        admin_col.insert_one({"admins": admins})

    def __add_admins(self, admins):
        admin_col = self.db.admins
        admin_col.update_one(
            {},
            {
                "$push": {
                    "admins": {"$each": admins}
                }
            }
        )

    def __rm_admins(self, admins):
        admin_col = self.db.admins
        admin_col.update_one(
            {},
            {
                "$pull": {
                    "admins": {"$in": admins}
                }
            }
        )

    def __is_admin(self, user):
        admin_col = self.db.admins
        admins = admin_col.find_one({})
        return user.name in admins["admins"]

    async def add_admin(self, msg):
        if not self.__is_admin(msg.author):
            return
        users = [user.name for user in msg.mentions]
        self.__add_admins(users)
        for user in msg.mentions:
            await self.say("{} is now an admin".format(user.mention), msg.channel)

    async def rm_admin(self, msg):
        if not self.__is_admin(msg.author):
            return
        users = [user.name for user in msg.mentions]
        self.__rm_admins(users)
        for user in msg.mentions:
            await self.say("{} is no longer an admin".format(user.mention), msg.channel)

    async def override(self, msg):
        if not self.__is_admin(msg.author):
            return
        if len(msg.content.split()) != 3:
            await self.say("Please include game id to override and the override status:\n"
                        +  "`!override game_id status`", msg.channel)
            return
        cmd, game_id, status = msg.content.split()
        matches = self.db.matches
        match = matches.find_one({"game_id": game_id})
        if not match:
            await self.say("No match with indicated game id found", msg.channel)
            return
        if match["status"] == stc.ACCEPTED:
            await self.say("Cannot override an accepted match", msg.channel)
            return
        if status.lower() not in ["accept", "remove"]:
            await self.say("Override status can only be `accept` or `remove`", msg.channel)
            return
        members = self.db.members
        for player_id in match["players"]:
            members.update_one(
                {"user_id": player_id},
                {
                    "$pull": {"pending": game_id}
                }
            )
        self.logger.info("Overriding game {} with {}".format(game_id, status))
        if status.lower() == "remove":
            matches.delete_one({"game_id": game_id})
            await self.say("Match {} has been removed".format(game_id), msg.channel)
        else:
            matches.update_one(
                {"game_id": game_id},
                {
                    "$set": {
                        "players.{}".format(p_id): stc.CONFIRMED for p_id in match["players"]
                    }
                }
            )
            await self.check_match_status(game_id, msg.channel)

    async def list_disputed(self, msg):
        if not self.__is_admin(msg.author):
            return
        matches = self.db.matches
        disputed = matches.find({"status": stc.DISPUTED})
        if not disputed.count():
            await self.say("No disputed matches found", msg.channel)
            return
        await self.say(
            "List of disputed matches:\n```{}```".format(
                "\n".join([match["game_id"] for match in disputed])), msg.channel)
        await self.say(
            "To resolve a dispute, say: `!override game_id accept/remove`",
            msg.channel)
