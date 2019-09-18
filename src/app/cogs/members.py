from datetime import datetime
import operator
from discord.ext import commands
from app.constants import emojis
from app.utils import checks, embed, line_table, table, utils

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
                if deck_name:
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
            emsg.add_field(name="Current Deck", value=player["deck"])

    def _add_season_badges(self, emsg, player):
        badges = ""
        if player["season_gold_badges"] > 0:
            badges += emojis.first_place*player["season_gold_badges"]
        if player["season_silver_badges"] > 0:
            badges += emojis.second_place*player["season_silver_badges"]
        if player["season_bronze_badges"] > 0:
            badges += emojis.third_place*player["season_bronze_badges"]
        if len(badges) > 0:
            emsg.add_field(name="Season Badges", value=badges)

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
        self._add_season_badges(emsg, player)
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


    def _make_match_tables(self, ctx, user, matches):
        title = "{}'s Match History".format(user.name)
        headers = ["DATE", "ID", "DECK", "RESULT"]
        max_name_len = 15
        rows = []
        for match in matches:
            date = utils.short_date_from_timestamp(match['timestamp'])
            deck_name = utils.get_player_deck(user.id, match)
            deck_name = utils.shorten_deck_name(ctx, deck_name, maxlen=max_name_len)
            result = "WIN" if match['winner'] == user.id else "LOSE"
            rows.append([date, match['game_id'], deck_name, result])
        _line_table = line_table.LineTable(rows, title=title, headers=headers)
        return _line_table

    @commands.command(
        brief="Show your recent matches",
        usage=("`{0}recent`\n" \
               "`{0}recent limit [n matches]`"
        )
    )
    @commands.guild_only()
    async def recent(self, ctx, *args):
        """Show your last 10 matches. If a number is specified, show that many matches instead."""

        limit = utils.get_command_arg(args, "limit", 10)
        if (type(limit) is not int):
            await ctx.send(embed=embed.error(description=f"Limit should be a number."))
            return

        users = utils.get_target_users(ctx)
        for user in users:
            if not self.bot.db.find_member(user.id, ctx.message.guild):
                continue
            matches = self.bot.db.find_user_matches(user.id, ctx.message.guild, limit=limit)
            if not matches:
                await ctx.send(embed=embed.info(description=f"No matches found for **{user.name}**"))
                continue
            _line_table = self._make_match_tables(ctx, user, matches)
            for _table in _line_table.text:
                await ctx.send(_table)
    

    @commands.command(
        brief="Show your match history against another player",
        usage=("`{0}compare @player`\n" \
               "`{0}compare @player1 @player2`"
        )
    )
    @commands.guild_only()
    @commands.check(checks.is_registered)
    async def compare(self, ctx, *args):
        """Show player performances in pods containing only the mentioned players. If only one player is mentioned, then the default is to compare that player with the caller of the command."""

        mentions = ctx.message.mentions
        if len(mentions) < 1:
            await ctx.send(embed=embed.error(description="Mention a player to compare with"))
            return
        if len(mentions) == 1 and mentions[0].id == ctx.message.author.id:
            await ctx.send(embed=embed.error(description="Not enough players mentioned"))
            return
        if len(mentions) == 1:
            mentions.append(ctx.message.author)
        if len(mentions) > 4:
            await ctx.send(embed=embed.error(description="Too many players mentioned"))
            return
        matches = self.bot.db.find_matches(
            {"players.user_id": {"$all": [user.id for user in mentions]}},
            ctx.message.guild
        )
        matches = list(matches)
        total = len(matches)
        if not total:
            await ctx.send(embed=embed.info(description="No matches found containing all mentioned players"))
            return
        data = {user.name: 0 for user in mentions}
        for match in matches:
            winner = next((user.name for user in mentions if user.id == match['winner']), None)
            if not winner:
                continue
            if winner in data:
                data[winner] += 1
        players = ", ".join(data.keys())
        emsg = embed.info(title=f"Games Containing: {players}")
        emsg.add_field(name="Total Matches", inline=False, value=str(total))
        for user_name in data:
            wins = data[user_name]
            losses = total - wins
            percent = wins/total
            emsg.add_field(name=user_name, inline=False, value=f"{wins}-{losses}, {percent:.1%}")
        await ctx.send(embed=emsg)


def setup(bot):
    bot.add_cog(Members(bot))
