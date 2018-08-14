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

def get_image_uris(card):
    if "card_faces" in card:
        return card['card_faces'][0]['image_uris']
    return card['image_uris']
