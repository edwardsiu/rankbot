import re
import requests

from app import exceptions as err
from app.utils.deckhosts import deck_utils

def _parse_decklist(decklist):
    parsed = []
    # parsed = [{"category": "name", "cards": []}]
    # cards = [{"name": "name", "count": 1}]
    # categories = {}
    # for card_name in decklist["mainboard"]:
    #     card = decklist["mainboard"][card_name]
    return deck_utils.sort_categories(parsed)

def search(link):
    deck_id_match = re.search(r'(?<=decks\/)[\w\d]+', link)
    if not deck_id_match:
        return []
    deck_id = deck_id_match.group()
    r = requests.get(f"https://api.moxfield.com/v1/decks/all/{deck_id}")
    cmdr_names = []
    decklist = r.json()
    if "commander" not in decklist:
        raise err.DeckNotFoundError()
    cmdr_names.append(decklist["commander"]["name"])
    if ("partner" in decklist):
        cmdr_names.append(decklist["partner"]["name"])
    return {"commanders": cmdr_names, "decklist": _parse_decklist(decklist)}
