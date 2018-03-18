def generate_game_id(hasher, msg_id, matches):
    msg_id = int(msg_id)
    while(True):
        game_id = hasher.encode(msg_id)[:4].lower()
        if not matches.find_one({"game_id": game_id}):
            return game_id
        msg_id -= 1
