from datetime import datetime
import operator
from discord.ext import commands
from app.utils import checks, embed, table, utils

class Members():
    def __init__(self, bot):
        self.bot = bot
        self.favorite_deck_window = 10


    @commands.command(
        brief="Register to this guild's EDH league",
        usage="`{0}register`"
    )
    @commands.guild_only()
    async def register(self, ctx):
        """Register to this guild's EDH league to participate in match tracking."""
            
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
        matches = self.bot.db.find_user_matches(player_id, guild, limit=self.favorite_deck_window)
        decks = {}
        for match in matches:
            player = next((i for i in match["players"] if i["user_id"] == player_id), None)
            deck_name = player["deck"]
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
        player = self.bot.db.find_member(user.id, guild)
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


    @commands.command(
        brief="Display your league profile",
        usage=("`{0}profile`\n" \
               "`{0}profile @user1`")
    )
    @commands.guild_only()
    async def profile(self, ctx):
        """Display the profile of the mentioned player if they are registered. If no player is mentioned, show your own profile."""

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


    @commands.command(
        brief="List all pending matches",
        usage="`{0}pending`"
    )
    @commands.guild_only()
    @commands.check(checks.is_registered)
    async def pending(self, ctx):
        """Display a list of all your pending matches. Use the `remind` command instead to alert players to confirm your pending matches."""

        user = ctx.message.author
        guild = ctx.message.guild
        player = self.bot.db.find_member(user.id, guild)
        if not player["pending"]:
            emsg = embed.msg(description="You have no pending, unconfirmed matches.")
            await ctx.send(embed=emsg)
            return
        emsg = embed.msg(
            title = "Pending Matches",
            description = ", ".join(player["pending"])
        ).add_field(
            name="Actions", 
            value=f"`{ctx.prefix}status [game id]`\n`{ctx.prefix}confirm [game id]`\n`{ctx.prefix}deny [game id]`"
        )
        await ctx.send(embed=emsg)


    def _make_match_tables(self, user, matches):
        title = "{}'s Match History".format(user.name)
        columns = ["Date (UTC)", "Game Id", "Deck", "Result"]
        rows = []
        for match in matches:
            date = datetime.fromtimestamp(match["timestamp"]).strftime("%Y-%m-%d")
            player = next((i for i in match["players"] if i["user_id"] == user.id), None)
            deck_name = player["deck"] if player["deck"] else "Unknown"
            result = "WIN" if match["winner"] == user.id else "LOSE"
            row = [date, match["game_id"], deck_name, result]
            rows.append(row)
        _tables = []
        table_height = 10
        for i in range(0, len(rows), table_height):
            _tables.append(table.Table(title, columns, rows[i:i+table_height]))
        return _tables

    @commands.command(
        brief="Show your recent matches",
        usage=("`{0}recent`\n" \
               "`{0}recent [n matches]`"
        )
    )
    @commands.guild_only()
    async def recent(self, ctx, *args):
        """Show your last 10 matches. If a number is specified, show that many matches instead."""

        limit = utils.get_limit(args)

        users = utils.get_target_users(ctx)
        for user in users:
            if not self.bot.db.find_member(user.id, ctx.message.guild):
                continue
            matches = self.bot.db.find_user_matches(user.id, ctx.message.guild, limit=limit)
            if not matches:
                continue
            _tables = self._make_match_tables(user, matches)
            for _table in _tables:
                await ctx.send(str(_table))
    


def setup(bot):
    bot.add_cog(Members(bot))
