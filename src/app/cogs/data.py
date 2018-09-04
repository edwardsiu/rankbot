import discord
from discord.ext import commands
import logging
import re

from app.constants import status_codes as stc
from app.constants import system
from app.utils import checks, embed, line_table, table, utils

class Data():
    def __init__(self, bot):
        self.bot = bot

    @commands.group(
        brief="Show summary info for the leage",
        usage="`{0}info`"
    )
    @commands.guild_only()
    async def info(self, ctx):
        """Show summary info of the league. Displays the number of registered players, the number of games recorded, and the number of pending games."""

        num_pending = self.bot.db.count_matches({"status": stc.PENDING}, ctx.message.guild)
        num_accepted = self.bot.db.count_matches({"status": stc.ACCEPTED}, ctx.message.guild)
        num_members = self.bot.db.members(ctx.message.guild).count()

        emsg = embed.info(title=f"{ctx.message.guild.name} League") \
                    .add_field(name="Players", value=str(num_members)) \
                    .add_field(name="Games Played", value=str(num_accepted)) \
                    .add_field(name="Unconfirmed Games", value=str(num_pending))
            #        .add_field(name="Donate", inline=False, value=f"[PayPal]({self.bot._config['donation_link']})")
        #)
        await ctx.send(embed=emsg)


    def _make_leaderboard_table(self, players, key, title):
        rows = []
        if key == "winrate":
            for i, player in enumerate(players):
                rows.append([
                    f"{i+1}.", 
                    player['name'], 
                    f"{100*player['wins']/player['accepted']:.3g}%"])
        else:
            for i, player in enumerate(players):
                rows.append([f"{i+1}.", player['name'], str(player[key])])
        if not rows:
            return [embed.info(description="No players found with enough matches")]
        return line_table.LineTable(rows, title=title)
        

    @commands.group(
        brief="Show the leaderboard",
        usage=("`{0}top`\n" \
               "`{0}top [wins|games|score|winrate]`"
        )
    )
    @commands.guild_only()
    async def top(self, ctx):
        """Display the league leaderboard. Specify a key to sort by total wins, win %, games, or points."""

        if ctx.invoked_subcommand is None:
            limit = utils.DEFAULT_LIMIT
            players = self.bot.db.find_top_members_by("points", ctx.message.guild, limit=limit)
            _tables = self._make_leaderboard_table(players, 'points', 'Top Players by Points')
            for _table in _tables.text:
                await ctx.send(_table)

    @top.command(
        name='wins',
        brief="Show the leaderboard for total wins",
        usage=("`{0}top wins`\n" \
               "`{0}top wins [n players]`"
        )
    )
    async def _top_wins(self, ctx, *args):
        """Display the top 10 players in the league by wins. If a number is specified, display that many players instead."""

        limit = utils.get_limit(args)
        players = self.bot.db.find_top_members_by("wins", ctx.message.guild, limit=limit)
        _tables = self._make_leaderboard_table(players, 'wins', 'Top Players by Total Wins')
        for _table in _tables.text:
            await ctx.send(_table)

    @top.command(
        name='winrate',
        brief="Show the leaderboard for win %",
        usage=("`{0}top winrate`\n" \
               "`{0}top winrate [n players]`"
        )
    )
    async def _top_winrate(self, ctx, *args):
        """Display the top 10 players in the league by win %. If a number is specified, display that many players instead."""

        limit = utils.get_limit(args)
        players = self.bot.db.find_top_members_by("winrate", ctx.message.guild, limit=limit)
        _tables = self._make_leaderboard_table(players, 'winrate', 'Top Players by Win %')
        for _table in _tables.text:
            await ctx.send(_table)

    @top.command(
        name='games',
        brief="Show the leaderboard for total games played",
        usage=("`{0}top games`\n" \
               "`{0}top games [n players]`"
        )
    )
    async def _top_games(self, ctx, *args):
        """Display the top 10 players in the league by games played. If a number is specified, display that many players instead."""

        limit = utils.get_limit(args)
        players = self.bot.db.find_top_members_by("accepted", ctx.message.guild, limit=limit)
        _tables = self._make_leaderboard_table(players, 'accepted', 'Top Players by Games Played')
        for _table in _tables.text:
            await ctx.send(_table)


    @top.command(
        name='score',
        brief="Show the leaderboard for highest score",
        usage=("`{0}top score`\n" \
               "`{0}top score [n players]`"
        )
    )
    async def _top_score(self, ctx, *args):
        """Display the top 10 players in the league by points. If a number is specified, display that many players instead."""

        limit = utils.get_limit(args)
        players = self.bot.db.find_top_members_by("points", ctx.message.guild, limit=limit)
        _tables = self._make_leaderboard_table(players, 'points', 'Top Players by Points')
        for _table in _tables.text:
            await ctx.send(_table)


    def _make_deck_tables(self, data, key):
        if key == "meta":
            title = "Deck Stats: Meta %"
            rows = [
                [f"{i+1}.", deck['name'], f"{100*deck[key]:.3g}%"] for i, deck in enumerate(data)
            ]
        elif key == "winloss":
            title = "Deck Stats: Win-Loss Ratio"
            rows = [
                [f"{i+1}.", deck['name'], f"{deck['wins']}-{deck['losses']}"] for i, deck in enumerate(data)
            ]
        elif key == "winrate":
            title = "Deck Stats: Win %"
            rows = [
                [f"{i+1}.", deck['name'], f"{100*deck[key]:.3g}%"] for i, deck in enumerate(data)
            ]
        elif key == "popularity":
            title = "Deck Stats: # of Pilots"
            rows = [
                [f"{i+1}.", deck['name'], str(len(deck['players']))] for i, deck in enumerate(data)
            ]

        return line_table.LineTable(rows, title=title)

    def _make_complete_deck_tables(self, data):
        headings = ["Name", "Wins", "Losses", "Win %", "Meta %", "Pilots"]
        rows = [
            [
                str(deck['name']),
                str(deck['wins']),
                str(deck['losses']),
                f"{100*deck['winrate']:.3g}%",
                f"{100*deck['meta']:.3g}%",
                str(len(deck['players']))
            ] for deck in data
        ]
        height = 10
        _tables = [
            str(table.Table(title="Deck Stats", columns=headings, rows=rows[i:i+height]))
            for i in range(0, len(rows)-1, height)
        ]
        return _tables

    def _make_full_player_deck_tables(self, data, user):
        headings = ["Name", "Wins", "Losses", "Win %"]
        rows = [
            [
                str(deck['name']),
                str(deck['wins']),
                str(deck['losses']),
                f"{100&deck['winrate']:.3g}%"
            ] for deck in data
        ]
        height = 10
        _tables = [
            str(table.Table(title=f"**{user.name}'s** Deck Stats", columns=headings, rows=rows[i:i+height]))
            for i in range(0, len(rows)-1, height)
        ]
        return _tables
        

    @commands.command(
        brief="Display records of tracked decks",
        usage=("`{0}deckstats`\n" \
               "`{0}deckstats [meta|winrate|popularity|all]`\n" \
               "`{0}deckstats [wins|winrate|all] @user`"
        )
    )
    @commands.guild_only()
    async def deckstats(self, ctx, *, sort_key: str=""):
        """Displays the records of all decks tracked by the league. Data displayed includes meta share, win %, wins, and popularity. A deck is required to have at least 10 games recorded in order to show up in the stats.
        
        Games played is the number of times a deck has been logged. 
        The meta share is the percentage of time a deck is logged and is proportional to games played.
        Win % should be self-explanatory. 
        Popularity is represented by the number of unique pilots that have logged matches with the deck.
        If a user is mentioned, display only deckstats for that user.

        By default, this command sorts the results by meta share but displays with wins and losses of each deck. Include one of the other keys to sort by those columns instead."""


        # Use a line_table instead of a block_table for better mobile experience
        # Display only the selected stat and the sample size
        # Leave detail statistical analysis in the deck info command
        if not ctx.message.mentions:
            data = utils.get_match_stats(ctx)
        else:
            await self.display_player_deck_stats(ctx, sort_key)
            return
        if not data:
            emsg = embed.error(description="No decks found with enough matches")
            await ctx.send(embed=emsg)
            return

        if not sort_key:
            sorted_data = utils.sort_by_entries(data)
            _tables = self._make_deck_tables(sorted_data, "winloss")
        elif sort_key.lower() == "winrate":
            sorted_data = utils.sort_by_winrate(data)
            _tables = self._make_deck_tables(sorted_data, "winrate")
        elif sort_key.lower() == "meta":
            sorted_data = utils.sort_by_entries(data)
            _tables = self._make_deck_tables(sorted_data, "meta")
        elif sort_key.lower() == "popularity":
            sorted_data = utils.sort_by_unique_players(data)
            _tables = self._make_deck_tables(sorted_data, "popularity")
        else:
            sorted_data = utils.sort_by_winrate(data)
            _tables = self._make_complete_deck_tables(sorted_data)
            for _table in _tables:
                await ctx.send(_table)
            return
        for _table in _tables.text:
            await ctx.send(_table)

    async def display_player_deck_stats(self, ctx, sort_key):
        sort_key = sort_key.split()[0]
        user = ctx.message.mentions[0]
        if not self.bot.db.find_member(user.id, ctx.message.guild):
            await ctx.send(embed=embed.error(f"**{user.name}** is not a registered player"))
            return
        data = utils.get_player_match_stats(ctx, user)
        if not data:
            await ctx.send(embed=embed.error(description=f"No matches found for **{user.name}**"))
            return
        
        if sort_key.lower() == "wins":
            sorted_data = utils.sort_by_entries(data)
            _tables = self._make_deck_tables(sorted_data, "winloss")
        elif sort_key.lower() == "winrate":
            sorted_data = utils.sort_by_winrate(data)
            _tables = self._make_deck_tables(sorted_data, "winrate")
        else:
            sorted_data = utils.sort_by_winrate(data)
            _tables = self._make_full_player_deck_tables(sorted_data, user)
            for _table in _tables:
                await ctx.send(_table)
            return
        for _table in _tables.text:
            await ctx.send(_table)


    def _make_match_table(self, title, matches, winner_type="player"):
        header = "`DATE` `ID` `REPLAY` `WINNER`\n"
        rows = []
        max_name_len = 16
        for match in matches:
            date = utils.short_date_from_timestamp(match['timestamp'])
            if winner_type == "deck":
                deck_name = match['winning_deck'] if match['winning_deck'] else "N/A"
                if len(deck_name) > max_name_len:
                    deck_name = self.bot.db.get_deck_short_name(deck_name)
                winner = deck_name
            else:
                winner = utils.get_winner_name(match)
                winner = utils.shorten_player_name(winner)
            replay_link = f"[Link]({match['replay_link']})" if match['replay_link'] else "`???`"
            rows.append(f"`{date} {match['game_id']}` {replay_link} `{winner}`")
        emsgs = []
        for i in range(0, len(rows), 20):
            emsgs.append(
                embed.info(title=title, description=(header + "\n".join(rows[i:(i+20)])))
            )
        return emsgs

    
    @commands.group(
        brief="Find a filtered list of games",
        usage=("`{0}games [decks|players]`")
    )
    @commands.guild_only()
    async def games(self, ctx):
        """Displays a list of filtered games. If no filter type is included, the most recent 10 games will be displayed. If filtered by decks, include a comma-separated list of decks that the games should contain. If filtered by players, mention all players that the games should contain."""

        if ctx.invoked_subcommand is None:
            matches = self.bot.db.find_matches({}, ctx.message.guild, limit=10)
            emsgs = self._make_match_table('Recent Games', matches, winner_type="player")
            for emsg in emsgs:
                await ctx.send(embed=emsg)
            return


    @games.command(
        name="decks",
        brief="Find a filtered list of games by decks",
        usage="`{0}games decks [deck 1], [deck 2], ...`"
    )
    async def _games_by_decks(self, ctx, *, deck_names: str=""):
        """Displays a list of games filtered by decks. Include a comma-separated list of decks to filter by."""

        if not deck_names:
            await ctx.send(embed=embed.error(ctx, description="No deck name included"))
            return
        deck_name_list = deck_names.split(',')
        if len(deck_name_list) > 4:
            await ctx.send(embed=embed.error(ctx, description="Games cannot contain more than 4 decks"))
            return

        deck_names = []
        for deck_name in deck_name_list:
            deck = self.bot.db.find_deck(deck_name)
            if not deck:
                continue
            deck_names.append(deck['name'])

        if not deck_names:
            await ctx.send(embed=embed.error(ctx, description="No decks found with the given deck names"))
            return
        matches = self.bot.db.find_matches({"players.deck": {"$all": deck_names}}, ctx.message.guild, limit=20)
        matches = list(matches)
        if not matches:
            await ctx.send(embed=embed.info(description=("No matches found containing " + ", ".join(deck_names))))
            return
        title = "Games Containing: " + ", ".join(deck_names)
        emsgs = self._make_match_table(title, matches, winner_type="deck")
        for emsg in emsgs:
            await ctx.send(embed=emsg)
        

    @games.command(
        name="players",
        brief="Find a filtered list of games by players",
        usage="`{0}games players @player1 @player2 ...`"
    )
    async def _games_by_players(self, ctx, *args):
        """Displays a list of games filtered by players. Mention all players to filter by. If no players are mentioned, filter by games containing the sender."""

        mentions = ctx.message.mentions
        if len(mentions) > 4:
            await ctx.send(embed=embed.error(description="Too many players mentioned"))
            return
        if len(mentions) == 0:
            mentions.append(ctx.message.author)
        matches = self.bot.db.find_matches(
            {"players.user_id": {"$all": [user.id for user in mentions]}},
            ctx.message.guild,
            limit=20
        )
        matches = list(matches)
        if not matches:
            await ctx.send(embed=embed.info(description=("No matches found containing " + ", ".join([user.name for user in mentions]))))
            return
        title = "Games Containing: " + ", ".join([mention.name for mention in mentions])
        emsgs = self._make_match_table(title, matches, winner_type="player")
        for emsg in emsgs:
            await ctx.send(embed=emsg)

def setup(bot):
    bot.add_cog(Data(bot))
