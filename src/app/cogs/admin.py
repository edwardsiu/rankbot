import discord
from discord.ext import commands
from app.constants import status_codes as stc
from app.utils import checks, embed

class Admin():
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name='set-admin', 
        brief="Set the league admin role",
        usage="`{0}set-admin @role`"
    )
    @commands.guild_only()
    @commands.check(checks.is_admin)
    async def set_admin(self, ctx, *, role: discord.Role):
        """Sets the league admin role to the mentioned role.
        League admins can audit, accept, and remove matches."""

        self.bot.db.set_admin_role(role.name, ctx.message.guild)
        await ctx.send(embed=embed.success(description=f"**SUCCESS** - {role.mention} set to league admin"))


    @commands.command(
        brief="Force a match into accepted state",
        usage="`{0}accept [game id]`"
    )
    @commands.guild_only()
    @commands.check(checks.is_admin)
    async def accept(self, ctx, *, game_id: str=""):
        """Force a match into accepted state.
        This should only be used if a match is known to be valid but one or more of the participants is unwilling or unavailable to confirm. This command can only be used by an admin."""

        if not game_id:
            await ctx.send(embed=embed.error(description="No game id specified"))
            return
        match = self.bot.db.find_match(game_id, ctx.message.guild)
        if not match:
            await ctx.send(embed=embed.error(description=f"`{game_id}` does not exist"))
            return
        if match["status"] == stc.ACCEPTED:
            return

        self.bot.db.confirm_match_for_users(game_id, ctx.message.guild)
        delta = self.bot.db.check_match_status(game_id, ctx.message.guild)
        if delta:
            await ctx.send(embed=embed.match_delta(game_id, delta))


    @commands.command(
        brief="Remove a match",
        usage="`{0}remove [game id]`"
    )
    @commands.guild_only()
    @commands.check(checks.is_registered)
    async def remove(self, ctx, *, game_id: str=""):
        """Removes a match from the tracking system.
        This should only be used if a match is known to be invalid. Only pending matches can be rejected. This command can only be used by an admin or the player who logged the match."""

        if not game_id:
            await ctx.send(embed=embed.error(description="No game id specified"))
            return
        match = self.bot.db.find_match(game_id, ctx.message.guild)
        if not match:
            await ctx.send(embed=embed.error(description=f"`{game_id}` does not exist"))
            return
        if match["status"] == stc.ACCEPTED:
            await ctx.send(embed=embed.error(description="Cannot override an accepted match"))
            return
        if not (match["winner"] == ctx.message.author.id or checks.is_admin(ctx)):
            await ctx.send(embed=embed.error(description="Only a league admin or the match winner can remove a match"))
            return

        self.bot.db.delete_match(game_id, ctx.message.guild)
        await ctx.send(embed=embed.msg(description=f"`{game_id}` has been removed"))
    

def setup(bot):
    bot.add_cog(Admin(bot))
