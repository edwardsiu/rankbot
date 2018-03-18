def generate_game_id(hasher, msg_id):
    hash_id = hasher.encode(int(msg_id))
    return hash_id[:4]
