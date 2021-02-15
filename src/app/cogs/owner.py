# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
import json
import random
from app.constants import color_names
from app import exceptions as err
from app.utils import checks, embed
from app.utils.deckhosts import deck_utils

class OwnerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    # Hidden means it won't show up on the default help.
    @commands.command(
        name='whoami', hidden=True,
        brief="Get the bot invite link",
        usage="`{0}whoami`"
    )
    @commands.is_owner()
    async def _whoami(self, ctx):
        """Return the bot invite link."""

        await ctx.message.author.send(f"https://discordapp.com/oauth2/authorize?" \
            f"client_id={self.bot._config['client_id']}&scope=bot&permissions=0")

    @commands.command(
        name='load', hidden=True,
        brief="Load a command module",
        usage="`{0}load [cog name]`"
    )
    @commands.is_owner()
    async def load_cog(self, ctx, *, cog: str):
        """Loads a command cog."""

        try:
            self.bot.load_extension(f'app.cogs.{cog}')
        except Exception as e:
            await ctx.send(embed=embed.error(description=f'**ERROR** - {type(e).__name__} - {e}'))
        else:
            await ctx.send(embed=embed.success(description='**SUCCESS**'))

    @commands.command(
        name='unload', hidden=True,
        brief="Unload a command module",
        usage="`{0}unload [cog name]`"
    )
    @commands.is_owner()
    async def unload_cog(self, ctx, *, cog: str):
        """Unloads a command cog."""

        try:
            self.bot.unload_extension(f'app.cogs.{cog}')
        except Exception as e:
            await ctx.send(embed=embed.error(description=f'**ERROR** - {type(e).__name__} - {e}'))
        else:
            await ctx.send(embed=embed.success(description='**SUCCESS**'))

    @commands.command(
        name='reload', hidden=True,
        brief="Reload a command module",
        usage="`{0}reload [cog name]`"
    )
    @commands.is_owner()
    async def reload_cog(self, ctx, *, cog: str):
        """Reloads a command cog."""

        try:
            self.bot.unload_extension(f'app.cogs.{cog}')
            self.bot.load_extension(f'app.cogs.{cog}')
        except Exception as e:
            await ctx.send(embed=embed.error(description=f'**ERROR** - {type(e).__name__} - {e}'))
        else:
            await ctx.send(embed=embed.success(description='**SUCCESS**'))

    @commands.group(
        name='add', hidden=True,
        brief="Add a component to the bot",
        usage=("`{0}add user`\n" \
               "`{0}add match`\n" \
               "`{0}add deck`\n"
        )
    )
    @commands.check(checks.is_super_admin)
    async def add_component(self, ctx):
        """Add a user, match, or deck to the league."""

        if ctx.invoked_subcommand is None:
            await ctx.send(embed=embed.error(description=f'**ERROR** - Specify a component to add'))
            return

    @add_component.command(
        name='user', hidden=True,
        brief="Register a user to the league",
        usage="`{0}add user @user`"
    )
    async def _add_user(self, ctx, *, user: discord.User):
        """Add a user to the database."""

        guild = ctx.message.guild
        if self.bot.db.add_member(user, guild):
            emsg = embed.msg(
                description = f"Registered **{user.name}** to the {guild.name} league"
            )
        else:
            emsg = embed.error(
                description = f"**{user.name}** is already registered"
            )
        await ctx.send(embed=emsg)

    def _load_deck_names(self, deckfile):
        with open(deckfile, "r") as infile:
            full_list = json.load(infile)
        decks = []
        for category in full_list:
            decks += [deck["name"] for deck in category["decks"]]
        return decks

    def _get_random_deck(self, deck_names):
        return deck_names[random.randint(0, len(deck_names)-1)]

    @add_component.command(
        name='match', hidden=True,
        brief="Add a match to the database",
        usage="`{0}add match @user1 @user2 @user3 @user4`"
    )
    async def _add_match(self, ctx):
        """Add a match to the database. Decks for each player are chosen at random. The winner is chosen at random. For testing purposes only."""

        guild = ctx.message.guild
        users = ctx.message.mentions
        if len(users) != 4:
            await ctx.send(embed=embed.error(description=f'**ERROR** - Not enough players mentioned'))
            return
        winner = users[random.randint(0,3)]
        
        game_id = self.bot.db.add_match(ctx, winner, users)
        deck_names = self._load_deck_names("../config/decks.json")
        for user in users:
            rand_deck = self._get_random_deck(deck_names)
            self.bot.db.confirm_match_for_user(game_id, user.id, rand_deck, guild)
        delta = self.bot.db.check_match_status(game_id, guild)
        if delta:
            await ctx.send(embed=embed.success(description=f'**SUCCESS** - Added {game_id}'))



    @add_component.command(
        name='deck', hidden=True,
        brief="Add a deck to the database",
        usage="`{0}add deck [deck name] [deck link]`"
    )
    async def _add_deck(self, ctx, *args):
        """Import a deck to the database. Information about the deck is scraped from the deck list link."""

        if len(args) < 2:
            await ctx.send(embed=embed.error(description=f'**ERROR** - Not enough args'))
            return
        if len(args) > 2:
            await ctx.send(embed=embed.error(description=f'**ERROR** - Too many args. Make sure to enclose deck names in quotes.'))
            return

        deck_name = args[0]
        deck_link = args[1]
        try:
            deck = deck_utils.extract(deck_link)
        except err.DeckNotFoundError:
            await ctx.send(embed=embed.error(description=f'**ERROR** - Failed to fetch decklist from link'))
            return
        except err.CardNotFoundError:
            await ctx.send(embed=embed.error(description=f'**ERROR** - Failed to fetch commanders from Scryfall'))
            return
        color_name = color_names.NAMES[deck["color_identity"]]
        self.bot.db.add_deck(
            deck["color_identity"],
            color_name,
            deck_name,
            [deck_name],
            [cmdr['name'] for cmdr in deck["commanders"]],
            deck_link
        )
        await ctx.send(embed=embed.success(description=f'**SUCCESS** - Imported {deck_name} to deck database'))


    @add_component.command(
        name='alias', hidden=True,
        brief="Add 1 or more aliases to a deck",
        usage="`{0}add alias [deck name] [alias 1] [alias 2] [alias 3]`"
    )
    async def _add_alias(self, ctx, *args):
        """Add one or more aliases for a deck. Names that are a multiple words must be enclosed in quotes."""

        if len(args) < 2:
            await ctx.send(embed=embed.error(description='**ERROR** - Not enough args'))
            return

        deck_name = args[0]
        aliases = args[1:]
        deck = self.bot.db.find_deck(deck_name)
        if not deck:
            await ctx.send(embed=embed.error(description='**ERROR** - Deck not found'))
            return
        response = self.bot.db.add_deck_aliases(deck_name, aliases)
        if not response:
            await ctx.send(embed=embed.error(description='**ERROR** - No aliases added'))
        else:
            await ctx.send(embed=embed.success(description=f'**SUCCESS** - New aliases added for **{deck["name"]}**'))

    @add_component.command(
        name='link', hidden=True,
        brief="Add a link to a deck",
        usage="`{0}add link [deck name] [deck link]`"
    )
    async def _add_link(self, ctx, *args):
        """Add or update a decklist link for a deck. Names that are multiple words must be enclosed in quotes."""

        if len(args) < 2:
            await ctx.send(embed=embed.error(description='**ERROR** - Not enough args'))
            return

        deck_name = args[0]
        deck_link = args[1]
        deck = self.bot.db.find_deck(deck_name)
        if not deck:
            await ctx.send(embed=embed.error(description='**ERROR** - Deck not found'))
            return

        try:
            decklist = deck_utils.extract(deck_link)
        except err.DeckNotFoundError:
            await ctx.send(embed=embed.error(description='**ERROR** - Failed to fetch deck from the given link'))
            return
        except err.CardNotFoundError:
            await ctx.send(embed=embed.error(description='**ERROR** - Failed to fetch commander from Scryfall'))
            return

        self.bot.db.add_deck_link(deck_name, deck_link)
        await ctx.send(embed=embed.success(description=f"**SUCCESS** - Added a link for **{deck['name']}**"))
        

    def _load_decks(self):
        with open("../config/decks.json", "r") as infile:
            decks = json.load(infile)
        decks_added = 0
        for category in decks:
            for deck in category["decks"]:
                decks_added += self.bot.db.add_deck(
                    category["colors"], 
                    category["color_name"],
                    deck["name"],
                    deck["aliases"],
                    deck["commanders"],
                    deck["link"]
                )
        return decks_added


    @commands.command(
        name="rescan", hidden=True,
        brief="Rescan the decks.json file",
        usage="`{0}rescan`"
    )
    @commands.is_owner()
    async def _rescan_decks(self, ctx):
        """Scans the decks.json file in config/ and imports the decks into the database."""

        decks_added = self._load_decks()
        if not decks_added:
            await ctx.send(embed=embed.info(
                description=f"Nothing new to import"))
        else:
            await ctx.send(embed=embed.success(
                description=f"**SUCCESS** - {decks_added} new deck(s) imported"))
        


def setup(bot):
    bot.add_cog(OwnerCog(bot))
