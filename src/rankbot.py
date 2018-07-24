import discord
from discord.ext import commands
from src.colors import BLUE, YELLOW, RED
from src import database

class RankBot(commands.Bot):
    def setup_config(self, config):
        self.db = database.RankDB(config["mongodb_host"], config["mongodb_port"])
        self.owner = config["owner"]
        self.client_id = config["client_id"]
        self.deck_data = {"data": None, "unsynced": True}

    async def on_server_join(self, server):
        emsg = discord.Embed(description=(
            "Please create a role and assign that role as the league "
            + "admin using `set_admin [role name]`"
        ))
        await self.send_embed(server.owner, emsg)

    async def on_server_remove(self, server):
        self.db.drop_database(str(server.id))

    async def is_registered(self, ctx):
        if not self.db.find_member(ctx.message.author.id, ctx.message.server.id):
            emsg = discord.Embed(color=RED, description=(
                "{} is not a registered player".format(ctx.message.author.name)
            ))
            await self.send_embed(ctx.message.channel, emsg)
            return False
        return True

    def is_in_server(self, ctx):
        return ctx.message.server

    def is_admin(self, ctx):
        user = ctx.message.author
        if (user.id == self.owner or user.id == ctx.message.server.owner.id):
            return True
        user_roles = [role.name for role in user.roles]
        if self.db.is_admin(user_roles, ctx.message.server.id):
            return True
        return False