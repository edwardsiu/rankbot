import requests

from app import exceptions as err

def search(card_name):
    try:
        params = {"fuzzy": card_name}
        r = requests.get("https://api.scryfall.com/cards/named", params=params)
    except Exception as e:
        logging.error(e)
        raise err.CardNotFoundError()
    else:
        return r.json()
