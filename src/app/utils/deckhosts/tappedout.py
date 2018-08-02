import re
import requests

from app import exceptions as err
from app.utils.deckhosts import deck_utils

def _get_card_name(line):
    name = re.search(r'\[.*?\]', line).group()[1:-1]
    return name

def _parse_decklist(dlist):
    lines = dlist.split('\n')
    decklist = []
    idx = -1
    for line in lines:
        if not line.strip():
            continue
        if re.match(r'### ', line):
            category = re.search(r"[a-zA-Z]+", line).group()
            decklist.append({"category": category, "cards": []})
            idx += 1
        elif re.match(r'[*]', line):
            match = re.search(r'\d+', line)
            if not match:
                continue
            count = match.group()
            name = _get_card_name(line)
            decklist[idx]['cards'].append({"name": name, "count": int(count)})
    return deck_utils.sort_categories(decklist)

def search(link):
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
            name = _get_card_name(_cmdr)
            cmdr_names.append(name)
    except Exception as e:
        logging.error(e)
        raise err.DeckNotFoundError()
    return {"commanders": cmdr_names, "decklist": _parse_decklist(r.text)}
