import asyncio
from datetime import datetime
from discord.ext import commands
from app.constants import emojis
from app.utils import checks, embed, utils

class Seasons():
    def __init__(self, bot):
        self.bot = bot


    @commands.command(
        brief="Get information about a season",
        usage=("`{0}season`\n" \
               "`{0}season [season number]`"
        )
    )
    @commands.guild_only()
    async def season(self, ctx, *, season_number: int = None):
        """Get information about a season."""

        season_info = self.bot.db.get_season(ctx.message.guild, season=season_number)
        if not season_info:
            await ctx.send(embed=embed.error(description=f"Season {season_number} does not exist."))
            return
        
        emsg = embed.info(title=f"Season {season_info['season_number']}")
        start_date = datetime.fromtimestamp(season_info["start_time"])
        emsg.add_field(name="Start Date", value=start_date.strftime("%Y-%m-%d"))
        if "end_time" in season_info:
            end_date = datetime.fromtimestamp(season_info["end_time"])
            emsg.add_field(name="End Date", value=end_date.strftime("%Y-%m-%d"))
            awards = [emojis.first_place, emojis.second_place, emojis.third_place]
            emsg.add_field(name="Season Awards", value="\n".join(
                [f"`{awards[i]} - {self.bot.db.find_member(user_id, ctx.message.guild)['name']}`" 
                for i, user_id in enumerate(season_info["season_leaders"])]
                )
            )
        await ctx.send(embed=emsg)

    @commands.command(
        name="end-season",
        brief="End the current season and starts a new season",
        usage="`{0}end-season`"
    )
    @commands.guild_only()
    @commands.check(checks.is_admin)
    async def end_season(self, ctx):
        """End the current season and start a new season. Season awards will be given out to the top 3 players."""

        # Display end-of-season stats for the top 10 players for points and games played
        players = self.bot.db.find_top_members_by("points", ctx.message.guild, limit=10)
        points_tables = utils.make_leaderboard_table(players, 'points', 'Top Players by Points')
        if points_tables is not None:
            for _table in points_tables.text:
                await ctx.send(_table)

        players = self.bot.db.find_top_members_by("accepted", ctx.message.guild, limit=10)
        played_tables = utils.make_leaderboard_table(players, 'accepted', 'Top Players by Games Played')
        if played_tables is not None:
            for _table in played_tables.text:
                await ctx.send(_table)

        # Rollover to the new season
        last_season_number, season_leaders = self.bot.db.reset_season(ctx.message.guild)
        awards = [emojis.first_place, emojis.second_place, emojis.third_place]
        emsg = embed.success(description=f"Season {last_season_number} has ended.")
        if season_leaders[0] is not None:
            emsg.add_field(name="Season Awards", value="\n".join(
                [f"`{awards[i]} - {player['name']}`" for i, player in enumerate(season_leaders)]
            ))
        await ctx.send(embed=emsg)

def setup(bot):
    bot.add_cog(Seasons(bot))
