def is_registered(ctx):
    if not ctx.bot.db.find_member(ctx.message.author, ctx.message.guild):
        return False
    return True

async def is_admin(ctx):
    if await ctx.bot.is_owner(ctx.message.author):
        return True
    if ctx.message.author.id == ctx.message.guild.owner.id:
        return True
    admin_role = ctx.bot.db.get_admin_role(ctx.message.guild)
    for role in ctx.message.author.roles:
        if role == admin_role:
            return True
    return False