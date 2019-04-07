from datetime import datetime
import re
import statsmodels.stats.proportion as stats

from app.constants import status_codes as stc
from app.constants import system
from app.utils import embed, line_table

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
    Searches through all the args for an integer"""

    for arg in args:
        if arg.isdigit():
            return int(re.match(r"\d*", arg).group())
    return DEFAULT_LIMIT

# deck data processing
def get_match_stats(ctx):
    matches = ctx.bot.db.find_matches(
        {
            "timestamp": {"$gt": system.deck_tracking_start_date}, 
            "status": stc.ACCEPTED
        }, ctx.message.guild)
    if not matches:
        return None
    return process_match_stats(ctx, matches)

def get_player_match_stats(ctx, user):
    matches = ctx.bot.db.find_matches(
        {
            "timestamp": {"$gt": system.deck_tracking_start_date},
            "status": stc.ACCEPTED,
            "players.user_id": user.id
        }, ctx.message.guild
    )
    if not matches:
        return None
    return process_player_match_stats(ctx, user, matches)

def get_deck_short_name(ctx, deck_name, cache):
    if len(deck_name) <= 18:
        # already short enough
        return deck_name
    if deck_name not in cache:
        cache[deck_name] = ctx.bot.db.get_deck_short_name(deck_name)
    return cache[deck_name]

def process_match_stats(ctx, matches):
    decks = {}
    name_cache = {}
    for match in matches:
        for player in match["players"]:
            deck_name = player["deck"]
            if not deck_name:
                deck_name = "Unknown"
            deck_name = get_deck_short_name(ctx, deck_name, name_cache)
            if deck_name in decks:
                decks[deck_name]["entries"] += 1
                decks[deck_name]["players"].add(player["user_id"])
            else:
                decks[deck_name] = {
                    "name": deck_name,
                    "entries": 1,
                    "players": {player["user_id"]},
                    "wins": 0
                }
        winning_deck = get_deck_short_name(ctx, match["winning_deck"], name_cache)
        decks[winning_deck]["wins"] += 1
    total_entries = sum([decks[deck_name]['entries'] for deck_name in decks])
    deck_match_threshold = ctx.bot.db.get_deck_match_threshold(ctx.message.guild)
    list_decks = [decks[i] for i in decks if (i != "Unknown" and decks[i]["entries"] >= deck_match_threshold)]
    for deck in list_decks:
        deck["winrate"] = deck["wins"]/deck["entries"]
        deck["meta"] = deck["entries"]/total_entries
        deck["losses"] = deck["entries"] - deck["wins"]
    return list_decks

def process_player_match_stats(ctx, user, matches):
    decks = {}
    name_cache = {}
    for match in matches:
        deck_name = get_player_deck(user.id, match)
        deck_name = get_deck_short_name(ctx, deck_name, name_cache)
        if deck_name in decks:
            decks[deck_name]["entries"] += 1
            decks[deck_name]["wins"] += 1 if match["winner"] == user.id else 0
        else:
            decks[deck_name] = {
                "name": deck_name,
                "entries": 1,
                "wins": 1 if match["winner"] == user.id else 0
            }
    list_decks = decks.values()
    for deck in list_decks:
        deck["winrate"] = deck["wins"]/deck["entries"]
        deck["losses"] = deck["entries"] - deck["wins"]
    return list_decks

def sort_by_entries(data):
    return sorted(data, key=lambda deck: deck["entries"], reverse=True)

def sort_by_wins(data):
    return sorted(data, key=lambda deck: deck["wins"], reverse=True)

def sort_by_winrate(data):
    return sorted(data, key=lambda deck: deck["winrate"], reverse=True)

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

def get_appearances(match, deck_name):
    """Counts the number of times deck_name shows up in a match"""

    return sum([1 if player["deck"] == deck_name else 0
        for player in match['players']])

def confint_95(success, samples):
    """Uses Clopper-Pearson method with 95% confidence"""

    return stats.proportion_confint(
        success, samples, alpha=0.05, method='beta')

def confint_95_diff(success, samples):
    """Return the +/- value on the proportion for a 90% confint"""

    proportion = success/samples
    return confint_95(success, samples)[1] - proportion

def date_from_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")

def short_date_from_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%m/%d")

def get_winner_name(match):
    return next((i['name'] for i in match['players'] if i['user_id'] == match['winner']),"N/A")

def get_player_deck(user_id, match):
    return next((i['deck'] for i in match['players'] if i['user_id'] == user_id), "N/A")

def shorten_deck_name(ctx, name, maxlen=16):
    if len(name) <= maxlen:
        return name
    shortened = ctx.bot.db.get_deck_short_name(name)
    if len(shortened) <= maxlen:
        return shortened
    return shortened[:(maxlen-3)] + "..."

def shorten_player_name(name, maxlen=16):
    if len(name) <= maxlen:
        return name
    tokens = name.split()
    if len(tokens[0]) <= maxlen:
        return tokens[0]
    return tokens[0][:(maxlen-3)] + "..."

def make_leaderboard_table(players, key, title):
    rows = []
    if key == "winrate":
        for i, player in enumerate(players):
            rows.append([
                f"{i+1}.", 
                player['name'], 
                f"{100*player['wins']/player['accepted']:.3g}%"])
    else:
        for i, player in enumerate(players):
            rows.append([f"{i+1}.", player['name'], str(player[key])])
    if not rows:
        return None
    return line_table.LineTable(rows, title=title)

def player_accumulator(A, B):
    for player in B["players"]:
        if player["deck"] == A["deck_name"]:
            if player["user_id"] not in A["data"]:
                A["data"][player["user_id"]] = {"name": player["name"], "wins": 0, "losses": 0, "games": 1}
            else:
                A["data"][player["user_id"]]["games"] += 1
            if player["user_id"] == B["winner"]:
                A["data"][player["user_id"]]["wins"] += 1
            else:
                A["data"][player["user_id"]]["losses"] += 1
    return A
