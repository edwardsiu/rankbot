from datetime import datetime
from discord.ext import commands
import json
import re
import scipy.stats as st
from app import exceptions as err
from app.constants import system
from app.utils import checks, embed, line_table, scryfall, utils
from app.utils.deckhosts import deck_utils

class Decks():
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        aliases=["set-deck"],
        brief="Set your current deck",
        usage="`{0}use [deck name]`"
    )
    @commands.guild_only()
    @commands.check(checks.is_registered)
    async def use(self, ctx, *, deck_name: str=""):
        """Set your current deck to the specified deck. 
        The deck must be a registered deck. A list of all registered decks can be viewed with the `decks` command. If the desired deck is not being tracked, Rogue can be used as a placeholder."""

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


    @commands.command(
        brief="Show all registered decks",
        usage=("`{0}decks`\n" \
               "`{0}decks [color combination]`"
        )
    )
    async def decks(self, ctx, *, color: str=""):
        """Show all registered decks, categorized by color combination. If a color combination is specified in WUBRG format, filter the results by that color combination. For example, to show only Esper decks, use WUB as the color combination (order does not matter)."""

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

    async def _get_deck(self, ctx, link):
        """Helper method for deck fetching."""

        if not link:
            await ctx.send(embed=embed.error(description="Please include a link to the decklist to preview."))
            return None

        try:
            deck = deck_utils.extract(link)
        except err.DeckNotFoundError:
            await ctx.send(embed=embed.error(description="Failed to fetch decklist from the given link."))
            return None
        except err.CardNotFoundError:
            await ctx.send(embed=embed.error(description="Failed to fetch commander from Scryfall."))
            return None
        return deck
        

    @commands.command(
        brief="Display a decklist preview",
        usage="`{0}preview [deck name]`"
    )
    async def preview(self, ctx, *, deck_name: str=""):
        """Show a preview of a decklist. Supported deck hosts are tappedout.net and deckstats.net."""

        if not deck_name:
            await ctx.send(embed=embed.error(description="No deck name specified."))
            return

        deck = self.bot.db.find_deck(deck_name)
        if not deck:
            await ctx.send(embed=embed.error(
                description=f"Deck not found. Use `{ctx.prefix}decks` to see a list of decks."))
            return
        if not deck['link']:
            await ctx.send(embed=embed.info(description=f"**{deck['name']}** does not have a decklist"))
            return
        decklist = await self._get_deck(ctx, deck['link'])
        if not decklist:
            await ctx.send(embed=embed.error(description="Error fetching decklist"))
            return
        commanders = " & ".join([commander['name'] for commander in decklist['commanders']])
        image_uris = scryfall.get_image_uris(decklist['commanders'][0])
        emsg = embed.info(title=commanders) \
                    .set_thumbnail(url=image_uris['art_crop'])
        for category in decklist['decklist']:
            category_name = category['category']
            count = sum([card['count'] for card in category['cards']])
            cards = [f"{card['count']} {card['name']}" for card in category['cards']]
            emsg.add_field(name=f"{category_name} ({count})", value="\n".join(cards))
        await ctx.send(embed=emsg)

    def _make_match_row(self, match, deck_name):
        return [
            datetime.fromtimestamp(match['timestamp']).strftime("%Y-%m-%d"),
            match['game_id'],
            'WIN' if match['winning_deck'] == deck_name else 'LOSE'
        ]

    def _make_match_history_table(self, matches, deck_name):
        rows = [self._make_match_row(match, deck_name) for match in matches]
        return line_table.LineTable(rows).text[0]


    def _get_match_stats(self, ctx, matches, deck_name):
        match_stats = {}
        total_appearances = sum(
            [utils.get_appearances(match, deck_name) for match in matches])
        total_deck_wins = self.bot.db.count_matches(
            {"winning_deck": deck_name}, ctx.message.guild)
        total_matches = self.bot.db.count_matches(
            {"timestamp": {"$gt":system.deck_tracking_start_date}}, ctx.message.guild)
        if total_appearances > 1:
            meta_percent = total_appearances/(total_matches*4)
            win_percent = total_deck_wins/total_appearances
            p_value = st.binom_test(total_deck_wins, total_appearances, p=0.25, alternative="greater")
            confint = utils.confint_95(total_deck_wins, total_appearances)
            match_stats['meta'] = f"{100*meta_percent:.3g}%"
            match_stats['winrate'] = f"{100*win_percent:.3g}%, p={p_value:.3g}"
            match_stats['confint'] = f"{100*confint[0]:.3g}% - {100*confint[1]:.3g}%"
        else:
            match_stats['meta'] = "`N/A`"
            match_stats['winrate'] = "`N/A`"
            match_stats['confint'] = "`N/A`"
        match_stats['wins'] = str(total_deck_wins)
        match_stats['losses'] = str(total_appearances - total_deck_wins)
        match_stats['entries'] = str(total_appearances)
        return match_stats


    @commands.command(
        brief="Display info about a deck",
        usage="`{0}deck [deck name]`"
    )
    async def deck(self, ctx, *, deck_name: str=""):
        """Displays detail info about a registered deck."""

        if not deck_name:
            await ctx.send(embed=embed.error(description="No deck name specified"))
            return
        deck = self.bot.db.find_deck(deck_name)
        if not deck:
            await ctx.send(embed=embed.error(description=f"{deck_name} was not found"))
            return
        matches = list(self.bot.db.find_matches(
            {"players.deck": deck['name']}, ctx.message.guild))
        match_stats = self._get_match_stats(ctx, matches, deck['name'])
        if matches:
            match_history = self._make_match_history_table(
                matches[:5], deck['name'])
        else:
            match_history = "`N/A`"
        
        card = scryfall.search(deck['commanders'][0])
        image_uris = scryfall.get_image_uris(card)
        emsg = embed.info(title=f"Deck: {deck['name']}") \
                    .add_field(name="Commanders", value=("\n".join(deck['commanders']))) \
                    .add_field(name="Aliases", value=("\n".join(deck['aliases']))) \
                    .add_field(name="# Matches", value=match_stats['entries']) \
                    .add_field(name="Meta %", value=match_stats['meta']) \
                    .add_field(name="Wins", value=match_stats['wins']) \
                    .add_field(name="Losses", value=match_stats['losses']) \
                    .add_field(name="Win %", value=match_stats['winrate']) \
                    .add_field(name="95% Confidence Interval", value=match_stats['confint']) \
                    .add_field(name="Recent Matches", value=match_history) \
                    .set_thumbnail(url=image_uris['small'])
        await ctx.send(embed=emsg)

def setup(bot):
    bot.add_cog(Decks(bot))
