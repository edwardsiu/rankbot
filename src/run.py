import logging
import logging.handlers
import os
import yaml

from discord.ext import commands
from app import rankbot

def get_cogs():
    #return [f.split(".")[0] for f in os.listdir("app/cogs") if not f[0] == "_"]
    return ["decks", "manage", "matches", "members", "owner", "stats"]

logging_fmt = '%(asctime)-15s - %(levelname)s - %(message)s'
handler = logging.handlers.RotatingFileHandler(filename="bot.log", maxBytes=100000, backupCount=1)
logging.basicConfig(format=logging_fmt, handlers=[handler], level=logging.INFO)

with open("../config/bot.yml", "r") as f:
    config = yaml.load(f.read())

bot = rankbot.RankBot(command_prefix=config["command_prefix"])
bot.setup_config(config)
cogs = get_cogs()
for cog in cogs:
    try:
        bot.load_extension("app.cogs.{}".format(cog))
        logging.info("Cog loaded: {}".format(cog))
    except ImportError:
        logging.error("Failed to load cog: {}".format(cog))
bot.run(config["token"], bot=True, reconnect=True)
