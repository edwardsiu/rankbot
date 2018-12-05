import asyncio
from datetime import datetime
from discord.ext import commands
from app.utils import checks, embed

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

            emsg.add_field(name="Season Winners", value="\n".join(
                [f"`{i+1}. {self.bot.db.find_member(user_id, ctx.message.guild)['name']}`" 
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

        last_season_number, season_leaders = self.bot.db.reset_season(ctx.message.guild)
        emsg = embed.success(description=f"Season {last_season_number} has ended.")
        emsg.add_field(name="Season Winners", value="\n".join(
            [f"`{i+1}. {player['name']}`" for i, player in enumerate(season_leaders)]
        ))
        await ctx.send(embed=emsg)

def setup(bot):
    bot.add_cog(Seasons(bot))
