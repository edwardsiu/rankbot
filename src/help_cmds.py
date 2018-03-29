import discord
from src.colors import *

def user_help(token):
    emsg = discord.Embed(title="Help")
    emsg.add_field(name="Command", inline=True, value=(
        "**"
        + "{}help\n\n".format(token)
        + "{}addme\n\n".format(token)
        + "{}register\n\n".format(token)
        + "{}players\n\n".format(token)
        + "{}describe\n\n".format(token)
        + "{}log\n\n".format(token)
        + "{}confirm\n\n".format(token)
        + "{}deny\n\n".format(token)
        + "{}score\n\n".format(token)
        + "{}top\n\n".format(token)
        + "{}pending\n\n".format(token)
        + "{}remind\n\n".format(token)
        + "{}status\n\n".format(token)
        + "{}lfg".format(token)
        + "**"
    ))
    emsg.add_field(name="Description", inline=True, value=(
        "show the command list. `{}help [command]` for detail\n\n".format(
            token)
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
        + "show the status of the given match\n\n"
        + "add or remove yourself from the ranked-lfg queue"
    ))
    return emsg

def admin_help(token):
    emsg = discord.Embed(title="Admin Help")
    emsg.add_field(name="Command", inline=True, value=(
        "**"
        + "{}add_user\n\n".format(token)
        + "{}rm_user\n\n".format(token)
        + "{}reset\n\n".format(token)
        + "{}set_admin\n\n".format(token)
        + "{}disputed\n\n".format(token)
        + "{}override".format(token)
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

def get_help_detail(command, token):
    name = "help_{}".format(command)
    if name in globals():
        emsg = globals()[name](token)
        return emsg
    return None

def help_log(token):
    usage = "`{}log @player1 @player2 @player3`".format(token)
    description = (
        "Logs a match result into the league. The winner of the match must be the one to log "
        + "the result, and mention exactly 3 losers. Upon logging the result, each loser must "
        + "confirm the match result via the `{0}confirm` command, or dispute it via `{0}deny`.".format(token)
    )
    return help_detail("log", usage, description)

def help_score(token):
    usage = "`{0}score`\n`{0}score @user1 @user2 ...`".format(token)
    description = (
        "Displays the score card of the given user, or the current user if no user "
        + "is mentioned. The score card contains the user's league points, total wins, "
        + "total losses, and win percentage. League points are calculated as follows: \n"
        + "\t1. Each registered player starts with 1000 points.\n"
        + "\t2. Losers of a match each lose 1% of their current points, rounded up.\n"
        + "\t3. Winner of a match gains the sum of the points lost by the losers."
    )
    return help_detail("score", usage, description)

def help_override(token):
    usage = "`{}override game_id action`\nValid actions are `accept` and `remove`".format(token)
    description = (
        "League admins can resolve a disputed match via the override command. "
        + "To override a match, the admin must indicate the game id. A list of disputed "
        + "game ids can be produced via the `{}disputed` command. Resolutions that are ".format(token)
        + "allowed are `accept` and `remove`, where `accept` sets the match to confirmed "
        + "and `remove` deletes the match entirely."
    )
    return help_detail("override", usage, description)
