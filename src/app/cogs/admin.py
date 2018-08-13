import discord
from discord.ext import commands
from app.constants import status_codes as stc
from app.utils import checks, embed

class Admin():
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        brief="Configure settings for the league",
        usage=("`{0}config`\n" \
               "`{0}config [admin]`")
    )
    @commands.guild_only()
    @commands.check(checks.is_admin)
    async def config(self, ctx):
        """Configure or view settings for the league"""

        if ctx.invoked_subcommand is None:
            settings = self.bot.db.get_config(ctx.message.guild)
            emsg = embed.info(title="League Configuration")
            for setting in settings:
                emsg.add_field(name=setting, value=settings[setting])
            await ctx.send(embed=emsg)
            return

    @config.command(
        name="admin", 
        brief="Set the league admin role",
        usage="`{0}config admin @role`"
    )
    @commands.guild_only()
    @commands.check(checks.is_admin)
    async def set_admin(self, ctx, *, role: discord.Role):
        """Sets the league admin role to the mentioned role.
        League admins can audit, accept, and remove matches."""

        self.bot.db.set_admin_role(role.name, ctx.message.guild)
        await ctx.send(embed=embed.success(description=f"**SUCCESS** - {role.mention} set to league admin"))

    @config.command(
        name="threshold"
        brief="Set player or deck leaderboard match threshold",
        usage="`{0}config threshold [player|deck] [value]`"
    )
    async def set_threshold(self, ctx, *args):
        """Set the player or deck threshold to appear on the leaderboard."""

        if len(args) < 2:
            await ctx.send(embed=embed.error(description="Not enough args, include a threshold type and threshold value"))
            return
        if not args[1].isdigit():
            await ctx.send(embed=embed.error(description="Threshold value should be a number"))
            return
        thresh_t = args[0]
        value = int(args[1])
        if thresh_t == "player":
            self.bot.db.set_player_match_threshold(value, ctx.message.guild)
        elif thresh_t == "deck":
            self.bot.db.set_deck_match_threshold(value, ctx.message.guild)
        else:
            await ctx.send(embed=embed.error(description="Unrecognized threshold type."))
            return
        await ctx.send(embed=embed.success(description=f"**SUCCESS** - {thresh_t.upper()} threshold set to {value}"))


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
