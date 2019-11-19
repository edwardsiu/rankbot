import asyncio
from datetime import datetime
from discord.ext import commands
from app.utils import checks, embed, line_table, table, utils
from app.constants import emojis
from app.constants import status_codes as stc

class Matches(commands.Cog):
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


    @commands.command(
        brief="Add a match to the tracking system",
        usage="`{0}log @user1 @user2 @user3`"
    )
    @commands.guild_only()
    @commands.check(checks.is_registered)
    async def log(self, ctx):
        """Add a match to the tracking system. 
        A match must have exactly 4 players. To log a match, the winner should invoke this command and mention the 3 players that lost. The match will be entered into the tracking system in PENDING state. Only after all players have confirmed the result will the match be accepted."""

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


    async def _get_player_confirmation(self, ctx, player, game_id):
        if not await self._confirm_deck(ctx, player, game_id):
            return None
        self.bot.db.confirm_match_for_user(game_id, ctx.message.author.id, player["deck"], ctx.message.guild)
        await ctx.send(embed=embed.success(description=f"Recieved confirmation from **{ctx.message.author.name}**"))
        return self.bot.db.check_match_status(game_id, ctx.message.guild)


    @commands.command(
        brief="Validate a match result",
        usage=("`{0}confirm`\n" \
               "`{0}confirm [game id]`"
        )
    )
    @commands.guild_only()
    @commands.check(checks.is_registered)
    async def confirm(self, ctx, *, game_id: str=""):
        """Validate a match result. All players, including the winner, must confirm a match. 
        By default, this command will confirm the most recent pending match by the caller. If a game_id is specified, then the specified match will be confirmed instead. 
        Confirmation is a two-step process to verify the caller's deck choice and then to verify that the match result is correct."""

        user = ctx.message.author
        member = self.bot.db.find_member(user.id, ctx.message.guild)
        if not member["pending"]:
            await ctx.send(embed=embed.info(description="No pending matches to confirm"))
            return
        if not game_id:
            game_id = member["pending"][-1]

        match = self.bot.db.find_match(game_id, ctx.message.guild)
        if not match:
            await ctx.send(embed=embed.error(description=f"`{game_id}` does not exist"))
            return
        player = next((i for i in match["players"] if i["user_id"] == user.id), None)
        if not player:
            await ctx.send(embed=embed.error(description="Only participants can confirm a match"))
            return

        if not player["confirmed"]:
            delta = await self._get_player_confirmation(ctx, member, game_id)
            if delta:
                await ctx.send(embed=embed.match_delta(game_id, delta))
        else:
            await ctx.send(embed=embed.error(description="You have already confirmed this match"))


    @commands.command(
        brief="Dispute a match result",
        usage="`{0}deny [game id]`"
    )
    @commands.guild_only()
    @commands.check(checks.is_registered)
    async def deny(self, ctx, *, game_id: str=""):
        """Dispute a match result. This will notify league admins that the match result requires attention. League admins may resolve the match by either accepting or removing it. If you created the match and there is an error (ie. mentioned the wrong players), then the `remove` command is more appropriate to undo the logged match and log the correct result."""

        user = ctx.message.author
        member = self.bot.db.find_member(user.id, ctx.message.guild)
        if not member["pending"]:
            await ctx.send(embed=embed.info(description="No pending matches to deny"))
            return
        if not game_id:
            await ctx.send(embed=embed.error(description="You must specify a game id to dispute it"))
            return

        match = self.bot.db.find_match(game_id, ctx.message.guild)
        if not match:
            await ctx.send(embed=embed.error(description=f"`{game_id}` does not exist"))
            return
        player = next((i for i in match["players"] if i["user_id"] == user.id), None)
        if not player:
            await ctx.send(embed=embed.error(description="Only participants can deny a match"))
            return

        if match["status"] == stc.ACCEPTED:
            await ctx.send(embed=embed.error(description="Accepted matches cannot be denied"))
        elif match["status"] == stc.DISPUTED:
            await ctx.send(embed=embed.info(description="This match has already been marked for review"))
        else:
            self.bot.db.set_match_status(stc.DISPUTED, game_id, ctx.message.guild)
            self.bot.db.unconfirm_match_for_user(game_id, user.id, ctx.message.guild)
            admin_role = self.bot.db.get_admin_role(ctx.message.guild)
            mention = "" if not admin_role else admin_role.mention
            await ctx.send(embed=embed.msg(
                description=f"{mention} Match `{game_id}` has been marked as **disputed**")
            )


    def _make_game_table(self, ctx, match):
        headers = ["PLAYER", "DECK", " "]
        rows = [
            [
                player['name'],
                utils.shorten_deck_name(ctx, player["deck"], maxlen=16) if player["deck"] else "N/A",
                "☑" if player["confirmed"] else "☐"
            ] for player in match['players']
        ]
        _line_table = line_table.BlockTable(rows, headers=headers, width=40)
        return _line_table.text[0]


    @commands.command(
        brief="Get details of a game",
        usage="`{0}game [game id]`"
    )
    @commands.guild_only()
    async def game(self, ctx, *, game_id: str=""):
        """Get the details of a game. Details include the date it was logged, who the players were, what decks were played, who won the match, and the confirmation status of the match."""

        if not game_id:
            await ctx.send(embed=embed.error(description="No game id specified"))
            return
        match = self.bot.db.find_match(game_id, ctx.message.guild)
        if not match:
            await ctx.send(embed=embed.error(description=f"`{game_id}` does not exist"))
            return

        winner = next((i for i in match["players"] if i["user_id"] == match["winner"]), None)
        date = datetime.fromtimestamp(match["timestamp"])
        if match["status"] == stc.ACCEPTED:
            status_symbol = emojis.accepted
        elif match["status"] == stc.PENDING:
            status_symbol = emojis.pending
        else:
            status_symbol = emojis.disputed
        emsg = embed.msg(title=f"Game id: {game_id}") \
                    .add_field(name="Date (UTC)", value=date.strftime("%Y-%m-%d")) \
                    .add_field(name="Winner", value=winner["name"]) \
                    .add_field(name="Status", value=status_symbol)

        if match['replay_link']:
            emsg.add_field(name="Replay", value=match['replay_link'])
        
        emsg.description = self._make_game_table(ctx, match)
        await ctx.send(embed=emsg)

    async def _find_user(self, user_id):
        return await self.bot.get_user_info(int(user_id))


    @commands.command(
        brief="Alert players to confirm pending matches",
        usage="`{0}remind`"
    )
    @commands.guild_only()
    @commands.check(checks.is_registered)
    async def remind(self, ctx):
        """Send an alert to each player to confirm your pending matches.
        This will pull your list of pending matches and mention all players in each match that has not yet confirmed the result."""

        member = self.bot.db.find_member(ctx.message.author.id, ctx.message.guild)
        if not member["pending"]:
            await ctx.send(embed=embed.msg(description="You have no pending matches"))
            return
        pending_matches = self.bot.db.find_matches({"game_id": {"$in": member["pending"]}}, ctx.message.guild)
        for match in pending_matches:
            unconfirmed = [
                await self.bot.get_user_info(player["user_id"]) for player in match["players"] 
                if not player["confirmed"]
            ]
            mentions = " ".join([user.mention for user in unconfirmed])
            emsg = embed.msg(
                title=f"Game id: {match['game_id']}",
                description=(f"{mentions}\n" \
                             f"Please confirm this match by saying: `{ctx.prefix}confirm {match['game_id']}`")
            )
            await ctx.send(embed=emsg)


def setup(bot):
    bot.add_cog(Matches(bot))
