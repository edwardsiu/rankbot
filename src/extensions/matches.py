import asyncio
from datetime import datetime
import discord
from discord.ext import commands
from src import checks
from src import embed
from src import emojis
from src import status_codes as stc
from src import table

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

        if not await self._are_players_registered(ctx, players):
            return
        if not await self._has_enough_players(ctx, players):
            return

        game_id = self.bot.db.add_match(ctx, winner, players)
        player_mentions = " ".join([player.mention for player in players])
        emsg = embed.msg(
            title=f'Game id: {game_id}',
            description=f"Match has been logged and awaiting confirmation from {player_mentions}"
        ).add_field(name="Actions", value=f"`{ctx.prefix}confirm` | `{ctx.prefix}deny`")
        await ctx.send(embed=emsg)


    async def _has_confirmed_deck(self, bot_msg, ctx):
        await bot_msg.add_reaction(emojis.thumbs_up)
        await bot_msg.add_reaction(emojis.thumbs_down)
        def check(reaction, user):
            return user == ctx.message.author and str(reaction.emoji) in (emojis.thumbs_up, emojis.thumbs_down)
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await bot_msg.delete()
            return False
        else:
            return reaction.emoji == emojis.thumbs_up


    async def _confirm_deck(self, ctx, player, game_id):
        if not player["deck"]:
            emsg = embed.error(
                description=(f"No deck specified for **{ctx.message.author.name}**\n" \
                             f"Set your deck with `{ctx.prefix}use`, then type `{ctx.prefix}confirm` again")
            )
            await ctx.send(embed=emsg)
            return False

        emsg = embed.msg(
            description=f"{ctx.message.author.mention} Was **{player['deck']}** the deck you piloted?"
        )
        bot_msg = await ctx.send(embed=emsg)
        
        if await self._has_confirmed_deck(bot_msg, ctx):
            return True

        await ctx.send(embed=embed.error(
            description=f"Set your deck with the `{ctx.prefix}use` command, then type `{ctx.prefix}confirm` again")
        )
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
        if delta:
            await self._show_delta(ctx, game_id, delta)


    @commands.command()
    @commands.guild_only()
    @commands.check(checks.is_registered)
    async def confirm(self, ctx, *, game_id: str=""):
        user = ctx.message.author
        player = self.bot.db.find_member(user.id, ctx.message.guild)
        if not player["pending"]:
            await ctx.send(embed=embed.info(description="No pending matches to confirm"))
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
    @commands.guild_only()
    @commands.check(checks.is_registered)
    async def deny(self, ctx, *, game_id: str=""):
        user = ctx.message.author
        player = self.bot.db.find_member(user.id, ctx.message.guild)
        if not player["pending"]:
            await ctx.send(embed=embed.info(description="No pending matches to deny"))
            return
        if not game_id:
            game_id = player["pending"][-1]

        pending_match = self.bot.db.find_match(game_id, ctx.message.guild)
        if not pending_match:
            await ctx.send(embed=embed.error(description=f"`{game_id}` does not exist"))
            return
        if str(user.id) not in pending_match["players"]:
            await ctx.send(embed=embed.error(description="Only participants can deny a match"))
            return

        if pending_match["status"] == stc.ACCEPTED:
            await ctx.send(embed=embed.error(description="Accepted matches cannot be denied"))
        elif pending_match["status"] == stc.DISPUTED:
            await ctx.send(embed=embed.info(description="This match has already been marked for review"))
        else:
            self.bot.db.set_match_status(stc.DISPUTED, game_id, ctx.message.guild)
            if pending_match["players"][str(user.id)] == stc.CONFIRMED:
                self.bot.db.unconfirm_match_for_user(game_id, user.id, ctx.message.guild)
            admin_role = self.bot.db.get_admin_role(ctx.message.guild)
            mention = "" if not admin_role else admin_role.mention
            await ctx.send(embed=embed.msg(
                description=f"{mention} Match `{game_id}` has been marked as **disputed**")
            )


    @commands.command()
    @commands.guild_only()
    @commands.check(checks.is_admin)
    async def accept(self, ctx, *, game_id: str=""):
        if not game_id:
            await ctx.send(embed=embed.error(description="No game id specified"))
            return
        match = self.bot.db.find_match(game_id, ctx.message.guild)
        if not match:
            await ctx.send(embed=embed.error(description=f"`{game_id}` does not exist"))
            return
        if match["status"] == stc.ACCEPTED:
            return

        self.bot.db.confirm_match_for_users(game_id, match["players"].keys(), ctx.message.guild)
        delta = self.bot.db.check_match_status(game_id, ctx.message.guild)
        if delta:
            await self._show_delta(ctx, game_id, delta)
        

    @commands.command()
    @commands.guild_only()
    @commands.check(checks.is_admin)
    async def reject(self, ctx, *, game_id: str=""):
        if not game_id:
            await ctx.send(embed=embed.error(description="No game id specified"))
            return
        match = self.bot.db.find_match(game_id, ctx.message.guild)
        if not match:
            await ctx.send(embed=embed.error(description=f"`{game_id}` does not exist"))
            return
        if match["status"] == stc.ACCEPTED:
            await ctx.send(embed=embed.error(description="Cannot override an accepted match"))
            return

        self.bot.db.delete_match(game_id, ctx.message.guild)
        await ctx.send(embed=embed.msg(description=f"`{game_id}` has been removed"))

    def _make_game_table(self, players, match):
        columns = ["Player", "Deck", "Status"]
        rows = []
        for player in players:
            user_id = str(player["user_id"])
            if match["decks"][user_id]:
                deck_name = match["decks"][user_id]
            else:
                deck_name = "???"
            status = " ☑" if match["players"][user_id] == stc.CONFIRMED else " ☐"
            rows.append([player["name"], deck_name, status])
        _table = table.Table(columns=columns, rows=rows, max_width=45)
        return str(_table)


    @commands.command()
    @commands.guild_only()
    async def game(self, ctx, *, game_id: str=""):
        if not game_id:
            await ctx.send(embed=embed.error(description="No game id specified"))
            return
        match = self.bot.db.find_match(game_id, ctx.message.guild)
        if not match:
            await ctx.send(embed=embed.error(description=f"`{game_id}` does not exist"))
            return
        winner = self.bot.db.find_member(match["winner"], ctx.message.guild)
        user_ids = [int(user_id) for user_id in match["players"]]
        players = self.bot.db.find_members({"user_id": {"$in": user_ids}}, ctx.message.guild)
        date = datetime.fromtimestamp(match["timestamp"])
        if match["status"] == stc.ACCEPTED:
            status_symbol = emojis.accepted
        elif match["status"] == stc.PENDING:
            status_symbol = emojis.pending
        else:
            status_symbol = emojis.disputed
        emsg = embed.msg(title=f"Game id: {game_id}") \
                    .add_field(name="Date", value=date.strftime("%Y-%m-%d")) \
                    .add_field(name="Winner", value=winner["name"]) \
                    .add_field(name="Status", value=status_symbol)
        
        emsg.description = self._make_game_table(players, match)
        await ctx.send(embed=emsg)

    async def _find_user(self, user_id):
        return await self.bot.get_user_info(int(user_id))


    @commands.command()
    @commands.guild_only()
    @commands.check(checks.is_registered)
    async def remind(self, ctx):
        member = self.bot.db.find_member(ctx.message.author.id, ctx.message.guild)
        if not member["pending"]:
            await ctx.send(embed=embed.msg(description="You have no pending matches"))
            return
        pending_matches = self.bot.db.find_matches({"game_id": {"$in": member["pending"]}}, ctx.message.guild)
        for match in pending_matches:
            emsg = discord.Embed()
            unconfirmed = [
                await self.bot.get_user_info(int(user_id)) for user_id in match["players"] 
                if match["players"][user_id] == stc.UNCONFIRMED
            ]
            mentions = " ".join([user.mention for user in unconfirmed])
            emsg = embed.msg(
                title=f"Game id: {match['game_id']}",
                description=(f"{mentions}\n" \
                             f"Please confirm this match by saying: `{ctx.prefix}confirm {match['game_id']}`")
            )
            await ctx.send(embed=emsg)

    def _get_game_ids_list(self, matches):
        if not matches.count():
            return "N/A"
        return "\n".join([f"`{match['game_id']}`" for match in matches])

    
    @commands.command()
    @commands.guild_only()
    @commands.check(checks.is_admin)
    async def matches(self, ctx):
        disputed_matches = self.bot.db.find_matches({"status": stc.DISPUTED}, ctx.message.guild)
        pending_matches = self.bot.db.find_matches({"status": stc.PENDING}, ctx.message.guild)
        disputed = self._get_game_ids_list(disputed_matches)
        pending = self._get_game_ids_list(pending_matches)
        emsg = embed.info(title="Pending and Disputed Matches") \
                    .add_field(name="Disputed", value=disputed) \
                    .add_field(name="Pending", value=pending) \
                    .add_field(name="Actions", 
                        value=f"`{ctx.prefix}game [game id]`\n`{ctx.prefix}accept [game id]`\n`{ctx.prefix}reject [game id]`")
        await ctx.send(embed=emsg)


def setup(bot):
    bot.add_cog(Matches(bot))
