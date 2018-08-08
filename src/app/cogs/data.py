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
        for i, player in enumerate(players):
            rows.append([f"{i+1}.", player['name'], str(player[key])])
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
               "`{0}top [wins|games|score]`"
        )
    )
    @commands.guild_only()
    async def top(self, ctx):
        """Display the league leaderboard. Specify a key to sort by total wins, games, or points."""

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

    def _make_deck_tables(self, title, data, syntax=None):
        columns = ["Deck", "Meta %", "Wins", "Win %", "Pilots"]
        rows = []
        total_entries = sum([deck["entries"] for deck in data])
        for deck in data:
            # skip any untracked decks. this occurs if a game was overriden by an admin
            if deck["deck_name"] == "Unknown" or deck["entries"] < system.min_matches:
                continue
            meta_percent = 100*deck["entries"]/total_entries
            win_percent =100*deck["wins"]/deck["entries"]
            row = [
                deck["deck_name"],
                f"{meta_percent:.3g}% ({deck['entries']})",
                str(deck["wins"]),
                f"{win_percent:.3g}%",
                str(len(deck["players"]))
            ]
            rows.append(row)
        rows_per_table = 10
        _tables = [
            str(
                table.Table(title, columns, rows[i:i+rows_per_table], syntax=syntax)
            ) for i in range(0, len(rows), rows_per_table)
        ]
        return _tables
        

    @commands.command(
        brief="Display records of tracked decks",
        usage=("`{0}deckstats`\n" \
               "`{0}deckstats [wins|winrate|popularity]`"
        )
    )
    @commands.guild_only()
    async def deckstats(self, ctx, *, sort_key: str=""):
        """Displays the records of all decks tracked by the league. Data displayed includes meta share, games played, total wins, win %, and popularity. A deck is required to have at least 5 games recorded in order to show up in the stats.
        
        Games played is the number of times a deck has been logged. 
        The meta share is the percentage of time a deck is logged and is proportional to games played.
        Total wins and win % should be self-explanatory. 
        Popularity is represented by the number of unique pilots that have logged matches with the deck.

        By default, this command sorts the results by meta share. Include one of the other keys to sort by those columns instead."""

        data = utils.get_match_stats(ctx)
        if not data:
            emsg = embed.error(description="No matches found")
            await ctx.send(embed=emsg)
            return

        if not sort_key:
            sorted_data = utils.sort_by_entries(data)
            _tables = self._make_deck_tables("Deck Stats [Meta % ▼]", sorted_data, "ini")
        elif sort_key.lower() == "wins":
            sorted_data = utils.sort_by_wins(data)
            _tables = self._make_deck_tables("Deck Stats [Wins ▼]", sorted_data, "ini")
        elif sort_key.lower() == "winrate":
            sorted_data = utils.sort_by_winrate(data)
            _tables = self._make_deck_tables("Deck Stats [Win % ▼]", sorted_data, "ini")
        elif sort_key.lower() == "popularity":
            sorted_data = utils.sort_by_unique_players(data)
            _tables = self._make_deck_tables("Deck Stats [Popularity ▼]", sorted_data, "ini")
        else:
            sorted_data = utils.sort_by_entries(data)
            _tables = self._make_deck_tables("Deck Stats [Meta % ▼]", sorted_data, "ini")
        for _table in _tables:
            await ctx.send(_table)


def setup(bot):
    bot.add_cog(Data(bot))
