import logging
import re
import requests

from app import exceptions as err
from app.utils import scryfall, utils
from app.utils.deckhosts import deckstats, tappedout, moxfield

def sort_categories(decklist):
    """Sort by number of rows so that the discord embed places
    long categories next to each other. This makes the embed more space efficient."""

    return sorted(decklist, key=lambda o: len(o['cards']), reverse=True)

def _get_color_identity(commanders):
    colors = []
    for commander in commanders:
        if commander:
            colors += commander["color_identity"]
    return utils.sort_color_str("".join(set(colors)))

def extract(link):
    if "tappedout" in link:
        deck = tappedout.search(link)
    elif "deckstats" in link:
        deck = deckstats.search(link)
    elif "moxfield" in link:
        deck = moxfield.search(link)
    else:
        raise err.DeckNotFoundError()

    commanders = [scryfall.search(cmdr_name) for cmdr_name in deck["commanders"]]
    color_identity = _get_color_identity(commanders)
    deck["commanders"] = commanders
    deck["color_identity"] = color_identity
    return deck
