import discord
from discord.ext import commands
from src import database
from src import embed
from src import help_formatter

class RankBot(commands.Bot):
    def setup_config(self, config):
        self.db = database.RankDB(config["mongodb_host"], config["mongodb_port"])
        self.client_id = config["client_id"]
        self.deck_data = {"data": None, "unsynced": True}

    async def on_guild_join(self, guild):
        emsg = embed.msg(description=(
            "Please create a role and assign that role as the league "
            + "admin using `set_admin [role name]`"
        ))
        await guild.owner.send(embed=emsg)