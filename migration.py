from pymongo import MongoClient

# python -m pip install -U https://github.com/Rapptz/discord.py/archive/rewrite.zip#egg=discord.py

client = MongoClient("localhost", 27017)
for shard in ["390254034289819669"]:
    db = client[shard]
    # migrate user id snowflakes
    members = db.members.find()
    for member in members:
        db.members.update_one({"user_id": member["user_id"]},
        {
            "$set": {
                "user_id": int(member["user_id"]),
                "deck": ""
            },
            "$rename": {
                "user": "name"
            }
        })
    db.members.create_index("user_id")
    matches = db.matches.find()
    for match in matches:
        if "decks" in match:
            db.matches.update_one({"game_id": match["game_id"]},
            {
                "$set": {
                    "winner": int(match["winner"])
                }
            })
        else:
            db.matches.update_one({"game_id": match["game_id"]},
            {
                "$set": {
                    "winner": int(match["winner"]),
                    "decks": {
                        user_id: "" for user_id in match["players"]
                    }
                }
            })
    db.matches.create_index("game_id")
    db.matches.create_index("status")
    
