def is_registered(ctx):
    if not ctx.bot.db.find_member(ctx.message.author, ctx.message.guild):
        return False
    return True