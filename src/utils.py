from math import ceil

def generate_game_id(hasher, msg_id, matches):
    msg_id = int(msg_id)
    while(True):
        game_id = hasher.encode(msg_id)[:4].lower()
        if not matches.find_one({"game_id": game_id}):
            return game_id
        msg_id -= 1

def update_score(match, members):
    winner = members.find_one({"user_id": match["winner"]})
    losers = [
        members.find_one({"user_id": player}) 
        for player in match["players"] if player != match["winner"]]
    gains = 0
    delta = []
    for player in losers:
        loss = ceil(player["points"]/100)
        gains += loss
        members.update_one(
            {"user_id": player["user_id"]},
            {
                "$inc": {
                    "points": -loss,
                    "losses": 1
                }
            }
        )
        delta.append({"player": player["user"], "change": -loss})
    members.update_one(
        {"user_id": match["winner"]},
        {
            "$inc": {
                "points": gains,
                "wins": 1
            }
        }
    )
    delta.append({"player": winner["user"], "change": gains})
    return delta