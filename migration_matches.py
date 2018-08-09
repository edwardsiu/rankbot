from pymongo import MongoClient

# python -m pip install -U https://github.com/Rapptz/discord.py/archive/rewrite.zip#egg=discord.py

client = MongoClient("localhost", 27017)
for shard in ["390254034289819669"]:
    db = client[shard]
    matches = db.matches.find()
    for match in matches:
        db.matches.replace_one({"game_id": match["game_id"]},
        {
            "game_id": match["game_id"],
            "timestamp": match["timestamp"],
            "status": match["status"],
            "winner": match["winner"],
            "players": [
                {
                    "user_id": int(player_id),
                    "name": db.members.find_one({"user_id": int(player_id)})["name"],
                    "deck": match["decks"][player_id],
                    "confirmed": match["players"][player_id] == "CONFIRMED"
                } for player_id in match["players"].keys()
            ]
        })
    db.matches.create_index("players")
    
