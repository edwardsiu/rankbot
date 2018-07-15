from src import table

# deck data processing
def process_match_stats(matches):
    decks = {}
    for match in matches:
        for player in match["decks"]:
            deck_name = match["decks"][player]
            if deck_name in decks:
                decks[deck_name]["entries"] += 1
                decks[deck_name]["players"].add(player)
            else:
                decks[deck_name] = {
                    "deck_name": deck_name,
                    "entries": 1,
                    "players": {player},
                    "wins": 0
                }
                if not deck_name:
                    decks[deck_name]["deck_name"] = "Unknown"
        winning_player = match["winner"]
        winning_deck = match["decks"][winning_player]
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

def make_deck_table(data):
    headings = ["Deck", "Games", "Wins", "Win %", "# Pilots", "Meta %"]
    rows = []
    total_entries = 0
    for deck in data:
        total_entries += deck["entries"]
    for deck in data:
        row = [
            deck["deck_name"],
            deck["entries"],
            deck["wins"],
            "{:.3f}%".format(100*deck["wins"]/deck["entries"]),
            len(deck["players"]),
            "{:.3f}%".format(100*deck["entries"]/total_entries)
        ]
        rows.append(row)
    tables = []
    table_height = 10
    for i in range(0, len(data), table_height):
        tables.append(table.make_table(headings, rows[i:i+table_height]))
    return tables