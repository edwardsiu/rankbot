import discord
from app.utils import embed

async def is_registered(ctx):
    if not ctx.bot.db.find_member(ctx.message.author.id, ctx.message.guild):
        await ctx.send(embed=embed.error(description=f"**{ctx.message.author.name}** is not registered"))
        return False
    return True

async def is_admin(ctx):
    if await ctx.bot.is_owner(ctx.message.author):
        return True
    if ctx.bot.is_super_admin(ctx.message.author.id):
        return True
    if ctx.message.author.id == ctx.message.guild.owner_id:
        return True
    admin_role = ctx.bot.db.get_admin_role(ctx.message.guild)
    if not discord.utils.find(lambda r: r.name == admin_role.name, ctx.message.author.roles):
        return False
    return True

async def is_super_admin(ctx):
    if await ctx.bot.is_owner(ctx.message.author):
        return True
    if ctx.bot.is_super_admin(ctx.message.author.id):
        return True
    return False
