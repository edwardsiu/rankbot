import discord

def is_registered(ctx):
    if not ctx.bot.db.find_member(ctx.message.author.id, ctx.message.guild):
        return False
    return True

async def is_admin(ctx):
    if await ctx.bot.is_owner(ctx.message.author):
        return True
    if ctx.message.author.id == ctx.message.guild.owner.id:
        return True
    admin_role = ctx.bot.db.get_admin_role(ctx.message.guild)
    if not discord.utils.find(lambda r: r.name == admin_role.name, ctx.message.author.roles):
        return False
    return True