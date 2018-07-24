import discord
from discord.ext import commands
import re

from src import table
from src import utils

class Stats():
    def __init__(self, bot):
        self.bot = bot
        self.deck_tracking_start_date = 1529132400

    @commands.group()
    async def info(self, ctx):
        if not self.bot.is_in_server(ctx):
            return

        emsg = discord.Embed()
        pending, accepted = self.bot.db.count_matches(ctx.message.server.id)
        num_members = self.bot.db.count_members(ctx.message.server.id)
        emsg.title="{} League".format(ctx.message.server.name)
        emsg.add_field(name="Players", inline=True, value=str(num_members))
        emsg.add_field(name="Games Played", inline=True, value=str(accepted))
        emsg.add_field(name="Unconfirmed Games", inline=True, value=str(pending))
        emsg.add_field(name="Link", inline=True, value=(
            "https://discordapp.com/oauth2/authorize?client_id={}&scope=bot&permissions=0".format(self.bot.client_id)
        ))
        await self.bot.send_embed(ctx.message.channel, emsg)
        

    @commands.group()
    async def top(self, ctx):
        if not self.bot.is_in_server(ctx):
            return

        if ctx.invoked_subcommand is None:
            limit = utils.DEFAULT_LIMIT
            players = self.bot.db.find_top_players(limit, ctx.message.server.id, "points")
            emsg = discord.Embed()
            emsg.description = "\n".join(["{}. **{}** with {} points".format(ix + 1, player['user'], player['points'])
                                      for ix, player in enumerate(players)])
            await self.bot.send_embed(ctx.message.channel, emsg)

    @top.command(name='wins')
    async def _top_wins(self, ctx):
        if not self.bot.is_in_server(ctx):
            return
        
        limit = utils.get_limit(ctx)
        players = self.bot.db.find_top_players(limit, ctx.message.server.id, "wins")
        emsg = discord.Embed()
        emsg.title = "Top Players by Points"
        emsg.description = "\n".join(["{}. **{}** with {} wins".format(ix + 1, player['user'], player['wins'])
                                      for ix, player in enumerate(players)])
        await self.bot.send_embed(ctx.message.channel, emsg)


    @top.command(name='games')
    async def _top_games(self, ctx):
        if not self.bot.is_in_server(ctx):
            return
        
        limit = utils.get_limit(ctx)
        players = self.bot.db.find_top_players(limit, ctx.message.server.id, "games")
        emsg = discord.Embed()
        emsg.title = "Top Players by Games Played"
        emsg.description = "\n".join(["{}. **{}** with {} games".format(ix + 1, player['user'], player['accepted'])
                                      for ix, player in enumerate(players)])
        await self.bot.send_embed(ctx.message.channel, emsg)

    @top.command(name='points')
    async def _top_points(self, ctx):
        if not self.bot.is_in_server(ctx):
            return
        
        limit = utils.get_limit(ctx)
        players = self.bot.db.find_top_players(limit, ctx.message.server.id, "points")
        emsg = discord.Embed()
        emsg.title = "Top Players by Points"
        emsg.description = "\n".join(["{}. **{}** with {} points".format(ix + 1, player['user'], player['points'])
                                      for ix, player in enumerate(players)])
        await self.bot.send_embed(ctx.message.channel, emsg)


    @commands.group()
    async def stats(self, ctx):
        if not self.bot.is_in_server(ctx):
            return

        if ctx.invoked_subcommand is None:
            emsg = discord.Embed()
            emsg.description = "Not enough args. Enter `{}help stats` for more info."
            await self.bot.send_error(ctx.message.channel, emsg)
            return

    def _make_deck_table(self, table_title, data):
        headings = ["Deck", "Games", "Wins", "Win %", "# Pilots", "Meta %"]
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