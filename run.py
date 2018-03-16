import logging
import yaml

from src import rankbot

with open("config/bot.yml", 'r') as f:
    config = yaml.load(f.read())
bot = rankbot.Isperia(str(config['token']))
bot.run(bot.token)
