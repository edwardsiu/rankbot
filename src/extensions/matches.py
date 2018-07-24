from datetime import datetime
import discord
from discord.ext import commands
import hashids
from src.colors import *
from src.emojis import confirm_emoji, unconfirm_emoji, trophy_emoji
from src import status_codes as stc

class Matches():
    def __init__(self, bot):
        self.bot = bot


    def _create_pending_game(self, msg, winner, players):
        hasher = hashids.Hashids(salt="cEDH league")
        game_id = self.bot.db.get_game_id(hasher, msg.id, msg.server.id)
        # create a pending game record in the database for players
        self.bot.db.add_match(game_id, winner, players, msg.server.id)
        return game_id


    async def _are_players_registered(self, ctx, players):
        for user in players:
            if not self.bot.db.find_member(user.id, ctx.message.server.id):
                emsg = discord.Embed()
                emsg.description = "**{}** is not a registered player".format(user.name)
                await self.bot.send_error(ctx.message.channel, emsg)
                return False
        return True


    async def _has_enough_players(self, ctx, players):
        if len(players) != 4:
            emsg = discord.Embed()
            emsg.description = "There must be exactly 3 other players to log a result."
            await self.bot.send_error(ctx.message.channel, emsg)
            return False
        return True


    @commands.command()
    async def log(self, ctx):
        if not self.bot.is_in_server(ctx):
            return
        if not await self.bot.is_registered(ctx):
            return

        winner = ctx.message.author
        losers = ctx.message.mentions
        players = [winner] + losers

        if not self._are_players_registered(ctx, players):
            return
        if not self._has_enough_players(ctx, players):
            return

        game_id = self._create_pending_game(ctx.message, winner, players)
        emsg = discord.Embed()
        emsg.title = "Game id: {}".format(game_id)
        emsg.description = ("Match has been logged and awaiting confirmation from "
            + "{}\n".format(" ".join([u.mention for u in players]))
            + "Please `{0}confirm` or `{0}deny` this record.".format(ctx.prefix))
        await self.bot.send_embed(ctx.message.channel, emsg)


    async def _has_pending(self, ctx, player):
        if not player["pending"]:
            emsg = discord.Embed()
            emsg.description = "You have no pending games to confirm"
            await self.bot.send_error(ctx.message.channel, emsg)
            return False
        return True


    def _get_pending_game_id(self, ctx, player):
        game_id = player["pending"][-1] if not ctx.args else ctx.args[0]
        return game_id


    async def _has_confirmed_deck(self, msg, ctx):
        await self.bot.add_reaction(msg, "👍")
        await self.bot.add_reaction(msg, "👎")
        resp = await self.bot.wait_for_reaction(["👍", "👎"], user=ctx.message.author, timeout=60.0, message=msg)
        if not resp:
            return False
        await self.bot.delete_message(msg)
        return resp.reaction.emoji == "👍"


    async def _confirm_deck(self, game_id, player, ctx):
        emsg = discord.Embed()
        emsg.title = "Game id: {}".format(game_id)
        if "deck" not in player or not player["deck"]:
            emsg.description = ("No deck specified for **{}**. ".format(ctx.message.author.name)
                + "Set your deck with the `{}use` command, ".format(ctx.prefix)
                + "then type `{}confirm` again.".format(ctx.prefix))
            await self.bot.send_error(ctx.message.channel, emsg)
            return False
        else:
            emsg.description = ("{} Was **{}** the deck you piloted?\n".format(ctx.message.author.mention, player["deck"]))
            bot_msg = await self.bot.send_embed(ctx.message.channel, emsg)
            if self._has_confirmed_deck(bot_msg, ctx):
                return True
            else:
                emsg = discord.Embed()
                emsg.description = ("Set your deck with the `{}use` command, ".format(ctx.prefix)
                    + "then type `{}confirm` again.".format(ctx.prefix))
                await self.bot.send_embed(ctx.message.channel, emsg)
                return False


    async def _get_player_confirmation(self, game_id, player, ctx):
        if not await self._confirm_deck(game_id, player, ctx):
            return
        emsg = discord.Embed()
        self.bot.db.confirm_player(player["deck"], ctx.message.author.id, game_id, ctx.message.server.id)
        emsg.description = "Received confirmation from **{}**".format(ctx.message.author.name)
        await self.bot.send_embed(ctx.message.channel, emsg)
        delta = self.bot.db.check_match_status(game_id, ctx.message.server.id)
        if not delta:
            return
        await self._show_delta(game_id, delta, ctx.message.channel)


    @commands.command()
    async def confirm(self, ctx):
        if not self.bot.is_in_server(ctx):
            return
        if not await self.bot.is_registered(ctx):
            return

        user = ctx.message.author
        player = self.bot.db.find_member(user.id, ctx.message.server.id)
        if not self._has_pending(ctx, player):
            return

        game_id = self._get_pending_game_id(ctx, player)
        pending_game = self.bot.db.find_match(game_id, ctx.message.server.id)

        emsg = discord.Embed()
        if not pending_game:
            emsg.description = "Match `{}` not found".format(game_id)
            await self.bot.send_error(ctx.message.channel, emsg)
            return
        if user.id not in pending_game["players"]:
            emsg.description = "Only participants can confirm a match"
            await self.bot.send_error(ctx.message.channel, emsg)
            return
        if pending_game["players"][user.id] == stc.UNCONFIRMED:
            await self._get_player_confirmation(game_id, player, ctx)
        else:
            emsg.description = "You have already confirmed this match"
            await self.bot.send_error(ctx.message.channel, emsg)


    async def _show_delta(self, game_id, delta, channel):
        emsg = discord.Embed(title="Game id: {}".format(game_id))
        emsg.description = ("Match has been accepted.\n"
            +  ", ".join(["`{0}: {1:+}`".format(i["player"], i["change"]) for i in delta]))
        # next time the stat-deck command is called, it will refetch the data
        self.bot.deck_data["unsynced"] = True
        await self.bot.send_embed(channel, emsg)


    @commands.command()
    async def deny(self, ctx):
        if not self.bot.is_in_server(ctx):
            return
        if not await self.bot.is_registered(ctx):
            return
        
        user = ctx.message.author
        player = self.bot.db.find_member(user.id, ctx.message.server.id)
        if not self._has_pending(ctx, player):
            return

        game_id = self._get_pending_game_id(ctx, player)
        pending_game = self.bot.db.find_match(game_id, ctx.message.server.id)

        emsg = discord.Embed()
        if not pending_game:
            emsg.description = "Match `{}` not found".format(game_id)
            await self.bot.send_error(ctx.message.channel, emsg)
            return
        if user.id not in pending_game["players"]:
            emsg.description = "Only participants can deny a match"
            await self.bot.send_error(ctx.message.channel, emsg)
            return
        if pending_game["status"] == stc.ACCEPTED:
            emsg.description = "Cannot deny an accepted match"
            await self.bot.send_error(ctx.message.channel, emsg)
            return
        if pending_game["status"] == stc.PENDING:
            self.bot.db.set_match_status(stc.DISPUTED, game_id, ctx.message.server.id)
            if pending_game["players"][user.id] == stc.CONFIRMED:
                self.bot.db.unconfirm_player(user.id, game_id, ctx.message.server.id)

        admin_role = self.bot.db.get_admin_role(ctx.message.server)
        mention = "" if not admin_role else admin_role.mention
        emsg.description = "{} Match `{}` has been marked as **disputed**".format(
            mention, game_id)
        await self.bot.send_error(ctx.message.channel, emsg)

    
    async def _get_match_to_override(self, ctx):
        emsg = discord.Embed()
        if not ctx.args:
            emsg.description = "Please include a game id to override. " \
                               "See `{}help {} for more info.".format(
                                   ctx.prefix, ctx.command)
            await self.bot.send_error(ctx.message.channel, emsg)
            return None
        game_id = ctx.args[0]
        match = self.bot.db.find_match(game_id, ctx.message.server.id)
        if not match:
            emsg.description = "Failed to find match with game id `{}`".format(game_id)
            await self.bot.send_error(ctx.message.channel, emsg)
            return None
        if match["status"] == stc.ACCEPTED:
            emsg.description = "Cannot override an accepted match"
            await self.bot.send_error(ctx.message.channel, emsg)
            return None
        return match


    @commands.command()
    async def accept(self, ctx):
        if not self.bot.is_in_server(ctx):
            return
        if not self.bot.is_admin(ctx):
            return

        match = self._get_match_to_override(ctx)
        if not match:
            return
        for player_id in match["players"]:
            self.bot.db.remove_pending_match(player_id, match["game_id"], ctx.message.server.id)
        self.bot.db.confirm_all_players(match["players"], match["game_id"], ctx.message.server.id)
        delta = self.bot.db.check_match_status(
            match["game_id"], ctx.message.server.id)
        if not delta:
            return
        await self._show_delta(match["game_id"], delta, ctx.message.channel)
        

    @commands.command()
    async def reject(self, ctx):
        if not self.bot.is_in_server(ctx):
            return
        if not self.bot.is_admin(ctx):
            return

        match = self._get_match_to_override(ctx)
        if not match:
            return
        for player_id in match["players"]:
            self.bot.db.remove_pending_match(player_id, match["game_id"], ctx.message.server.id)
        self.bot.db.delete_match(match["game_id"], ctx.message.server.id)
        emsg = discord.Embed()
        emsg.description = "Match `{}` has been removed".format(match["game_id"])
        await self.bot.send_embed(ctx.message.channel, emsg)


    @commands.command()
    @commands.guild_only()
    async def status(self, ctx, *, game_id: str):
        emsg = discord.Embed()
        #if not ctx.args:
        #    emsg.description = "Please include a game id"
        #    await self.bot.send_error(ctx.message.channel, emsg)
        #    return
        #game_id = ctx.args[0]
        match = self.bot.db.find_match(game_id, ctx.message.guild.id)
        if not match:
            emsg.description = "Match `{}` not found".format(game_id)
            emsg.color = C_ERR
            #await self.bot.send_error(ctx.message.channel, emsg)
            await ctx.send(embed=emsg)
            return
        winner = self.bot.db.find_member(match["winner"], ctx.message.guild.id)
        players = [self.bot.db.find_member(pid, ctx.message.guild.id) for pid in match["players"]]
        emsg.title = "Game id: {}".format(game_id)
        date = datetime.fromtimestamp(match["timestamp"])
        emoji_type = {stc.CONFIRMED: confirm_emoji, stc.UNCONFIRMED: unconfirm_emoji}
        player_strings = []
        for player in players:
            if "decks" in match and match["decks"][player["user_id"]]:
                deck_name = match["decks"][player["user_id"]]
            else:
                deck_name = "???"
            status_msg = u"{} {}: {}".format(emoji_type[match["players"][player["user_id"]]], 
                player["user"], deck_name)
            if player["user_id"] == winner["user_id"]:
                status_msg += u" " + trophy_emoji
            player_strings.append(status_msg)
        emsg.add_field(name="Date", inline=True, value=date.strftime("%Y-%m-%d"))
        emsg.add_field(name="Status", inline=True, value=match["status"])
        emsg.add_field(name="Players", inline=True, value=("\n".join(player_strings)))
        #await self.bot.send_embed(ctx.message.channel, emsg)
        emsg.color = C_OK
        await ctx.send(embed=emsg)


    @commands.command()
    async def remind(self, ctx):
        if not self.bot.is_in_server(ctx):
            return
        if not await self.bot.is_registered(ctx):
            return

        user = ctx.message.author
        pending_matches = self.bot.db.find_player_pending(user.id, ctx.message.server.id)
        for match in pending_matches:
            emsg = discord.Embed()
            unconfirmed = [discord.utils.get(ctx.message.server.members, id=user_id).mention
                for user_id in match["players"] if match["players"][user_id] != stc.CONFIRMED
            ]
            emsg.title = "Game id: {}".format(match["game_id"])
            emsg.description = "{}\nPlease confirm this match by saying: `{}confirm {}`".format(
                " ".join(unconfirmed), ctx.prefix, match["game_id"])
            await self.bot.send_embed(ctx.message.channel, emsg)

    
    @commands.command()
    async def disputed(self, ctx):
        if not self.bot.is_in_server(ctx):
            return
        if not self.bot.is_admin(ctx):
            return

        disputed_matches = self.bot.db.find_matches({"status": stc.DISPUTED}, ctx.message.server.id)
        emsg = discord.Embed()
        if not disputed_matches.count():
            emsg.description = "No disputed matches found"
            await self.bot.send_embed(ctx.message.channel, emsg)
            return
        emsg.title = "Disputed Matches"
        emsg.description = ("\n".join([match["game_id"] for match in disputed_matches])
            + "\nUse `{0}accept [game id]` or `{0}reject [game id]` to resolve a dispute.".format(
                ctx.prefix
            ))
        await self.bot.send_embed(ctx.message.channel, emsg)


def setup(bot):
    bot.add_cog(Matches(bot))