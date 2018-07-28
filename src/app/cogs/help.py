import discord
from discord.ext import commands
from app.utils import embed

class Help():
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief="Show this page", hidden=True)
    async def help(self, ctx, *, name: str=""):
        """Show a list of commands. Show detailed help by specifying a command."""

        if name:
            await self.command_help(ctx, name)
            return
        emsg = embed.info(title="Command Help")
        cogs = {}
        for command in self.bot.commands:
            if command.hidden:
                continue
            if command.cog_name in cogs:
                cogs[command.cog_name].append(command)
            else:
                cogs[command.cog_name] = [command]
        sorted_cog_keys = sorted(cogs.keys(), reverse=True)
        for cog_name in sorted_cog_keys:
            cogs[cog_name].sort(key=lambda o: o.name)
            cog_summary = []
            for command in cogs[cog_name]:
                cog_summary.append(f"**`{ctx.prefix}{command.qualified_name}`** -- {command.brief}")
            emsg.add_field(name=cog_name, inline=False, value=("\n".join(cog_summary)))
        emsg.set_footer(text=f"Type {ctx.prefix}help [command] for more info")
        await ctx.send(embed=emsg)
        

    async def command_help(self, ctx, name):
        command = self.bot.get_command(name)
        if not command:
            await ctx.send(embed=embed.error(description="Command not found"))
            return
        if command.name == "help":
            return
        emsg = embed.info(title=f"Command: {command.qualified_name}")
        emsg.add_field(name="Usage", inline=False, value=command.usage.format(ctx.prefix))
        emsg.add_field(name="Description", inline=False, value=command.help)
        if command.aliases:
            aliases = ", ".join([f"`{ctx.prefix}{alias}`" for alias in command.aliases])
            emsg.add_field(name="Aliases", inline=False, value=aliases)
        await ctx.send(embed=emsg)


def setup(bot):
    bot.remove_command('help')
    bot.add_cog(Help(bot))
