import discord
from discord.ext import commands
import logging
import re

from src import checks
from src import embed
from src import status_codes as stc
from src import table
from src import utils

class Stats():
    def __init__(self, bot):
        self.bot = bot
        self.deck_tracking_start_date = 1529132400

    @commands.group()
    @commands.guild_only()
    async def info(self, ctx):
        matches_collection = self.bot.db.get_matches(ctx.message.guild.id)
        pending = matches_collection.count({"status": stc.PENDING})
        accepted = matches_collection.count({"status": stc.ACCEPTED})
        members_collection = self.bot.db.get_members(ctx.message.guild.id)
        nmembers = members_collection.count()

        emsg = embed.info(title=f"{ctx.message.guild.name} League") \
                    .add_field(name="Players", value=str(nmembers)) \
                    .add_field(name="Games Played", value=str(accepted)) \
                    .add_field(name="Unconfirmed Games", value=str(pending)) \
                    .add_field(name="Link", value=(
            f"https://discordapp.com/oauth2/authorize?" \
            f"client_id={self.bot.client_id}&scope=bot&permissions=0")
        )
        await ctx.send(embed=emsg)
        

    @commands.group()
    @commands.guild_only()
    async def top(self, ctx):
        if ctx.invoked_subcommand is None:
            limit = utils.DEFAULT_LIMIT
            players = self.bot.db.find_top_members_by("points", ctx.message.guild, limit=limit)
            emsg = embed.msg(
                title = "Top Players by Points",
                description = "\n".join([f"{ix+1}. **{player['name']}** with {player['points']} points"
                                      for ix, player in enumerate(players)])
            )
            await ctx.send(embed=emsg)

    @top.command(name='wins')
    async def _top_wins(self, ctx, *args):
        limit = utils.get_limit(args)
        players = self.bot.db.find_top_members_by("wins", ctx.message.guild, limit=limit)
        emsg = embed.msg(
            title = "Top Players by Total Wins",
            description = "\n".join([f"{ix+1}. **{player['name']}** with {player['wins']} wins"
                                      for ix, player in enumerate(players)])
        )
        await ctx.send(embed=emsg)


    @top.command(name='games')
    async def _top_games(self, ctx, *args):
        limit = utils.get_limit(args)
        players = self.bot.db.find_top_members_by("accepted", ctx.message.guild, limit=limit)
        emsg = embed.msg(
            title = "Top Players by Games Played",
            description = "\n".join([f"{ix+1}. **{player['name']}** with {player['accepted']} games"
                                      for ix, player in enumerate(players)])
        )
        await ctx.send(embed=emsg)

    @top.command(name='points')
    async def _top_points(self, ctx, *args):
        limit = utils.get_limit(args)
        players = self.bot.db.find_top_members_by("points", ctx.message.guild, limit=limit)
        emsg = embed.msg(
            title = "Top Players by Points",
            description = "\n".join([f"{ix+1}. **{player['name']}** with {player['points']} points"
                                      for ix, player in enumerate(players)])
        )
        await ctx.send(embed=emsg)


    @commands.group()
    @commands.guild_only()
    async def stat(self, ctx):
        if ctx.invoked_subcommand is None:
            emsg = embed.error(
                description = f"Not enough args. Enter `{ctx.prefix}help stat` for more info."
            )
            await ctx.send(embed=emsg)
            return

    def _make_tables(self, title, data, syntax=None):
        columns = ["Deck", "Meta %", "Wins", "Win %", "Pilots"]
        rows = []
        total_entries = sum([deck["entries"] for deck in data])
        for deck in data:
            meta_percent = 100*deck["entries"]/total_entries
            win_percent =100*deck["wins"]/deck["entries"]
            row = [
                deck["deck_name"],
                f"{meta_percent:.3f}% ({deck['entries']})",
                str(deck["wins"]),
                f"{win_percent:.3f}%",
                str(len(deck["players"]))
            ]
            rows.append(row)
        rows_per_table = 10
        _tables = [
            str(
                table.Table(title, columns, rows[i:i+rows_per_table], syntax=syntax)
            ) for i in range(0, len(data), rows_per_table)
        ]
        return _tables

    async def _send_tables(self, ctx, _tables):
        for _table in _tables:
            await ctx.send(_table)


    @stat.command()
    async def decks(self, ctx, *args):
        """Display statistics about tracked decks.
        Statistics shown are:
            1. Games played
            2. Total Wins
            3. Win %
            4. Popularity (number of unique players)
            5. Pod % (Games played/total matches)
        Default (no args): show all decks sorted by games played
        wins: show all decks sorted by total wins
        winrate: show all decks sorted by winrate
        players: show all decks sorted by popularity (unique players)"""

        if self.bot.deck_data["unsynced"]:
            matches = self.bot.db.find_matches(
                {"timestamp": {"$gt": self.deck_tracking_start_date}}, ctx.message.guild)
            if matches:
                self.bot.deck_data["data"] = utils.process_match_stats(matches)
            self.bot.deck_data["unsynced"] = False

        if not self.bot.deck_data["data"]:
            emsg = embed.error(description="No matches found")
            await ctx.send(embed=emsg)
            return

        if not args:
            sorted_data = utils.sort_by_entries(self.bot.deck_data["data"])
            _tables = self._make_tables("Deck Stats [Meta % ▼]", sorted_data, "ini")
        elif args[0].lower() == "wins":
            sorted_data = utils.sort_by_wins(self.bot.deck_data["data"])
            _tables = self._make_tables("Deck Stats [Wins ▼]", sorted_data, "ini")
        elif args[0].lower() == "winrate":
            sorted_data = utils.sort_by_winrate(self.bot.deck_data["data"])
            _tables = self._make_tables("Deck Stats [Win % ▼]", sorted_data, "ini")
        elif args[0].lower() == "popularity":
            sorted_data = utils.sort_by_unique_players(self.bot.deck_data["data"])
            _tables = self._make_tables("Deck Stats [Popularity ▼]", sorted_data, "ini")
        else:
            sorted_data = utils.sort_by_entries(self.bot.deck_data["data"])
            _tables = self._make_tables("Deck Stats [Meta % ▼]", sorted_data, "ini")
        await self._send_tables(ctx, _tables)


def setup(bot):
    bot.add_cog(Stats(bot))
