import discord
from discord.ext import commands
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

        emsg = embed.info(title="{} League".format(ctx.message.guild.name)) \
                    .add_field(name="Players", value=str(nmembers)) \
                    .add_field(name="Games Played", value=str(accepted)) \
                    .add_field(name="Unconfirmed Games", value=str(pending)) \
                    .add_field(name="Link", value=(
            "https://discordapp.com/oauth2/authorize?client_id={}&scope=bot&permissions=0".format(self.bot.client_id))
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
                description = "\n".join(["{}. **{}** with {} points".format(ix + 1, player['name'], player['points'])
                                      for ix, player in enumerate(players)])
            )
            await ctx.send(embed=emsg)

    @top.command(name='wins')
    async def _top_wins(self, ctx, *args):
        limit = utils.get_limit(args)
        players = self.bot.db.find_top_members_by("wins", ctx.message.guild, limit=limit)
        emsg = embed.msg(
            title = "Top Players by Total Wins",
            description = "\n".join(["{}. **{}** with {} wins".format(ix + 1, player['name'], player['wins'])
                                      for ix, player in enumerate(players)])
        )
        await ctx.send(embed=emsg)


    @top.command(name='games')
    async def _top_games(self, ctx, *args):
        limit = utils.get_limit(args)
        players = self.bot.db.find_top_members_by("accepted", ctx.message.guild, limit=limit)
        emsg = embed.msg(
            title = "Top Players by Games Played",
            description = "\n".join(["{}. **{}** with {} games".format(ix + 1, player['name'], player['accepted'])
                                      for ix, player in enumerate(players)])
        )
        await ctx.send(embed=emsg)

    @top.command(name='points')
    async def _top_points(self, ctx, *args):
        limit = utils.get_limit(args)
        players = self.bot.db.find_top_members_by("points", ctx.message.guild, limit=limit)
        emsg = embed.msg(
            title = "Top Players by Points",
            description = "\n".join(["{}. **{}** with {} points".format(ix + 1, player['name'], player['points'])
                                      for ix, player in enumerate(players)])
        )
        await ctx.send(embed=emsg)


    @commands.group()
    @commands.guild_only()
    async def stats(self, ctx):
        if ctx.invoked_subcommand is None:
            emsg = embed.error(
                description = "Not enough args. Enter `{}help stats` for more info."
            )
            await ctx.send(embed=emsg)
            return

    def _make_deck_table(self, table_title, data):
        columns = ["Deck", "Games", "Wins", "Win %", "# Pilots", "Meta %"]
        rows = []
        total_entries = 0
        for deck in data:
            total_entries += deck["entries"]
        for deck in data:
            row = [
                deck["deck_name"],
                deck["entries"],
                deck["wins"],
                "{:.3f}%".format(100*deck["wins"]/deck["entries"]),
                len(deck["players"]),
                "{:.3f}%".format(100*deck["entries"]/total_entries)
            ]
            rows.append(row)
        tables = []
        table_height = 10
        for i in range(0, len(data), table_height):
            tables.append(table.make_table(table_title, headings, rows[i:i+table_height]))
        return tables

    async def _display_deck_table(self, ctx, table_title, deck_data):
        text_tables = self._make_deck_table(table_title, deck_data)
        for text_table in text_tables:
            await self.bot.send_message(ctx.message.channel, utils.code_block(text_table))


    @stats.group()
    async def decks(self, ctx):
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
                {"timestamp": {"$gt": self.deck_tracking_start_date}}, ctx.message.server.id)
            if matches:
                self.bot.deck_data["data"] = utils.process_match_stats(matches)
            self.bot.deck_data["unsynced"] = False

        if not self.bot.deck_data["data"]:
            emsg = discord.Embed()
            emsg.description = "No matches found."
            await self.bot.send_error(ctx.message.channel, emsg)
            return

        if ctx.invoked_subcommand is None:
            sorted_data = utils.sort_by_entries(self.bot.deck_data["data"])
            await self._display_deck_table(ctx, "Deck Stats (Sorted by Meta Share)", sorted_data)
            return


    @decks.command(name='wins')
    async def _stats_decks_wins(self, ctx):
        sorted_data = utils.sort_by_wins(self.bot.deck_data["data"])
        await self._display_deck_table(ctx, "Deck Stats (Sorted by Total Wins)", sorted_data)


    @decks.command(name='winrate')
    async def _stats_decks_winrate(self, ctx):
        sorted_data = utils.sort_by_winrate(self.bot.deck_data["data"])
        await self._display_deck_table(ctx, "Deck Stats (Sorted by Win %)", sorted_data)


    @decks.command(name='popularity')
    async def _stats_decks_popularity(self, ctx):
        sorted_data = utils.sort_by_unique_players(self.bot.deck_data["data"])
        await self._display_deck_table(ctx, "Deck Stats (Sorted by Popularity)", sorted_data)


def setup(bot):
    bot.add_cog(Stats(bot))
