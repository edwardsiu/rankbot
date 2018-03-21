import logging
import logging.handlers

import asyncio
import discord
from functools import wraps
import hashids
from pymongo import MongoClient, DESCENDING
from src import database
from src import status_codes as stc


def admin(func):
    @wraps(func)
    async def wrapper(self, msg):
        user = msg.author
        user_roles = [role.name for role in user.roles]
        if not self.db.is_admin(user_roles, msg.server.id) and user.id != msg.server.owner.id:
            return
        await func(self, msg)
    return wrapper


def server(func):
    @wraps(func)
    async def wrapper(self, msg):
        if not msg.server:
            return
        await func(self, msg)
    return wrapper

def test_cmd(func):
    @wraps(func)
    async def wrapper(self, msg):
        if self.mode != stc.TEST:
            return
        await func(self, msg)
    return wrapper

commands = [
    # these commands can be used in PMs
    "help", "addme", 

    # these commands must be used in a server
    "log", "register", "confirm", "deny",
    "pending", "status", "top", "score", "describe", 
    "who",

    # these commands must be used in a server and can only be called by an admin
    "set_admin", "override", "disputed", "reset",
    "add_user", "rm_user"
]

class Isperia(discord.Client):
    def __init__(self, token, config):
        super().__init__()
        self.token = token
        self.MAX_MSG_LEN = 2000
        self.client_id = config["client_id"]
        self.league_name = config["league_name"]
        self.players = config["players"]
        self.commands = commands
        self.mode = stc.OPERATION
        self.hasher = hashids.Hashids(salt="cEDH league")
        self.logger = logging.getLogger('discord')
        self.logger.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler(
            filename='discord.log', encoding='utf-8', mode='w',
            backupCount=1, maxBytes=1000000)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        self.logger.addHandler(handler)
        self.db = database.RankDB(config["mongodb_host"], config["mongodb_port"])

    def __is_admin(self, msg):
        user = msg.author
        if not msg.server:
            return False
        if user.id == msg.server.owner.id:
            return True
        user_roles = [role.name for role in user.roles]
        if self.db.is_admin(user_roles, msg.server.id):
            return True
        return False

    async def on_ready(self):
        self.logger.info('Logged in as {}'.format(self.user.name))

    async def on_server_join(self, server):
        await self.say("Please create a role and assign that role as the league "
                    +   "admin using !set_admin `role name`", server.owner)

    async def on_server_remove(self, server):
        self.db.drop_database(str(server.id))

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
        if cmd in self.commands:
            cmd_to_run = getattr(self, cmd)
            await cmd_to_run(msg)

    async def help(self, msg):
        user = msg.author
        if len(msg.content.split()) == 1:
            await self.say(
                ("Commands:\n"
                 +   "```!help        -   show command list\n\n"
                 +   "!addme       -   get invite link to add Isperia\n\n"
                 +   "!register    -   register to the {}\n\n".format(self.league_name)
                 +   "!who         -   list the names of every registered player\n\n"
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
            if self.__is_admin(msg):
                await self.say(
                    ("Admin Commands:\n"
                     +   "```!add_user    -   register the mentioned user\n\n"
                     +   "!rm_user     -   unregister the mentioned user\n\n"
                     +   "!reset       -   reset all points and remove all matches\n\n"
                     +   "!set_admin   -   set the mentioned role as league admin\n\n"
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

    @server
    async def register(self, msg):
        # check if user is already registered
        user = msg.author
        if self.db.add_member(user, msg.server.id):
            await self.say("Registered {} to the {}".format(
                user.mention, self.league_name), msg.channel)
        else:
            await self.say("{} is already registered".format(user.mention), msg.channel)

    @server
    async def unregister(self, msg):
        user = msg.author
        if not self.db.delete_member(user, msg.server.id):
            await self.say("{} is not previously registered".format(
                user.mention), msg.channel)
        else:
            await self.say("{} has been unregistered from the {}".format(
                user.mention, self.league_name), msg.channel)

    @server
    async def log(self, msg):
        winner = msg.author
        losers = msg.mentions
        players = [winner] + losers
        # verify that all players are registered players
        for user in players:
            if not self.db.find_member(user.id, msg.server.id):
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
        game_id = self.db.get_game_id(self.hasher, msg.id, msg.server.id)
        # create a pending game record in the database for players
        self.db.add_match(game_id, winner, players, msg.server.id)
        return game_id

    @server
    async def confirm(self, msg):
        user = msg.author
        player = self.db.find_member(user.id, msg.server.id)
        if not player:
            return
        if not player["pending"]:
            await self.say("You have no pending games to confirm", msg.channel)
            return

        if len(msg.content.split()) < 2:
            game_id = player["pending"][-1]
        else:
            game_id = msg.content.split()[1]

        pending_game = self.db.find_match(game_id, msg.server.id)
        if not pending_game:
            await self.say("No matching game id found", msg.channel)
            return
        if user.id not in pending_game["players"]:
            return
        if pending_game["players"][user.id] == stc.UNCONFIRMED:
            self.db.confirm_player(user.id, game_id, msg.server.id)
            await self.say("Received confirmation from {}".format(
                user.mention), msg.channel)
            delta = self.db.check_match_status(game_id, msg.server.id)
            if not delta:
                return
            await self.show_delta(game_id, delta, msg.channel)
        else:
            await self.say("You have already confirmed this match", msg.channel)

    async def show_delta(self, game_id, delta, channel):
        await self.say("Match {} has been accepted.\n".format(game_id)
                    +  "```{}```".format(", ".join(
                    ["{0}: {1:+}".format(i["player"], i["change"]) for i in delta])), channel)

    @server
    async def deny(self, msg):
        user = msg.author
        player = self.db.find_member(user.id, msg.server.id)
        if not player:
            return
        if not player["pending"]:
            await self.say("You have no pending games to confirm", msg.channel)
            return

        if len(msg.content.split()) < 2:
            game_id = player["pending"][-1]
        else:
            game_id = msg.content.split()[1]

        pending_game = self.db.find_match(game_id, msg.server.id)
        if not pending_game:
            await self.say("No matching game id found", msg.channel)
            return
        if user.id not in pending_game["players"]:
            return
        if pending_game["status"] == stc.ACCEPTED:
            await self.say("Cannot deny a confirmed match", msg.channel)
            return
        if pending_game["status"] == stc.PENDING:
            self.db.set_match_status(stc.DISPUTED, game_id, msg.server.id)
            if pending_game["players"][user.id] == stc.CONFIRMED:
                self.db.unconfirm_player(user.id, game_id, msg.server.id)
        admin_role = self.db.get_admin_role(msg.server)
        await self.say("Match `{}` has been marked as **disputed** {}".format(
                        game_id, admin_role.mention), msg.channel)

    @server
    async def score(self, msg):
        if len(msg.content.split()) < 2:
            users = [msg.author]
        else:
            users = msg.mentions
        for user in users:
            member = self.db.find_member(user.id, msg.server.id)
            if not member:
                return
            if not member["accepted"]:
                win_percent = 0.0
            else:
                win_percent = 100*float(member["wins"])/member["accepted"]
            await self.say(
                "```Player: {}\n".format(user.name)
            +   "Points: {}\n".format(member["points"])
            +   "Wins:   {}\n".format(member["wins"])
            +   "Losses: {}\n".format(member["losses"])
            +   "Win %:  {0:.3f}```".format(win_percent)
                , msg.channel)

    @server
    async def describe(self, msg):
        pending, accepted = self.db.count_matches(msg.server.id)
        num_members = self.db.count_members(msg.server.id)
        await self.say(
            ("There are {} registered players in the {}\n".format(
                num_members, self.league_name)
             + "Confirmed match results: {}\n".format(accepted)
             + "Pending match results: {}\n".format(pending)),
            msg.channel)

    @server
    async def pending(self, msg):
        user = msg.author
        player = self.db.find_member(user.id, msg.server.id)
        if not player:
            return
        if not player["pending"]:
            await self.say("You have no pending match records.", msg.channel)
            return
        pending_matches = [self.db.find_match(game_id, msg.server.id) for game_id in player["pending"]]
        pending_list = "List of game ids awaiting confirmation:\n```{}```".format(
            "\n".join(["{}: {}".format(match["game_id"], match["players"][user.id]) for match in pending_matches])
        )
        await self.say(pending_list, msg.channel)
        await self.say("To check the status of a pending match, say: `!status game_id`\n"
                    +   "To confirm a pending match, say: `!confirm game_id`\n"
                    +   "To deny a pending match, say: `!deny game_id`", msg.channel)

    @server
    async def status(self, msg):
        if len(msg.content.split()) < 2:
            await self.say("Please include a game id", msg.channel)
            return
        game_id = msg.content.split()[1]
        match = self.db.find_match(game_id, msg.server.id)
        if not match:
            await self.say("No match found for game id {}".format(game_id),
                           msg.channel)
            return
        winner = self.db.find_member(match["winner"], msg.server.id)
        players = [self.db.find_member(pid, msg.server.id) for pid in match["players"]]
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

    @server
    async def top(self, msg):
        try:
            cmd, limit = msg.content.split()
            limit = int(limit)
        except:
            limit = 10
        if limit > 32:
            channel = msg.author
        else:
            channel = msg.channel
        top_members = self.db.find_top_players(limit, msg.server.id)
        await self.say("Top Players:\n{}".format(
            '\n'.join(["{}. {} with {} points".format(ix + 1, member['user'], member['points'])
                       for ix, member in enumerate(top_members)])
        ), channel)

    @server
    async def who(self, msg):
        members = self.db.find_all_members(msg.server.id)
        await self.say("```{}```".format(
            ", ".join([member["user"] for member in members])
        ), msg.channel)

    @server
    async def lfg(self, msg):
        pass

    @server
    @admin
    async def reset(self, msg):
        self.db.reset_scores(msg.server.id)
        self.db.reset_matches(msg.server.id)
        await self.say(
            ("All registered players have had their scores reset and "
             + "all match records have been cleared."), msg.channel)

    @server
    @admin
    async def set_admin(self, msg):
        if not msg.role_mentions:
            await self.say("Please mention a role to set as league admin role", msg.channel)
            return
        role = msg.role_mentions[0]
        self.db.set_admin_role(role.name, msg.server.id)
        await self.say("{} are now the league admins".format(role.mention), msg.channel)

    @server
    @admin
    async def override(self, msg):
        if len(msg.content.split()) != 3:
            await self.say("Please include game id to override and the override status:\n"
                        +  "`!override game_id status`", msg.channel)
            return
        try:
            cmd, game_id, status = msg.content.split()
        except:
            return
        match = self.db.find_match(game_id, msg.server.id)
        if not match:
            await self.say("No match with indicated game id found", msg.channel)
            return
        if match["status"] == stc.ACCEPTED:
            await self.say("Cannot override an accepted match", msg.channel)
            return
        if status.lower() not in ["accept", "remove"]:
            await self.say("Override status can only be `accept` or `remove`", msg.channel)
            return
        for player_id in match["players"]:
            self.db.remove_pending_match(player_id, game_id, msg.server.id)
        self.logger.info("Overriding game {} with {}".format(game_id, status))
        if status.lower() == "remove":
            self.db.delete_match(game_id, msg.server.id)
            await self.say("Match {} has been removed".format(game_id), msg.channel)
        else:
            self.db.confirm_all_players(match["players"], game_id, msg.server.id)
            delta = self.db.check_match_status(game_id, msg.server.id)
            if not delta:
                return
            await self.show_delta(game_id, delta, msg.channel)

    @server
    @admin
    async def disputed(self, msg):
        disputed_matches = self.db.find_matches({"status": stc.DISPUTED}, msg.server.id)
        if not disputed_matches.count():
            await self.say("No disputed matches found", msg.channel)
            return
        await self.say(
            "List of disputed matches:\n```{}```".format(
                "\n".join([match["game_id"] for match in disputed_matches])), msg.channel)
        await self.say(
            "To resolve a dispute, say: `!override game_id accept/remove`",
            msg.channel)

    @admin
    async def test(self, msg):
        if self.mode == stc.OPERATION:
            self.mode = stc.TEST
            await self.say("Switched to testing mode", msg.channel)
        else:
            self.mode = stc.OPERATION
            await self.say("Switched to normal mode", msg.channel)

    @server
    @admin
    async def add_user(self, msg):
        users = msg.mentions
        if not users:
            return
        for user in users:
            if self.db.add_member(user, msg.server.id):
                await self.say("Registered {} to the {}".format(
                    user.mention, self.league_name), msg.channel)
            else:
                await self.say("{} is already registered".format(user.mention), msg.channel)

    @server
    @admin
    async def rm_user(self, msg):
        users = msg.mentions
        if not users:
            return
        for user in users:
            if self.db.delete_member(user, msg.server.id):
                await self.say("Unregistered {} from the {}".format(
                    user.mention, self.league_name), msg.channel)
