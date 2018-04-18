import discord

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
        + "{}all\n\n".format(token)
        + "{}pending\n\n".format(token)
        + "{}remind\n\n".format(token)
        + "{}recent\n\n".format(token)
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
        + "see the full player rankings in the league\n\n"
        + "list your pending unconfirmed matches\n\n"
        + "remind players to confirm your pending matches\n\n"
        + "show the last 5 matches and their result\n\n"
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

def help_confirm(token):
    usage = "`{0}confirm`\n`{0}confirm [game id]`".format(token)
    description = (
        "Confirm a match with the given game id. If no game id is given, confirms "
        + "the most recent unconfirmed match. All match results logged with the "
        + "`{}log` command must be confirmed by all players for the result to be ".format(token)
        + "accepted."
    )
    return help_detail("confirm", usage, description)

def help_deny(token):
    usage = "`{0}deny`\n`{0}deny [game id]`".format(token)
    description = (
        "Dispute a match with the given game id. If no game id is given, disputes "
        + "the most recent unconfirmed match. A match marked as `DISPUTED` cannot be "
        + "resolved except by a league admin."
    )
    return help_detail("deny", usage, description)

def help_score(token):
    usage = "`{0}score`\n`{0}score @user1 @user2 ...`".format(token)
    description = (
        "Displays the score card for the given user(s), or the current user if no user "
        + "is mentioned. The score card contains the user's league points, total wins, "
        + "total losses, and win percentage. League point changes are calculated based "
        + "on the score difference between the winner and each loser, such that losing "
        + "to someone worse than you causes a greater loss in points while losing to "
        + "someone with a higher score than you causes a lesser loss in points.\n\n"
    )
    return help_detail("score", usage, description)

def help_top(token):
    usage = "`{0}top`\n`{0}top [wins|games|points]`".format(token)
    description = (
        "Displays the top 10 players in the league by points, wins, or games played. "
        + "If a category is not specified, ranking by points will be shown. Players that "
        + "have not played any matches will not be included in the leaderboard."
    )
    return help_detail("top", usage, description)

def help_all(token):
    usage = "`{0}all`\n`{0}all [wins|games|points]`".format(token)
    description = (
        "Displays all players in the league by points, wins, or games played. "
        + "If a category is not specified, ranking by points will be shown. "
        + "Players that have not played any matches will not be included in the leaderboard."
    )
    return help_detail("all", usage, description)

def help_remind(token):
    usage = "`{}remind`".format(token)
    description = (
        "Pings players that need to confirm/deny a pending match in your pending queue."
    )
    return help_detail("remind", usage, description)

def help_status(token):
    usage = "`{}status [game id]`".format(token)
    description = (
        "Shows details about the match with the given game id, including the match status, "
        + "winner, players, and each players' confirmation status."
    )
    return help_detail("status", usage, description)

def help_recent(token):
    usage = "`{0}recent`\n`{0}recent @user1 @user2 ...`".format(token)
    description = (
        "Show your last 5 matches and their result. If there are mentioned users, show "
        + "their last 5 matches instead."
    )
    return help_detail("recent", usage, description)

def help_lfg(token):
    usage = "`{}lfg`".format(token)
    description = (
        "Add yourself to the lfg queue or remove yourself from the lfg queue if you are "
        + "already on it. Displays the players in the lfg queue. When the queue hits 4 "
        + "players, ping all 4 players to notify them of a pod."
    )
    return help_detail("lfg", usage, description)

def help_reset(token):
    usage = "`{}reset`".format(token)
    description = (
        "Resets all points to the default and clears all match results. Asks for "
        + "confirmation before resetting."
    )
    return help_detail("reset", usage, description)

def help_override(token):
    usage = "`{}override [game_id] [accept|remove]`".format(token)
    description = (
        "League admins can resolve a disputed match via the override command. "
        + "To override a match, the admin must indicate the game id. A list of disputed "
        + "game ids can be produced via the `{}disputed` command. Resolutions that are ".format(token)
        + "allowed are `accept` and `remove`, where `accept` sets the match to confirmed "
        + "and `remove` deletes the match entirely."
    )
    return help_detail("override", usage, description)
