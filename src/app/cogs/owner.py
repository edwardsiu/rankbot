import discord
from discord.ext import commands
import json
import random
import re
import requests
from app.utils import embed, utils
from app.constants import color_names

class OwnerCog():
    def __init__(self, bot):
        self.bot = bot
    
    # Hidden means it won't show up on the default help.
    @commands.command(
        name='load', hidden=True,
        brief="Load a command module",
        usage="`{0}load [cog name]`"
    )
    @commands.is_owner()
    async def cog_load(self, ctx, *, cog: str):
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
    async def cog_unload(self, ctx, *, cog: str):
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
    async def cog_reload(self, ctx, *, cog: str):
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
    @commands.is_owner()
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

    def _fetch_scryfall(self, name):
        try:
            params = {"fuzzy": name}
            r = requests.get("https://api.scryfall.com/cards/named", params=params)
        except:
            return None
        else:
            return r.json()

    def _fetch_names_tappedout(self, link):
        result = re.search(r'(?<=mtg-decks/).*?(?=/)', link)
        if not result:
            return []
        slug = result.group()
        r = requests.get(f"http://tappedout.net/mtg-decks/{slug}/?fmt=markdown")
        commander_names = []
        try:
            match = re.findall(r'### Commander.*((\n[*] 1.*)+)', r.text)[0][0]
            _commanders = match.strip().split('\n')
            for _commander in _commanders:
                name = re.search(r'\[.*?\]', _commander).group()[1:-1]
                commander_names.append(name)
        except Exception as e:
            print(e)
            return []
        return commander_names

    def _get_color_identity(self, commanders):
        colors = []
        for commander in commanders:
            if commander:
                colors += commander["color_identity"]
        return utils.sort_color_str("".join(colors))


    @add_component.command(
        name='deck', hidden=True,
        brief="Add a deck to the database",
        usage="`{0}add deck [deck name] [tappedout slug]`"
    )
    async def _add_deck(self, ctx, *args):
        if len(args) < 2:
            await ctx.send(embed=embed.error(description=f'**ERROR** - Not enough args'))
            return
        if len(args) > 2:
            await ctx.send(embed=embed.error(description=f'**ERROR** - Too many args. Make sure to enclose deck names in quotes.'))
            return

        deck_name = args[0]
        deck_link = args[1]
        if self.bot.db.find_deck(deck_name):
            await ctx.send(embed=embed.error(description=f'**ERROR** - {deck_name} already exists'))
            return

        if 'tappedout' in deck_link:
            names = self._fetch_names_tappedout(deck_link)
        else:
            await ctx.send(embed=embed.error(description=f'**ERROR** - This deck hosting site is not supported'))
            return
        if not names:
            await ctx.send(embed=embed.error(description=f'**ERROR** - Failed to fetch commanders from Tappedout slug'))
            return
        commanders = [self._fetch_scryfall(name) for name in names]
        if not commanders:
            await ctx.send(embed=embed.error(description=f'**ERROR** - Failed to fetch commanders from Scryfall'))
            return
        color_identity = self._get_color_identity(commanders)
        color_name = color_names.NAMES[color_identity]
        self.bot.db.add_deck(
            color_identity,
            color_name,
            deck_name,
            [deck_name.lower()]
        )
        await ctx.send(embed=embed.success(description=f'**SUCCESS** - Imported {deck_name} to deck database'))
        

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
                    deck["nicknames"]
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
