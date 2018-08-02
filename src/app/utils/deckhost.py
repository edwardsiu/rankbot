import logging
import re
import requests

from app import exceptions as err
from app.utils import utils

def _search_scryfall(card_name):
    try:
        params = {"fuzzy": card_name}
        r = requests.get("https://api.scryfall.com/cards/named", params=params)
    except Exception as e:
        logging.error(e)
        raise err.CardNotFoundError()
    else:
        return r.json()

def _search_tappedout(link):
    _slug_match = re.search(r'(?<=mtg-decks/).*?(?=/)', link)
    if not _slug_match:
        return []
    slug = _slug_match.group()
    r = requests.get(f"http://tappedout.net/mtg-decks/{slug}/?fmt=markdown")
    cmdr_names = []
    try:
        match = re.findall(r'### Commander.*((\n[*] 1.*)+)', r.text)[0][0]
        _cmdrs = match.strip().split('\n')
        for _cmdr in _cmdrs:
            name = re.search(r'\[.*?\]', _cmdr).group()[1:-1]
            cmdr_names.append(name)
    except Exception as e:
        logging.error(e)
        raise err.DeckNotFoundError()
    return cmdr_names

def _search_deckstats(link):
    r = requests.get(f"{link}?export_txt=1")
    cmdr_names = []
    try:
        match = re.findall(r"Commander.*((\n[\w ,']*)+)", r.text)[0][0]
        _cmdrs = match.strip().split('\n')
        for _cmdr in _cmdrs:
            name = re.search(r"\D+", commander).group()
            cmdr_names.append(name)
    except Exception as e:
        logging.error(e)
        raise err.DeckNotFoundError()
    return cmdr_names

def _get_color_identity(commanders):
    colors = []
    for commander in commanders:
        if commander:
            colors += commander["color_identity"]
    return utils.sort_color_str("".join(colors))

def parse_deck(link):
    if "tappedout" in link:
        cmdr_names = _search_tappedout(link)
    elif "deckstats" in link:
        cmdr_names = _search_deckstats(link)
    else:
        return None
    if not cmdr_names:
        return None

    commanders = [_search_scryfall(cmdr_name) for cmdr_name in cmdr_names]
    color_identity = _get_color_identity(commanders)
    if not color_identity:
        return None
    return (color_identity, commanders)
