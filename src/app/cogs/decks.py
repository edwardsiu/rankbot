from discord.ext import commands
import json
import re
from app.utils import checks, embed, utils

class Decks():
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["set-deck"])
    @commands.guild_only()
    @commands.check(checks.is_registered)
    async def use(self, ctx, *, deck_name: str=""):
        """Set the user's current deck.

        Usage:
          use [deck name]

        Description:
          Deck must be a registered deck. A list of all registered decks 
          can be viewed with the `decks` command. If the desired deck is 
          not being tracked, Rogue can be used as a placeholder deck."""

        user = ctx.message.author
        action_description = f"`{ctx.prefix}decks`\n`{ctx.prefix}decks [color set]`"
        if not deck_name:
            emsg = embed.error(description="No deck specified.") \
                        .add_field(name="Actions", value=action_description)
            await ctx.send(embed=emsg)
            return
        if deck_name.lower() == "rogue":
            official_name = "Rogue"
        else:
            deck = self.bot.db.find_deck(deck_name)
            if not deck:
                emsg = embed.error(description=f"{deck_name} is not a recognized deck.") \
                            .add_field(name="Actions", value=action_description)
                await ctx.send(embed=emsg)
                return
            else:
                official_name = deck["name"]
        self.bot.db.set_deck(official_name, user, ctx.message.guild)
        await ctx.send(embed=embed.msg(description=f"Deck set to {official_name} for **{user.name}**"))


    @commands.command()
    async def decks(self, ctx, *, color: str=""):
        """Show all registered decks.
        
        Usage:
          decks
          decks [color combo]
          decks wub

        Description:
          Show all registered decks, categorized by color combination.
          If a color combination is specified in wubrg format,
          filter the results by that color combination."""

        if not color:
            emsg = embed.msg(title="Registered Decks")
            colors = utils.get_all_color_combinations()
            for color in colors:
                example = self.bot.db.find_one_deck_by_color(color)
                if not example:
                    continue
                decks = self.bot.db.find_decks_by_color(color)
                emsg.add_field(name=example["color_name"], value=(
                    "\n".join(deck["name"] for deck in decks)
                ))
            await ctx.send(embed=emsg)
        else:
            example = self.bot.db.find_one_deck_by_color(color)
            if not example:
                await ctx.send(embed=embed.error(description="No decks found with the specified color combination."))
            else:
                decks = self.bot.db.find_decks_by_color(color)
                emsg = embed.msg(
                    title=f"Registered {example['color_name']} Decks",
                    description=("\n".join(deck["name"] for deck in decks))
                )
                await ctx.send(embed=emsg)



def setup(bot):
    bot.add_cog(Decks(bot))
