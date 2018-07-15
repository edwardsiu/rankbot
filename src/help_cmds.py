import discord

def add_token(token, s):
    return "{}{}".format(token, s)

def user_help(token):
    emsg = discord.Embed(title="Command Help")
    emsg.add_field(name="{}help".format(token), inline=False, value=(
        "Show the command list. `{}help [command]` for detail\n\n".format(token)
    ))
    emsg.add_field(name="{}addme".format(token), inline=False, value=(
        "Get an invite link to add Isperia"
    ))
    emsg.add_field(name="{}register".format(token), inline=False, value=(
        "Register to the server ranked league"
    ))
    emsg.add_field(name="{}log".format(token), inline=False, value=(
        "Log a match result into the ranked system"
    ))
    emsg.add_field(name="{}confirm".format(token), inline=False, value=(
        "Verify the most recent match result"
    ))
    emsg.add_field(name="{}deny".format(token), inline=False, value=(
        "Dispute the most recent match result"
    ))
    emsg.add_field(name="{}status".format(token), inline=False, value=(
        "Check the details of the most recent match"
    ))
    emsg.add_field(name="{}pending".format(token), inline=False, value=(
        "List your pending unconfirmed matches"
    ))
    emsg.add_field(name="{}remind".format(token), inline=False, value=(
        "Remind players to confirm your pending matches"
    ))
    emsg.add_field(name="{}top".format(token), inline=False, value=(
        "List the top players in the league"
    ))
    emsg.add_field(name="{}all".format(token), inline=False, value=(
        "See the full player rankings"
    ))
    emsg.add_field(name="{}score".format(token), inline=False, value=(
        "Show your ranked score card"
    ))
    emsg.add_field(name="{}recent".format(token), inline=False, value=(
        "Show your last 5 match results"
    ))
    emsg.add_field(name="{}describe".format(token), inline=False, value=(
        "Show an overview of the league"
    ))
    emsg.add_field(name="{}players".format(token), inline=False, value=(
        "List the names of all registered players"
    ))
    emsg.add_field(name="{}lfg".format(token), inline=False, value=(
        "Add or remove yourself from the looking-for-game queue"
    ))
    emsg.add_field(name="{}deck".format(token), inline=False, value=(
        "Show your last played deck"
    ))
    emsg.add_field(name="{}set-deck".format(token), inline=False, value=(
        "Set your last played deck"
    ))
    emsg.add_field(name="{}list-deck".format(token), inline=False, value=(
        "Show all registered decks that are being tracked"
    ))
    emsg.add_field(name="{}stat-deck".format(token), inline=False, value=(
        "Show tracked deck statistics"
    ))
    return emsg

def admin_help(token):
    emsg = discord.Embed(title="Admin Command Help")
    emsg.add_field(name="{}add_user".format(token), inline=False, value=(
        "Register the mentioned user to the league"
    ))
    emsg.add_field(name="{}rm_user".format(token), inline=False, value=(
        "Unregister the mentioned user from the league"
    ))
    emsg.add_field(name="{}reset".format(token), inline=False, value=(
        "Reset all points and remove all matches"
    ))
    emsg.add_field(name="{}set_admin".format(token), inline=False, value=(
        "Set the mentioned role as the league admin role"
    ))
    emsg.add_field(name="{}disputed".format(token), inline=False, value=(
        "List all disputed matches"
    ))
    emsg.add_field(name="{}override".format(token), inline=False, value=(
        "Resolve a disputed match"
    ))
    return emsg

def help_detail(command, usage, description):
    emsg = discord.Embed(title="Command: {}".format(command))
    emsg.add_field(name="Usage", value=usage)
    emsg.add_field(name="Description", value=description)
    return emsg

def get_help_detail(command, token):
    name = "help_{}".format(command.replace("-","_"))
    if name in globals():
        emsg = globals()[name](token)
        return emsg
    return None

def help_log(token):
    usage = "`{}log @player1 @player2 @player3`".format(token)
    description = (
        "Logs a match result into the league. The winner of the match must be the one to log "
        + "the result, and mention exactly 3 losers. Upon logging the result, each player must "
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
        + "have played less than 5 matches will not be included in the leaderboard."
    )
    return help_detail("top", usage, description)

def help_all(token):
    usage = "`{0}all`\n`{0}all [wins|games|points]`".format(token)
    description = (
        "Displays all players in the league by points, wins, or games played. "
        + "If a category is not specified, ranking by points will be shown. "
        + "Players that have played less than 5 matches will not be included in the leaderboard."
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

def help_deck(token):
    usage = "`{0}deck`\n`{0}deck @user1 @user2 ...`".format(token)
    description = (
        "Show the last played deck of the mentioned players, or your own last played deck "
        + "if no players are mentioned."
    )
    return help_detail("deck", usage, description)

def help_set_deck(token):
    usage = "`{}set-deck [deck name]`".format(token)
    description = (
        "Set your last played deck to `deck name`. Short hand names are allowed. If no "
        + "deck name is specified or the deck is not a recognized deck, the deck will "
        + "default to Rogue."
    )
    return help_detail("set-deck", usage, description)

def help_list_deck(token):
    usage = "`{0}list-deck`\n`{0}list-deck [color combo]`".format(token)
    description = (
        "Show a list of all registered decks tracked by Isperia. If a color combination "
        + "is specified, shows a list of decks with the given color combination. "
        + "Otherwise, a list of all decks will be displayed. Color combinations should "
        + "be in WUBRG format."
    )
    return help_detail("list-deck", usage, description)

def help_stat_deck(token):
    usage = "`{0}stat-deck`\n`{0}stat-deck [wins|winrate|popularity]".format(token)
    description = (
        "Show match statistics of decks tracked by Isperia. The default sort is by total "
        + "games played. Wins will sort by total wins. Winrate sorts by win %. Popularity "
        + "sorts by number of unique players playing the deck."
    )
    return help_detail("stat-deck", usage, description)

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
