from src import table
import re

DEFAULT_LIMIT = 10

# message processing
def get_target_users(ctx):
    """Returns the users the command should be applied to. Commands that apply to users
    generally apply to the mentioned users, or if no users are mentioned, applies 
    to the author of the message."""

    if len(ctx.message.mentions):
        return ctx.message.mentions
    return [ctx.message.author]

def get_avatar(user):
    if not user.avatar_url:
        return user.default_avatar_url
    return user.avatar_url

def get_limit(args):
    """Returns the number of elements to fetch from the database.
    Limit is based on the first arg of the command context."""

    if not len(args):
        return DEFAULT_LIMIT
    arg = args[0]
    if arg.isdigit():
        return int(re.match(r"\d*", arg).group())
    elif arg.lower() == "all":
        return 0
    else:
        return DEFAULT_LIMIT

def code_block(string):
    return "```" + string + "```"

# deck data processing
def process_match_stats(matches):
    decks = {}
    for match in matches:
        for member_id in match["decks"]:
            deck_name = match["decks"][member_id]
            if deck_name in decks:
                decks[deck_name]["entries"] += 1
                decks[deck_name]["players"].add(member_id)
            else:
                decks[deck_name] = {
                    "deck_name": deck_name,
                    "entries": 1,
                    "players": {member_id},
                    "wins": 0
                }
                if not deck_name:
                    decks[deck_name]["deck_name"] = "Unknown"
        winner_id = match["winner"]
        winning_deck = match["decks"][str(winner_id)]
        decks[winning_deck]["wins"] += 1
    list_decks = [decks[i] for i in decks]
    return list_decks

def sort_by_entries(data):
    return sorted(data, key=lambda deck: deck["entries"], reverse=True)

def sort_by_wins(data):
    return sorted(data, key=lambda deck: deck["wins"], reverse=True)

def sort_by_winrate(data):
    return sorted(data, key=lambda deck: float(deck["wins"])/deck["entries"], reverse=True)

def sort_by_unique_players(data):
    return sorted(data, key=lambda deck: len(deck["players"]), reverse=True)

def recurse_color_combinations(color, prefix, out):
    if len(color) > 0:
        recurse_color_combinations(color[1:], prefix+color[0], out)
        recurse_color_combinations(color[1:], prefix, out)
        out.append(prefix+color[0])
    return out

def get_all_color_combinations():
    combinations = recurse_color_combinations("wubrg", "", [])
    return sorted(combinations, key=lambda i: len(i))

def sort_color_str(color_str):
    return "".join(sorted(color_str.lower()))

def transform_deck_name(deck_name):
    """Convert a deck name to a canonical form. The canonical form contains only
    lower-cased letters and is sorted in alphabetical order. This allows,
    for example, Chain Veil Teferi and Teferi Chain Veil to match to the same deck."""

    sorted_name = "".join(sorted(deck_name.lower()))
    letters_only = re.search(r"([a-z]*)$", sorted_name).group()
    return letters_only