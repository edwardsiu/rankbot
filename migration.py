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
                    "user_id": int(member["user_id"])
                #},
                #"$rename": {
                #    "user": "name"
                }
            })
