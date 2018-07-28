import discord
from discord.ext import commands
from app.utils import checks, embed

class Manage():
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='set-admin')
    @commands.guild_only()
    @commands.check(checks.is_admin)
    async def set_admin(self, ctx, *, role: discord.Role):
        self.bot.db.set_admin_role(role.name, ctx.message.guild)
        await ctx.send(embed=embed.success(description=f"**SUCCESS** - {role.mention} set to league admin"))

    
    async def reset(self, ctx):
        if not self.bot.is_in_server(ctx):
            return
        if not self.bot.is_admin(ctx):
            return

        emsg = discord.Embed(description="Are you sure you want to reset? (Y/n)")
        await self.bot.send_embed(ctx.message.channel, emsg)
        response = await self.bot.wait_for_message(author=ctx.message.author)
        if response.content == "Y":
            self.bot.db.reset_scores(ctx.message.server.id)
            self.bot.db.reset_matches(ctx.message.server.id)
            emsg = discord.Embed(description=(
                "All registered players have had their scores reset and "
                + "all match records have been cleared."))
            await self.bot.send_embed(ctx.message.channel, emsg)
        else:
            emsg = discord.Embed(description="Reset has been cancelled")
            await self.bot.send_embed(ctx.message.channel, emsg)


def setup(bot):
    bot.add_cog(Manage(bot))
