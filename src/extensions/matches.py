from datetime import datetime
import discord
from discord.ext import commands
from src import checks
from src import embed
from src.emojis import confirm_emoji, unconfirm_emoji, trophy_emoji
from src import status_codes as stc

class Matches():
    def __init__(self, bot):
        self.bot = bot


    async def _are_players_registered(self, ctx, players):
        for user in players:
            if not self.bot.db.find_member(user.id, ctx.message.guild):
                await ctx.send(embed=embed.error(description=f"**{user.name}** is not a registered player"))
                return False
        return True


    async def _has_enough_players(self, ctx, players):
        if len(players) != 4:
            await ctx.send(embed=embed.error(description="There must be exactly 3 other players to log a result"))
            return False
        return True


    @commands.command()
    @commands.guild_only()
    @commands.check(checks.is_registered)
    async def log(self, ctx):
        winner = ctx.message.author
        losers = ctx.message.mentions
        players = [winner] + losers

        if not self._are_players_registered(ctx, players):
            return
        if not self._has_enough_players(ctx, players):
            return

        game_id = self.bot.db.add_match(ctx, winner, players)
        player_mentions = " ".join([player.mention for player in players])
        emsg = embed.msg(
            title=f'Game id: {game_id}',
            description=f"Match has been logged and awaiting confirmation from {player_mentions}"
        ).set_footer(text=f"Actions: `{ctx.prefix}confirm` | `{ctx.prefix}deny`")
        await ctx.send(embed=emsg)


    async def _has_confirmed_deck(self, msg, author):
        await msg.add_reaction(msg, "👍")
        await msg.add_reaction(msg, "👎")
        def check(reaction, user):
            return user == author and str(reaction.emoji) in ["👍", "👎"]
        
        reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
        if not reaction:
            return False
        await msg.delete()
        return reaction.emoji == "👍"


    async def _confirm_deck(self, ctx, player, game_id):
        if not player["deck"]:
            emsg = embed.error(
                description=(f"No deck specified for **{ctx.message.author.name}**\n" \
                             f"Set your deck with `{ctx.prefix}use`, then type `{ctx.prefix}confirm` again")
            )
            await ctx.send(embed=emsg)
            return False
        else:
            emsg = embed.msg(
                description=f"{ctx.message.author.mention} Was **{player['deck']}** the deck you piloted?"
            )
            bot_msg = await ctx.send(embed=emsg)
            if self._has_confirmed_deck(bot_msg, ctx.message.author):
                return True
            else:
                emsg = discord.Embed()
                emsg.description = ("Set your deck with the `{}use` command, ".format(ctx.prefix)
                    + "then type `{}confirm` again.".format(ctx.prefix))
                await self.bot.send_embed(ctx.message.channel, emsg)
                return False

    async def _show_delta(self, ctx, game_id, delta):
        emsg = embed.msg(title=f"Game id: {game_id}") \
                    .add_field(name="Status", value="`ACCEPTED`") \
                    .add_field(name="Point Changes", value=(
                        "\n".join([f"`{i['player']}: {i['change']:+}`" for i in delta])
                    ))
        # next time the stat-deck command is called, it will refetch the data
        self.bot.deck_data["unsynced"] = True
        await ctx.send(embed=emsg)


    async def _get_player_confirmation(self, ctx, player, game_id):
        if not await self._confirm_deck(ctx, player, game_id):
            return
        self.bot.db.confirm_match_for_user(game_id, ctx.message.author.id, player["deck"], ctx.message.guild)
        await ctx.send(embed=embed.success(description=f"Recieved confirmation from **{ctx.message.author.name}**"))
        delta = self.bot.db.check_match_status(game_id, ctx.message.guild)
        if delta is not None:
            await self._show_delta(ctx, game_id, delta)


    @commands.command()
    @commands.guild_only()
    @commands.check(checks.is_registered)
    async def confirm(self, ctx, *, game_id: str=""):
        user = ctx.message.author
        player = self.bot.db.find_member(user.id, ctx.message.guild)
        if not len(player["pending"]):
            await ctx.send(embed=embed.msg(description="No pending matches to confirm"))
            return
        if not game_id:
            game_id = player["pending"][-1]

        pending_match = self.bot.db.find_match(game_id, ctx.message.guild)
        if not pending_match:
            await ctx.send(embed=embed.error(description=f"`{game_id}` does not exist"))
            return
        if str(user.id) not in pending_match["players"]:
            await ctx.send(embed=embed.error(description="Only participants can confirm a match"))
            return

        if pending_match["players"][str(user.id)] == stc.UNCONFIRMED:
            await self._get_player_confirmation(ctx, player, game_id)
        else:
            await ctx.send(embed=embed.error(description="You have already confirmed this match"))


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
    @commands.guild_only()
    @commands.check(checks.is_admin)
    async def accept(self, ctx):
        match = self._get_match_to_override(ctx)
        if not match:
            return
        for player_id in match["players"]:
            self.bot.db.remove_pending_match(match["game_id"], int(player_id), ctx.message.guild)
        self.bot.db.confirm_all_players(match["game_id"], match["players"], ctx.message.guild)
        delta = self.bot.db.check_match_status(
            match["game_id"], ctx.message.guild)
        if not delta:
            return
        await self._show_delta(match["game_id"], delta, ctx)
        

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
