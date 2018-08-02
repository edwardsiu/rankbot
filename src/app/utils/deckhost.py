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

def _get_card_name_tappedout(line):
    name = re.search(r'\[.*?\]', line).group()[1:-1]
    return name

def _get_card_name_deckstats(line):
    name = re.search(r"\D+", line).group()
    return name

def _parse_tappedout_decklist(dlist):
    lines = dlist.split('\n')
    decklist = {}
    current_key = ""
    for line in lines:
        if not line.strip():
            continue
        if re.match(r'### ', line):
            current_key = re.search(r"[a-zA-Z]+", line).group()
            decklist[current_key] = []
        elif re.match(r'[*]', line):
            match = re.search(r'\d+', line)
            if not match:
                continue
            count = match.group()
            name = _get_card_name_tappedout(line)
            decklist[current_key].append(f'{count} {name}')
            
    return decklist

def _parse_deckstats_decklist(dlist):
    lines = dlist.split('\n')
    decklist = {}
    current_key = ""
    for line in lines:
        if not line.strip():
            continue
        if re.match(r'\D', line):
            current_key = line.strip()
            decklist[current_key] = []
        else:
            decklist[current_key].append(line)
    return decklist

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
            name = _get_card_name_tappedout(_cmdr)
            cmdr_names.append(name)
    except Exception as e:
        logging.error(e)
        raise err.DeckNotFoundError()
    return {"commanders": cmdr_names, "decklist": _parse_tappedout_decklist(r.text)}

def _search_deckstats(link):
    r = requests.get(f"{link}?export_txt=1")
    cmdr_names = []
    try:
        match = re.findall(r"Commander.*((\n[\w ,']*)+)", r.text)[0][0]
        _cmdrs = match.strip().split('\n')
        for _cmdr in _cmdrs:
            name = _get_card_name_deckstats(_cmdr)
            cmdr_names.append(name)
    except Exception as e:
        logging.error(e)
        raise err.DeckNotFoundError()
    return {"commanders": cmdr_names, "decklist": _parse_deckstats_decklist(r.text)}

def _get_color_identity(commanders):
    colors = []
    for commander in commanders:
        if commander:
            colors += commander["color_identity"]
    return utils.sort_color_str("".join(colors))

def parse_deck(link):
    if "tappedout" in link:
        deck = _search_tappedout(link)
    elif "deckstats" in link:
        deck = _search_deckstats(link)
    else:
        return None
    if not deck:
        return None

    commanders = [_search_scryfall(cmdr_name) for cmdr_name in deck["commanders"]]
    color_identity = _get_color_identity(commanders)
    if not color_identity:
        return None
    deck["commanders"] = commanders
    deck["color_identity"] = color_identity
    return deck
