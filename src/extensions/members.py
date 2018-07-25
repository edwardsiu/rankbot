from datetime import datetime
import operator
import discord
from discord.ext import commands
from src.checks import is_registered
from src import embed
from src import table
from src import utils

class Members():
    def __init__(self, bot):
        self.bot = bot
        self.favorite_deck_window = 10


    @commands.command()
    @commands.guild_only()
    async def register(self, ctx):
        """Register to this guild's EDH league."""
            
        user = ctx.message.author
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


    def _get_favorite_deck(self, player, guild):
        player_id = player["user_id"]
        matches = self.bot.db.find_member_matches(player, guild, limit=self.favorite_deck_window)
        decks = {}
        for match in matches:
            if "decks" in match:
                deck_name = match["decks"][str(player_id)]
                if deck_name and deck_name in decks:
                    decks[deck_name] += 1
                else:
                    decks[deck_name] = 1
        if decks:
            return max(decks.items(), key=operator.itemgetter(1))[0]
        return None


    def _add_favorite_deck_field(self, emsg, player, guild):
        if "deck" in player and player["deck"]:
            favorite_deck = self._get_favorite_deck(player, guild)
            emsg.add_field(name="Favorite Deck", value=favorite_deck)


    def _add_last_played_deck_field(self, emsg, player):
        if "deck" in player and player["deck"]:
            emsg.add_field(name="Last Played Deck", value=player["deck"])


    def _get_profile_card(self, user, guild):
        player = self.bot.db.find_member(user, guild)
        if not player:
            return None
        win_percent = 100*player["wins"]/player["accepted"] if player["accepted"] else 0.0
        emsg = embed.info(title=user.name) \
                    .set_thumbnail(url=utils.get_avatar(user)) \
                    .add_field(name="Points", value=str(player["points"])) \
                    .add_field(name="Wins", value=str(player["wins"])) \
                    .add_field(name="Losses", value=str(player["losses"])) \
                    .add_field(name="Win %", value="{:.3f}%".format(win_percent))
        self._add_favorite_deck_field(emsg, player, guild)
        self._add_last_played_deck_field(emsg, player)
        return emsg


    @commands.command()
    @commands.guild_only()
    async def profile(self, ctx):
        """Display the profile of a registered player.
        
        Usage:
          profile
          profile @user1
        """

        users = utils.get_target_users(ctx)
        for user in users:
            profile_card = self._get_profile_card(user, ctx.message.guild)
            if not profile_card:
                emsg = embed.error(
                    description = "**{}** is not a registered player".format(user.name)
                )
                await ctx.send(embed=emsg)
                continue
            await ctx.send(embed=profile_card)


    @commands.command()
    @commands.guild_only()
    @commands.check(is_registered)
    async def pending(self, ctx):
        user = ctx.message.author
        guild = ctx.message.guild
        player = self.bot.db.find_member(user, guild)
        if not player["pending"]:
            emsg = embed.msg(description="You have no pending, unconfirmed matches.")
            await ctx.send(embed=emsg)
            return
        emsg = embed.msg(
            title = "Pending Matches",
            description = ", ".join(player["pending"])
        ).set_footer(text="Actions: {0}status [game id] | " \
                     "{0}confirm [game id] | " \
                     "{0}deny [game id]".format(ctx.prefix)
        )
        await ctx.send(embed=emsg)


    def _make_match_table(self, user, matches):
        columns = ["Date (UTC)", "Game Id", "Deck", "Result"]
        rows = []
        title = "{}'s Match History".format(user.name)
        for match in matches:
            date = datetime.fromtimestamp(match["timestamp"]).strftime("%Y-%m-%d")
            if "decks" in match and match["decks"][str(user.id)]:
                deck_name = match["decks"][str(user.id)]
            else:
                deck_name = "Unknown"
            result = "WIN" if match["winner"] == str(user.id) else "LOSE"
            row = [date, match["game_id"], deck_name, result]
            rows.append(row)
        return table.Table(title, columns, rows)

    @commands.command()
    @commands.guild_only()
    async def history(self, ctx):
        users = utils.get_target_users(ctx)
        for user in users:
            player = self.bot.db.find_member(user, ctx.message.guild)
            if not player:
                continue
            matches = self.bot.db.find_member_matches(player, ctx.message.guild, limit=5)
            if not matches:
                continue
            match_table = self._make_match_table(user, matches)
            await ctx.send(str(match_table))
    


def setup(bot):
    bot.add_cog(Members(bot))
