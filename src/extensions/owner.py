import discord
from discord.ext import commands
import hashids
import json
import random
from src import embed

class OwnerCog():
    def __init__(self, bot):
        self.bot = bot
        self.decks = self._load_deck_names("config/decks.json")
    
    # Hidden means it won't show up on the default help.
    @commands.command(name='load', hidden=True)
    @commands.is_owner()
    async def cog_load(self, ctx, *, cog: str):
        """Command which Loads a Module."""

        try:
            self.bot.load_extension(f'src.extensions.{cog}')
        except Exception as e:
            await ctx.send(embed=embed.error(description=f'**`ERROR:`** {type(e).__name__} - {e}'))
        else:
            await ctx.send(embed=embed.success(description='**`SUCCESS`**'))

    @commands.command(name='unload', hidden=True)
    @commands.is_owner()
    async def cog_unload(self, ctx, *, cog: str):
        """Command which Unloads a Module.
        Remember to use dot path. e.g: cogs.owner"""

        try:
            self.bot.unload_extension(f'src.extensions.{cog}')
        except Exception as e:
            await ctx.send(embed=embed.error(description=f'**`ERROR:`** {type(e).__name__} - {e}'))
        else:
            await ctx.send(embed=embed.success(description='**`SUCCESS`**'))

    @commands.command(name='reload', hidden=True)
    @commands.is_owner()
    async def cog_reload(self, ctx, *, cog: str):
        """Command which Reloads a Module.
        Remember to use dot path. e.g: cogs.owner"""

        try:
            self.bot.unload_extension(f'src.extensions.{cog}')
            self.bot.load_extension(f'src.extensions.{cog}')
        except Exception as e:
            await ctx.send(embed=embed.error(description=f'**`ERROR:`** {type(e).__name__} - {e}'))
        else:
            await ctx.send(embed=embed.success(description='**`SUCCESS`**'))

    @commands.group(name='add', hidden=True)
    @commands.is_owner()
    async def add_component(self, ctx):
        """Add a user, match, or deck to the bot."""

        if ctx.invoked_subcommand is None:
            await ctx.send(embed=embed.error(description=f'**`ERROR:`** Specify a component to add'))
            return

    @add_component.command(name='user', hidden=True)
    async def _add_user(self, ctx, *, user: discord.User):
        """Add a user to the database."""

        guild = ctx.message.guild
        if self.bot.db.add_member(user, guild):
            emsg = embed.msg(
                description = "Registered **{}** to the {} league".format(user.name, guild.name)
            )
        else:
            emsg = embed.error(
                description = "**{}** is already registered".format(user.name)
            )
        await ctx.send(embed=emsg)

    def _load_deck_names(self, deckfile):
        with open(deckfile, "r") as infile:
            full_list = json.load(infile)
        decks = []
        for category in full_list:
            decks += [deck["name"] for deck in category["decks"]]
        return decks

    def _get_random_deck(self):
        return self.decks[random.randint(0, len(self.decks)-1)]

    @add_component.command(name='match', hidden=True)
    async def _add_match(self, ctx):
        """Add a match to the database. Winner is the first player mentioned."""

        guild = ctx.message.guild
        players = ctx.message.mentions
        if len(players) != 4:
            await ctx.send(embed=embed.error(description=f'**`ERROR:`** Not enough players mentioned'))
            return
        winner = players[random.randint(0,3)]
        hasher = hashids.Hashids(salt="cEDH league")
        game_id = self.bot.db.get_game_id(hasher, ctx.message.id, guild)
        self.bot.db.add_match(game_id, winner, players, guild)
        for player in players:
            rand_deck = self._get_random_deck()
            self.bot.db.confirm_player(rand_deck, game_id, player, guild)
        delta = self.bot.db.check_match_status(game_id, guild)
        if delta:
            await ctx.send(embed=embed.success(description=f'**`SUCCESS:`** Added {game_id}'))
        


def setup(bot):
    bot.add_cog(OwnerCog(bot))
