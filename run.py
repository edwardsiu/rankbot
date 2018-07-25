import logging
import logging.handlers
import os
import yaml

from discord.ext import commands
from src import rankbot

def get_extensions():
    return [f.split(".")[0] for f in os.listdir("src/extensions") if not f[0] == "_"]

logging_fmt = '%(asctime)-15s - %(levelname)s - %(message)s'
handler = logging.handlers.RotatingFileHandler(filename="bot.log", maxBytes=100000, backupCount=1)
logging.basicConfig(format=logging_fmt, handlers=[handler], level=logging.INFO)

with open("config/bot.yml", "r") as f:
    config = yaml.load(f.read())

bot = rankbot.RankBot(command_prefix=config["command_prefix"])
bot.setup_config(config)
#extensions = get_extensions()
extensions = ["owner", "members", "stats"]
for ext in extensions:
    try:
        bot.load_extension("src.extensions.{}".format(ext))
        logging.info("Extension loaded: {}".format(ext))
    except ImportError:
        logging.error("Failed to load extension: {}".format(ext))
bot.run(config["token"], bot=True, reconnect=True)