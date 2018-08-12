import discord
from discord.ext import commands
import logging
import re

from app.constants import status_codes as stc
from app.constants import system
from app.utils import checks, embed, line_table, table, utils

class Data():
    def __init__(self, bot):
        self.bot = bot

    @commands.group(
        brief="Show summary info for the leage",
        usage="`{0}info`"
    )
    @commands.guild_only()
    async def info(self, ctx):
        """Show summary info of the league. Displays the number of registered players, the number of games recorded, and the number of pending games."""

        num_pending = self.bot.db.count_matches({"status": stc.PENDING}, ctx.message.guild)
        num_accepted = self.bot.db.count_matches({"status": stc.ACCEPTED}, ctx.message.guild)
        num_members = self.bot.db.members(ctx.message.guild).count()

        emsg = embed.info(title=f"{ctx.message.guild.name} League") \
                    .add_field(name="Players", value=str(num_members)) \
                    .add_field(name="Games Played", value=str(num_accepted)) \
                    .add_field(name="Unconfirmed Games", value=str(num_pending))
            #        .add_field(name="Link", value=(
            #f"https://discordapp.com/oauth2/authorize?" \
            #f"client_id={self.bot.client_id}&scope=bot&permissions=0")
        #)
        await ctx.send(embed=emsg)


    def _make_leaderboard_table(self, players, key, title):
        rows = []
        if key == "winrate":
            for i, player in enumerate(players):
                rows.append([
                    f"{i+1}.", 
                    player['name'], 
                    f"{100*player['wins']/player['accepted']:.3g}%"])
        else:
            for i, player in enumerate(players):
                rows.append([f"{i+1}.", player['name'], str(player[key])])
        if not rows:
            return [embed.info(description="No players found with enough matches")]
        _line_table = line_table.LineTable(rows)
        _tables = _line_table.generate()
        emsgs = []
        for _table in _tables:
            emsg = embed.msg(
                title = title,
                description = _table
            )
            emsgs.append(emsg)
        return emsgs
        

    @commands.group(
        brief="Show the leaderboard",
        usage=("`{0}top`\n" \
               "`{0}top [wins|games|score|winrate]`"
        )
    )
    @commands.guild_only()
    async def top(self, ctx):
        """Display the league leaderboard. Specify a key to sort by total wins, win %, games, or points."""

        if ctx.invoked_subcommand is None:
            limit = utils.DEFAULT_LIMIT
            players = self.bot.db.find_top_members_by("points", ctx.message.guild, limit=limit)
            emsgs = self._make_leaderboard_table(players, 'points', 'Top Players by Points')
            for emsg in emsgs:
                await ctx.send(embed=emsg)

    @top.command(
        name='wins',
        brief="Show the leaderboard for total wins",
        usage=("`{0}top wins`\n" \
               "`{0}top wins [n players]`"
        )
    )
    async def _top_wins(self, ctx, *args):
        """Display the top 10 players in the league by wins. If a number is specified, display that many players instead."""

        limit = utils.get_limit(args)
        players = self.bot.db.find_top_members_by("wins", ctx.message.guild, limit=limit)
        emsgs = self._make_leaderboard_table(players, 'wins', 'Top Players by Total Wins')
        for emsg in emsgs:
            await ctx.send(embed=emsg)

    @top.command(
        name='winrate',
        brief="Show the leaderboard for win %",
        usage=("`{0}top winrate`\n" \
               "`{0}top winrate [n players]`"
        )
    )
    async def _top_winrate(self, ctx, *args):
        """Display the top 10 players in the league by win %. If a number is specified, display that many players instead."""

        limit = utils.get_limit(args)
        players = self.bot.db.find_top_members_by("winrate", ctx.message.guild, limit=limit)
        emsgs = self._make_leaderboard_table(players, 'winrate', 'Top Players by Win %')
        for emsg in emsgs:
            await ctx.send(embed=emsg)

    @top.command(
        name='games',
        brief="Show the leaderboard for total games played",
        usage=("`{0}top games`\n" \
               "`{0}top games [n players]`"
        )
    )
    async def _top_games(self, ctx, *args):
        """Display the top 10 players in the league by games played. If a number is specified, display that many players instead."""

        limit = utils.get_limit(args)
        players = self.bot.db.find_top_members_by("accepted", ctx.message.guild, limit=limit)
        emsgs = self._make_leaderboard_table(players, 'accepted', 'Top Players by Games Played')
        for emsg in emsgs:
            await ctx.send(embed=emsg)


    @top.command(
        name='score',
        brief="Show the leaderboard for highest score",
        usage=("`{0}top score`\n" \
               "`{0}top score [n players]`"
        )
    )
    async def _top_score(self, ctx, *args):
        """Display the top 10 players in the league by points. If a number is specified, display that many players instead."""

        limit = utils.get_limit(args)
        players = self.bot.db.find_top_members_by("points", ctx.message.guild, limit=limit)
        emsgs = self._make_leaderboard_table(players, 'points', 'Top Players by Points')
        for emsg in emsgs:
            await ctx.send(embed=emsg)

    def _make_deck_tables(self, data, key):
        if key == "meta":
            title = "Deck Stats: Meta %"
            header = ["Deck Name", "#", "Meta %"]
            rows = [
                [deck['name'], str(deck['entries']), f"{100*deck[key]:.3g}%"] for deck in data
            ]
        elif key == "wins":
            title = "Deck Stats: Wins"
            header = ["Deck Name", "#", "Wins"]
            rows = [
                [deck['name'], str(deck['entries']), str(deck['wins'])] for deck in data
            ]
        elif key == "winrate":
            title = "Deck Stats: Win %"
            header = ["Deck Name", "#", "Win %"]
            rows = [
                [deck['name'], str(deck['entries']), f"{100*deck[key]:.3g}%"] for deck in data
            ]
        elif key == "popularity":
            title = "Deck Stats: Popularity"
            header = ["Deck Name", "#", "Pilots"]
            rows = [
                [deck['name'], str(deck['entries']), str(len(deck['players']))] for deck in data
            ] 

        _block_table = line_table.BlockTable(header, rows)
        _tables = _block_table.generate()
        emsgs = [
            embed.msg(title=title, description=_table) for _table in _tables
        ]
        return emsgs
        

    @commands.command(
        brief="Display records of tracked decks",
        usage=("`{0}deckstats`\n" \
               "`{0}deckstats [wins|winrate|popularity]`"
        )
    )
    @commands.guild_only()
    async def deckstats(self, ctx, *, sort_key: str=""):
        """Displays the records of all decks tracked by the league. Data displayed includes meta share, win %, wins, and popularity. A deck is required to have at least 10 games recorded in order to show up in the stats.
        
        Games played is the number of times a deck has been logged. 
        The meta share is the percentage of time a deck is logged and is proportional to games played.
        Wins and win % should be self-explanatory. 
        Popularity is represented by the number of unique pilots that have logged matches with the deck.

        By default, this command sorts the results by meta share. Include one of the other keys to sort by those columns instead."""


        # Use a line_table instead of a block_table for better mobile experience
        # Display only the selected stat and the sample size
        # Leave detail statistical analysis in the deck info command
        data = utils.get_match_stats(ctx)
        if not data:
            emsg = embed.error(description="No decks found with enough matches")
            await ctx.send(embed=emsg)
            return

        if not sort_key:
            sorted_data = utils.sort_by_entries(data)
            _tables = self._make_deck_tables(sorted_data, "meta")
        elif sort_key.lower() == "winrate":
            sorted_data = utils.sort_by_winrate(data)
            _tables = self._make_deck_tables(sorted_data, "winrate")
        elif sort_key.lower() == "wins":
            sorted_data = utils.sort_by_wins(data)
            _tables = self._make_deck_tables(sorted_data, "wins")
        elif sort_key.lower() == "popularity":
            sorted_data = utils.sort_by_unique_players(data)
            _tables = self._make_deck_tables(sorted_data, "popularity")
        else:
            sorted_data = utils.sort_by_entries(data)
            _tables = self._make_deck_tables(sorted_data, "meta")
        for _table in _tables:
            await ctx.send(embed=_table)


def setup(bot):
    bot.add_cog(Data(bot))
