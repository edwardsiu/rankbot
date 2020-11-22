import re
import requests

from app import exceptions as err
from app.utils.deckhosts import deck_utils

TYPE_MAP = {
    "1": "Planeswalker",
    "2": "Creature",
    "3": "Sorcery",
    "4": "Instant",
    "5": "Artifact",
    "6": "Enchantment",
    "7": "Land",
}

def _parse_decklist(decklist):
    extracted = [
        {
            "category": TYPE_MAP[decklist[card_name]["card"]["type"]],
            "name": card_name,
            "count": decklist[card_name]["quantity"],
        } for card_name in decklist
    ]
    category_map = {}
    for card in extracted:
        card_category = card["category"]
        if card_category not in category_map:
            category_map[card_category] = []
        category_map[card_category].append({ "name": card["name"], "count": card["count"] })
    parsed = [{"category": category, "cards": category_map[category]} for category in category_map]
    return deck_utils.sort_categories(parsed)

def search(link):
    deck_id_match = re.search(r'(?<=decks\/)[\w\d_-]+', link)
    if not deck_id_match:
        return []
    deck_id = deck_id_match.group()
    r = requests.get(f"https://api.moxfield.com/v2/decks/all/{deck_id}")
    decklist = r.json()
    if "commanders" not in decklist:
        raise err.DeckNotFoundError()
    cmdr_names = [card_name for card_name in decklist["commanders"]]
    return {"commanders": cmdr_names, "decklist": _parse_decklist(decklist["mainboard"])}
