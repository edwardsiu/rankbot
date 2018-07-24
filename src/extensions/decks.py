import discord
from discord.ext import commands
import json
import re

class Decks():
    def __init__(self, bot):
        self.bot = bot
        self._decks = {}
        self._deck_nicknames = {}
        self._load_decks()


    def _transform_deck_name(self, deck_name):
        """Convert a deck name to a canonical form. The canonical form contains only
        lower-cased letters and is sorted in alphabetical order. This allows,
        for example, Chain Veil Teferi and Teferi Chain Veil to match to the same deck."""

        sorted_name = "".join(sorted(deck_name.lower()))
        letters_only = re.search(r"([a-z]*)$", sorted_name).group()
        return letters_only


    def _load_decks(self):
        with open("config/decks.json", "r") as infile:
            self._decks = json.load(infile)
        for category in self._decks:
            category["colors"] = "".join(sorted(category["colors"].lower()))
            for deck in category["decks"]:
                for nickname in deck["nicknames"]:
                    self._deck_nicknames[self._transform_deck_name(nickname)] = deck["name"]


    @commands.command(pass_context=True)
    async def reload_decks(self, ctx):
        if not self.bot.is_admin(ctx):
            return

        self._load_decks()
        emsg = discord.Embed()
        emsg.description = "Decks reloaded"
        await self.bot.send_embed(ctx.message.channel, emsg)


    @commands.command(pass_context=True, aliases=["set-deck"])
    async def use(self, ctx):
        """Set the user's last played deck to the given deck name.
        Rogue is a placeholder deck name for an unregistered deck.
        Unrecognized deck names default to Rogue."""

        if not self.bot.is_in_server(ctx):
            return
        if not await self.bot.is_registered(ctx):
            return

        user = ctx.message.author
        emsg = discord.Embed()
        print(ctx.args)
        if not len(ctx.args):
            emsg.description = "Please include a deck name. " \
                               "Enter `{}decks` to see all tracked decks.".format(ctx.prefix)
            await self.bot.send_error(ctx.message.channel, emsg)
            return
        
        deck_name = " ".join(ctx.args)
        deck_id = self._transform_deck_name(deck_name)
        if deck_id == self._transform_deck_name("rogue"):
            official_name = "Rogue"
        elif deck_id in self._deck_nicknames:
            official_name = self._deck_nicknames[deck_id]
        else:
            official_name = "Rogue"
            self.bot.db.set_deck(user.id, "Rogue", ctx.message.server.id)
            emsg.description = "**{0}** is not a recognized deck.\n" \
                               "Defaulting to Rogue. Enter `{1}decks` " \
                               "to see all tracked decks.".format(deck_name, ctx.prefix)
            await self.bot.send_error(ctx.message.channel, emsg)
            return
        
        self.bot.db.set_deck(user.id, official_name, ctx.message.server.id)
        emsg.description = "Deck set to {} for **{}**".format(official_name, user.name)
        await self.bot.send_embed(ctx.message.channel, emsg)
        

    async def _show_decks(self, ctx, colors):
        emsg = discord.Embed()
        color_key = "".join(sorted(colors.lower()))
        for category in self._decks:
            if category["colors"] == color_key:
                emsg.title = "{} Decks".format(category["color_name"])
                category_decks = [deck["name"] for deck in category["decks"]]
                emsg.description = "\n".join(category_decks)
                await self.bot.send_embed(ctx.message.channel, emsg)
                return
        emsg.description = "No decks found for that color combination.\n" \
                           "Enter `{0}decks` for a full list of decks or " \
                           "`{0}help decks` for more usage info.".format(ctx.prefix)
        await self.bot.send_error(ctx.message.channel, emsg)


    @commands.command(pass_context=True)
    async def decks(self, ctx):
        """Show a list of all registered decks by color combination. If a color combination
        is specified, filter the results by that color combination."""

        if not len(ctx.args):
            emsg = discord.Embed()
            emsg.title = "Registered Decks"
            for category in self._decks:
                emsg.add_field(name=category["color_name"], inline=False,
                    value=("\n".join([i["name"] for i in category["decks"]])))
            await self.bot.send_embed(ctx.message.channel, emsg)
        else:
            await self._show_decks(ctx, colors=ctx.args[0])

    


def setup(bot):
    bot.add_cog(Decks(bot))