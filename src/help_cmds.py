import discord
from src.colors import *

def user_help():
    emsg = discord.Embed(title="Help", color=YELLOW)
    emsg.add_field(name="Command", inline=True, value=(
        "**"
        + "!help\n\n"
        + "!addme\n\n"
        + "!register\n\n"
        + "!players\n\n"
        + "!describe\n\n"
        + "!log\n\n"
        + "!confirm\n\n"
        + "!deny\n\n"
        + "!score\n\n"
        + "!top\n\n"
        + "!pending\n\n"
        + "!remind\n\n"
        + "!status"
        + "**"
    ))
    emsg.add_field(name="Description", inline=True, value=(
        "show the command list. `!help [command]` for detail\n\n"
        + "get an invite link to add Isperia\n\n"
        + "register to the server league\n\n"
        + "list the name of all players in the league\n\n"
        + "show details about the league\n\n"
        + "log a match result\n\n"
        + "confirm the most recent match result\n\n"
        + "dispute the most recent match result\n\n"
        + "show your score card\n\n"
        + "see the top players in the league\n\n"
        + "list your pending unconfirmed matches\n\n"
        + "remind players to confirm your pending matches\n\n"
        + "show the status of the given match"
    ))
    return emsg

def admin_help():
    emsg = discord.Embed(title="Admin Help", color=YELLOW)
    emsg.add_field(name="Command", inline=True, value=(
        "**"
        + "!add_user\n\n"
        + "!rm_user\n\n"
        + "!reset\n\n"
        + "!set_admin\n\n"
        + "!disputed\n\n"
        + "!override"
        + "**"
    ))
    emsg.add_field(name="Description", inline=True, value=(
        "register the mentioned user\n\n"
        + "unregister the mentioned user\n\n"
        + "reset all points and remove all matches\n\n"
        + "set the mentioned role as the league admin role\n\n"
        + "list all disputed matches\n\n"
        + "resolve a disputed match"
    ))
    return emsg

def help_detail(command, usage, description):
    emsg = discord.Embed(title="Command: {}".format(command))
    emsg.add_field(name="Usage", value=usage)
    emsg.add_field(name="Description", value=description)
    return emsg

def get_help_detail(command):
    name = "help_{}".format(command)
    if name in globals():
        emsg = globals()[name]()
        return emsg
    return None

def help_log():
    usage = "`!log @player1 @player2 @player3`"
    description = (
        "Logs a match result into the league. The winner of the match must be the one to log "
        + "the result, and mention exactly 3 losers. Upon logging the result, each loser must "
        + "confirm the match result via the `!confirm` command, or dispute it via `!deny`."
    )
    return help_detail("log", usage, description)

def help_override():
    usage = "`!override game_id action`\nValid actions are `accept` and `remove`"
    description = (
        "League admins can resolve a disputed match via the override command. "
        + "To override a match, the admin must indicate the game id. A list of disputed "
        + "game ids can be produced via the `!disputed` command. Resolutions that are "
        + "allowed are `accept` and `remove`, where `accept` sets the match to confirmed "
        + "and `remove` deletes the match entirely."
    )
    return help_detail("override", usage, description)
