from src import database
from pymongo import MongoClient, ASCENDING
from src import status_codes as stc

#server_id = "113555415446413312"
server_id = "390254034289819669"

def update_score(match):
    members = db.get_members(server_id)
    winner = db.find_member(match["winner"], server_id)
    losers = [
        db.find_member(player, server_id)
        for player in match["players"] if player != match["winner"]]
    gains = 0
    delta = []
    for player in losers:
        modifier = int(round(0.05 * (player["points"] - winner["points"])))
        loss = 10 + modifier
        if loss < 3:
            loss = 3
        elif loss > 17:
            loss = 17
        gains += loss
        members.update_one(
            {"user_id": player["user_id"]},
            {
                "$inc": {
                    "points": -loss
                }
            }
        )
    members.update_one(
        {"user_id": match["winner"]},
        {
            "$inc": {
                "points": gains
            }
        }
    )


db = database.RankDB("localhost", 27017)
members = db.get_members(server_id)
members.update_many({}, {
    "$set": {
        "points": 1000
    }
})
matches = db.get_matches(server_id) #cedh server
sorted_matches = matches.find({"status": stc.ACCEPTED}, sort=[("timestamp", ASCENDING)])
for match in sorted_matches:
    update_score(match)
