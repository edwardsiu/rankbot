import logging
import logging.handlers

import asyncio
import discord
from functools import wraps
import hashids
from pymongo import MongoClient, DESCENDING
from src.colors import *
from src import database
from src import help_cmds
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

def registered(func):
    @wraps(func)
    async def wrapper(self, msg):
        if not self.db.find_member(msg.author.id, msg.server.id):
            emsg = discord.Embed(color=RED, description=(
                "{} is not a registered player".format(msg.author.name)
            ))
            await self.send_embed(msg.channel, emsg)
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
    "players", "remind", "lfg",

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
        self.commands = commands
        self.command_token = "$"
        self.mode = stc.OPERATION
        self.hasher = hashids.Hashids(salt="cEDH league")
        self.lfgq = {}
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
        emsg = discord.Embed(description=(
            "Please create a role and assign that role as the league "
            + "admin using `set_admin [role name]`"
        ))
        await self.send_embed(server.owner, emsg)

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

    async def send_help(self, channel, embedded_msg):
        embedded_msg.color = YELLOW
        await self.send_typing(channel)
        await self.send_message(channel, embed=embedded_msg)

    async def send_error(self, channel, embedded_msg):
        embedded_msg.color = RED
        await self.send_typing(channel)
        await self.send_message(channel, embed=embedded_msg)
    
    async def send_embed(self, channel, embedded_msg, color=BLUE):
        embedded_msg.color = color
        await self.send_typing(channel)
        await self.send_message(channel, embed=embedded_msg)

    async def on_message(self, msg):
        if msg.author == self.user:
            return
        text = msg.content
        if not text or text[0] != self.command_token:
            return

        cmd = text.split()[0][1:]
        if cmd in self.commands:
            cmd_to_run = getattr(self, cmd)
            await cmd_to_run(msg)

    async def help(self, msg):
        user = msg.author
        if len(msg.content.split()) == 1:
            embedded_msg = help_cmds.user_help(self.command_token)
            await self.send_help(user, embedded_msg)
            if self.__is_admin(msg):
                embedded_msg = help_cmds.admin_help(self.command_token)
                await self.send_help(user, embedded_msg)
        else:
            tokens = msg.content.split()
            embedded_msg = help_cmds.get_help_detail(tokens[1], self.command_token)
            if embedded_msg:
                await self.send_help(msg.channel, embedded_msg)
            else:
                embed = discord.Embed(description="No help found for that command")
                await self.send_error(msg.channel, embedded_msg)

    async def addme(self, msg):
        await self.say("https://discordapp.com/oauth2/authorize?client_id={}&scope=bot&permissions=0".format(
            self.client_id), msg.channel)

    @server
    async def register(self, msg):
        # check if user is already registered
        user = msg.author
        emsg = discord.Embed()
        if self.db.add_member(user, msg.server.id):
            emsg.description = "Registered **{}** to the {} league".format(user.name, msg.server.name)
            await self.send_embed(msg.channel, emsg)
        else:
            emsg.description = "**{}** is already registered".format(user.name)
            await self.send_error(msg.channel, emsg)


    @server
    async def unregister(self, msg):
        user = msg.author
        emsg = discord.Embed()
        if not self.db.delete_member(user, msg.server.id):
            emsg.description = "**{}** is not previously registered".format(user.name)
            await self.send_error(msg.channel, emsg)
        else:
            emsg.description = "**{}** has been unregistered from the {} league".format(user.name, msg.server.name)
            await self.send_embed(msg.channel, emsg)

    @server
    async def log(self, msg):
        winner = msg.author
        losers = msg.mentions
        players = [winner] + losers
        # verify that all players are registered players
        emsg = discord.Embed()
        for user in players:
            if not self.db.find_member(user.id, msg.server.id):
                emsg.description = "**{}** is not a registered player".format(user.name)
                await self.send_error(msg.channel, emsg)
                return

        if len(losers) != 3:
            emsg.description = "There must be exactly 3 players to log a result."
            await self.send_error(msg.channel, emsg)
            return

        game_id = self.create_pending_game(msg, winner, players)
        emsg.title = "Game id: {}".format(game_id)
        emsg.description = ("Match has been logged and awaiting confirmation from "
            + "{}\n".format(" ".join([u.mention for u in losers]))
            + "Please `{0}confirm` or `{0}deny` this record.".format(self.command_token))
        await self.send_embed(msg.channel, emsg)

    def create_pending_game(self, msg, winner, players):
        game_id = self.db.get_game_id(self.hasher, msg.id, msg.server.id)
        # create a pending game record in the database for players
        self.db.add_match(game_id, winner, players, msg.server.id)
        return game_id

    @server
    @registered
    async def confirm(self, msg):
        user = msg.author
        player = self.db.find_member(user.id, msg.server.id)
        emsg = discord.Embed()
        if not player["pending"]:
            emsg.description = "You have no pending games to confirm"
            await self.send_error(msg.channel, emsg)
            return

        if len(msg.content.split()) < 2:
            game_id = player["pending"][-1]
        else:
            game_id = msg.content.split()[1]

        pending_game = self.db.find_match(game_id, msg.server.id)
        if not pending_game:
            emsg.description = "Match `{}` not found".format(game_id)
            await self.send_error(msg.channel, emsg)
            return
        if user.id not in pending_game["players"]:
            emsg.description = "Only participants can confirm a match"
            await self.send_error(msg.channel, emsg)
            return
        if pending_game["players"][user.id] == stc.UNCONFIRMED:
            self.db.confirm_player(user.id, game_id, msg.server.id)
            emsg.description = "Received confirmation from **{}**".format(user.name)
            await self.send_embed(msg.channel, emsg)
            delta = self.db.check_match_status(game_id, msg.server.id)
            if not delta:
                return
            await self.show_delta(game_id, delta, msg.channel)
        else:
            emsg.description = "You have already confirmed this match"
            await self.send_error(msg.channel, emsg)

    async def show_delta(self, game_id, delta, channel):
        emsg = discord.Embed(title="Game id: {}".format(game_id))
        emsg.description = ("Match has been accepted.\n"
            +  ", ".join(["`{0}: {1:+}`".format(i["player"], i["change"]) for i in delta]))
        await self.send_embed(channel, emsg)

    @server
    @registered
    async def deny(self, msg):
        user = msg.author
        player = self.db.find_member(user.id, msg.server.id)
        emsg = discord.Embed()
        if not player["pending"]:
            emsg.description = "You have no pending games to deny"
            await self.send_error(msg.channel, emsg)
            return

        if len(msg.content.split()) < 2:
            game_id = player["pending"][-1]
        else:
            game_id = msg.content.split()[1]

        pending_game = self.db.find_match(game_id, msg.server.id)
        if not pending_game:
            emsg.description = "Match `{}` not found".format(game_id)
            await self.send_error(msg.channel, emsg)
            return
        if user.id not in pending_game["players"]:
            emsg.description = "Only participants can deny a match"
            await self.send_error(msg.channel, emsg)
            return
        if pending_game["status"] == stc.ACCEPTED:
            emsg.description = "Cannot deny an accepted match"
            await self.send_error(msg.channel, emsg)
            return
        if pending_game["status"] == stc.PENDING:
            self.db.set_match_status(stc.DISPUTED, game_id, msg.server.id)
            if pending_game["players"][user.id] == stc.CONFIRMED:
                self.db.unconfirm_player(user.id, game_id, msg.server.id)
        admin_role = self.db.get_admin_role(msg.server)
        emsg.description = "{} Match `{}` has been marked as **disputed**".format(
            admin_role.mention, game_id)
        await self.send_error(msg.channel, emsg)

    @server
    async def score(self, msg):
        if len(msg.content.split()) < 2:
            users = [msg.author]
        else:
            users = msg.mentions
        for user in users:
            emsg = discord.Embed()
            member = self.db.find_member(user.id, msg.server.id)
            if not member:
                emsg.description = "**{}** is not a registered player".format(user.name)
                await self.send_error(msg.channel, emsg)
                continue
            if not member["accepted"]:
                win_percent = 0.0
            else:
                win_percent = 100*float(member["wins"])/member["accepted"]
            emsg.title = user.name
            emsg.add_field(name="Points", inline=True, value=str(member["points"]))
            emsg.add_field(name="Wins", inline=True, value=str(member["wins"]))
            emsg.add_field(name="Losses", inline=True, value=str(member["losses"]))
            emsg.add_field(name="Win %", inline=True,
                           value="{:.3f}%".format(win_percent))
            await self.send_embed(msg.channel, emsg, color=GREEN)

    @server
    async def describe(self, msg):
        emsg = discord.Embed()
        pending, accepted = self.db.count_matches(msg.server.id)
        num_members = self.db.count_members(msg.server.id)
        emsg = discord.Embed(title="{} League".format(msg.server.name), description=(
            "There are {} registered players in the {} league\n".format(
                num_members, msg.server.name)
            + "Total confirmed matches played: {}\n".format(accepted)
            + "Total unconfirmed matches: {}\n".format(pending)))
        await self.send_embed(msg.channel, emsg)

    @server
    async def pending(self, msg):
        user = msg.author
        emsg = discord.Embed()
        pending_matches = self.db.find_player_pending(user.id, msg.server.id)
        if not pending_matches:
            emsg.description = "You have no pending match records"
            await self.send_embed(msg.channel, emsg)
            return
        pending_list = "List of game ids awaiting confirmation:\n{}".format(
            "\n".join(["**{}**: {}".format(match["game_id"], match["players"][user.id]) for match in pending_matches])
        )
        emsg.title = "Pending Matches"
        emsg.description = ("\n".join(
            ["**{}**: {}".format(match["game_id"], match["players"][user.id]) for match in pending_matches])
            + "\n\nActions: `{0}status [game id]` `{0}confirm [game id]` `{0}deny [game id]`".format(
                self.command_token
            ))
        await self.send_embed(msg.channel, emsg)

    @server
    async def status(self, msg):
        emsg = discord.Embed()
        if len(msg.content.split()) < 2:
            emsg.description = "Please include a game id"
            await self.send_error(msg.channel, emsg)
            return
        game_id = msg.content.split()[1]
        match = self.db.find_match(game_id, msg.server.id)
        if not match:
            emsg.description = "Match `{}` not found".format(game_id)
            await self.send_error(msg.channel, emsg)
            return
        winner = self.db.find_member(match["winner"], msg.server.id)
        players = [self.db.find_member(pid, msg.server.id) for pid in match["players"]]
        emsg.title = "Game id: {}".format(game_id)
        emsg.description = (
            "Status: {}\n".format(match["status"])
            + "Winner: {}\n".format(winner["user"])
            + "Players:\n{}".format(
                "\n".join(["   {}: {}".format(u["user"], match["players"][u["user_id"]]) for u in players]))
        )
        await self.send_embed(msg.channel, emsg)

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
        emsg = discord.Embed()
        top_members = self.db.find_top_players(limit, msg.server.id)
        emsg.title = "Top Players"
        emsg.description = "\n".join(["{}. **{}** with {} points".format(ix + 1, member['user'], member['points'])
                       for ix, member in enumerate(top_members)])
        await self.send_embed(msg.channel, emsg)

    @server
    async def players(self, msg):
        members = self.db.find_all_members(msg.server.id)
        member_names = [member["user"] for member in members]
        emsg = discord.Embed(title="Registered Players")
        emsg.description = ", ".join(member_names)
        await self.send_embed(msg.channel, emsg)

    @server
    @registered
    async def remind(self, msg):
        user = msg.author
        pending = self.db.find_player_pending(user.id, msg.server.id)
        for match in pending:
            emsg = discord.Embed()
            unconfirmed = [discord.utils.get(msg.server.members, id=user_id).mention
                for user_id in match["players"] if match["players"][user_id] != stc.CONFIRMED
            ]
            emsg.title = "Game id: {}".format(match["game_id"])
            emsg.description = "{}\nPlease confirm this match by saying: `{}confirm {}`".format(
                " ".join(unconfirmed), self.command_token, match["game_id"])
            await self.send_embed(msg.channel, emsg)

    @server
    @registered
    async def lfg(self, msg):
        if msg.server.id not in self.lfgq:
            self.lfgq[msg.server.id] = []
        if msg.author not in self.lfgq[msg.server.id]:
            self.lfgq[msg.server.id].append(msg.author)
            emsg = discord.Embed(description=(
                "Added **{}** to the lfg queue\n".format(msg.author.name)
                + "LFG: {}".format(" ".join(["**{}**".format(user.name)
                                             for user in self.lfgq[msg.server.id]]))
            ))
            await self.send_embed(msg.channel, emsg)
            if len(self.lfgq[msg.server.id]) >= 4:
                emsg = discord.Embed(title="Game found", description=(
                    " ".join([user.mention for user in self.lfgq[msg.server.id]])
                ))
                self.lfgq[msg.server.id] = []
                await self.send_embed(msg.channel, emsg)
        else:
            self.lfgq[msg.server.id].remove(msg.author)
            emsg = discord.Embed(description=(
                "Removed **{}** from the lfg queue\n".format(msg.author.name)
                + "LFG: {}".format(" ".join(["**{}**".format(user.name)
                                             for user in self.lfgq[msg.server.id]]))
            ))
            await self.send_embed(msg.channel, emsg)
            

    @server
    @admin
    async def reset(self, msg):
        self.db.reset_scores(msg.server.id)
        self.db.reset_matches(msg.server.id)
        emsg = discord.Embed(description=(
            "All registered players have had their scores reset and "
             + "all match records have been cleared."))
        await self.send_embed(msg.channel, emsg)

    @server
    @admin
    async def set_admin(self, msg):
        emsg = discord.Embed()
        if not msg.role_mentions:
            emsg.description = "Please mention a role to set as league admin role"
            await self.send_error(msg.channel, emsg)
            return
        role = msg.role_mentions[0]
        self.db.set_admin_role(role.name, msg.server.id)
        emsg.description = "{} are now the league admins".format(role.mention)
        await self.send_embed(msg.channel, emsg)

    @server
    @admin
    async def override(self, msg):
        emsg = discord.Embed()
        if len(msg.content.split()) != 3:
            emsg.description = (
                "Please include the game id and override action. "
                + "See `{}help override` for more info.".format(
                    self.command_token
                ))
            await self.send_error(msg.channel, emsg)
            return
        try:
            cmd, game_id, status = msg.content.split()
        except:
            return
        match = self.db.find_match(game_id, msg.server.id)
        if not match:
            emsg.description = "Match `{}` not found".format(game_id)
            await self.send_error(msg.channel, emsg)
            return
        if match["status"] == stc.ACCEPTED:
            emsg.description = "Cannot override an accepted match"
            await self.send_error(msg.channel, emsg)
            return
        if status.lower() not in ["accept", "remove"]:
            emsg.description = "Override action can only be `accept` or `remove`"
            await self.send_error(msg.channel, emsg)
            return
        for player_id in match["players"]:
            self.db.remove_pending_match(player_id, game_id, msg.server.id)
        self.logger.info("Overriding game {} with {}".format(game_id, status))
        if status.lower() == "remove":
            self.db.delete_match(game_id, msg.server.id)
            emsg.description = "Match {} has been removed".format(game_id)
            await self.send_embed(msg.channel, emsg)
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
        emsg = discord.Embed()
        if not disputed_matches.count():
            emsg.description = "No disputed matches found"
            await self.send_embed(msg.channel, emsg)
            return
        emsg.title = "Disputed Matches"
        emsg.description = ("\n".join([match["game_id"] for match in disputed_matches])
            + "\nTo resolve a dispute, say `{}override [game id] [action]`\n".format(self.command_token)
            + "See `{}help override` for more info".format(self.command_token))
        await self.send_embed(msg.channel, emsg)

    @admin
    async def test(self, msg):
        emsg = discord.Embed()
        if self.mode == stc.OPERATION:
            self.mode = stc.TEST
            emsg.description = "Switched to testing mode"
            await self.send_embed(msg.channel, emsg)
        else:
            self.mode = stc.OPERATION
            emsg.description = "Switched to normal mode"
            await self.send_embed(msg.channel, emsg)

    @server
    @admin
    async def add_user(self, msg):
        users = msg.mentions
        if not users:
            return
        for user in users:
            emsg = discord.Embed()
            if self.db.add_member(user, msg.server.id):
                emsg.description = "Registered {} to the {} league".format(
                    user.mention, msg.server.name)
                await self.send_embed(msg.channel, emsg)
            else:
                emsg.description = "**{}** is already registered".format(user.name)
                await self.send_error(msg.channel, emsg)

    @server
    @admin
    async def rm_user(self, msg):
        users = msg.mentions
        if not users:
            return
        for user in users:
            emsg = discord.Embed()
            if self.db.delete_member(user, msg.server.id):
                emsg.description = "Unregistered **{}** from the {} league".format(
                    user.name, msg.server.name)
                await self.send_embed(msg.channel, emsg)
            else:
                emsg.description = "**{}** is not a registered player".format(user.name)
                await self.send_error(msg.channel, emsg)
