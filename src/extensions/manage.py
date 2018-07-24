import discord
from discord.ext import commands

class Manage():
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def admin(self, ctx):
        if not self.bot.is_in_server(ctx):
            return
        if not self.bot.is_admin(ctx):
            return

        emsg = discord.Embed()
        if not ctx.message.role_mentions:
            emsg.description = "Please mention a role to set as league admin role"
            await self.bot.send_error(ctx.message.channel, emsg)
            return
        role = ctx.message.role_mentions[0]
        self.bot.db.set_admin_role(role.name, ctx.message.server.id)
        emsg.description = "{} are now the league admins".format(role.mention)
        await self.bot.send_embed(ctx.message.channel, emsg)

    
    @commands.command()
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