import re
import requests

from app import exceptions as err
from app.utils.deckhosts import deck_utils

def _get_card_name(line):
    name = re.search(r"\D+", line).group()
    return name

def _parse_decklist(dlist):
    lines = dlist.split('\n')
    decklist = []
    idx = -1
    for line in lines:
        if not line.strip():
            continue
        if re.match(r'\D', line):
            category = line.strip()
            decklist.append({"category": category, "cards": []})
            idx += 1
        else:
            match = re.search(r'\d+', line)
            if not match:
                continue
            count = match.group()
            name = _get_card_name(line)
            decklist[idx]['cards'].append({"name": name, "count": int(count)})
    return deck_utils.sort_categories(decklist)

def search(link):
    r = requests.get(f"{link}?export_txt=1")
    cmdr_names = []
    try:
        match = re.findall(r"Commander.*((\n[\w ,']*)+)", r.text)[0][0]
        _cmdrs = match.strip().split('\n')
        for _cmdr in _cmdrs:
            name = _get_card_name(_cmdr)
            cmdr_names.append(name)
    except Exception as e:
        logging.error(e)
        raise err.DeckNotFoundError()
    return {"commanders": cmdr_names, "decklist": _parse_decklist(r.text)}
