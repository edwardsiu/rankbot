import time

import discord
from pymongo import MongoClient, DESCENDING
from src import status_codes as stc

"""PRECOND: All messages that are to be processed are received in a server rather than DM"""

class RankDB(MongoClient):
    def get_db(self, guild_id):
        return self[str(guild_id)]

    def get_members(self, guild_id):
        db = self.get_db(guild_id)
        return db.members

    def get_matches(self, guild_id):
        db = self.get_db(guild_id)
        return db.matches

    def get_guild(self, guild_id):
        db = self.get_db(guild_id)
        return db.server

    def set_admin_role(self, role_name, guild):
        settings_collection = self.get_guild(guild.id)
        if not settings_collection.find_one({}):
            settings_collection.insert_one({"admin": role_name})
        else:
            settings_collection.update_one(
                {},
                {
                    "$set": {"admin": role_name}
                }
            )

    def get_admin_role(self, guild):
        settings_collection = self.get_guild(guild.id)
        guild_config = settings_collection.find_one({})
        if not guild_config or "admin" not in guild_config:
            return None
        return discord.utils.get(guild.roles, name=guild_config["admin"])


    # Player methods
    def add_member(self, user, guild):
        members = self.get_members(guild.id)
        if not self.find_member(user, guild):
            data = {
                "name": user.name,  # string
                "user_id": user.id, # int (was string)
                "points": 1000,
                "pending": [],
                "accepted": 0,
                "wins": 0,
                "losses": 0,
                "deck": ""
            }
            members.insert_one(data)
            return True
        return False

    def delete_member(self, user, server_id):
        members = self.get_members(server_id)
        return members.find_one_and_delete({"user_id": user.id})

    def find_member(self, user, guild):
        members = self.get_members(guild.id)
        return members.find_one({"user_id": user.id})

    def find_member_by_id(self, user_id, guild):
        members = self.get_members(guild.id)
        return members.find_one({"user_id": user_id})

    def find_members(self, query, guild, limit=0):
        members = self.get_members(guild.id)
        return members.find(query, limit=limit)

    def find_top_members_by(self, sort_key, guild, limit=0):
        members = self.get_members(guild.id)
        return members.find({"accepted": {"$gt": 4}}, limit=limit, sort=[(sort_key, DESCENDING)])


    # Match methods
    def add_pending_match(self, game_id, user, guild):
        members = self.get_members(guild.id)
        members.update_one(
            {"user_id": user.id},
            {
                "$push": {"pending": game_id}
            }
        )
    
    def remove_pending_match(self, game_id, user_id, guild):
        members = self.get_members(guild.id)
        members.update_one(
            {"user_id": user_id},
            {
                "$pull": {"pending": game_id}
            }
        )
    
    def member_inc_accepted(self, member_id, guild):
        members = self.get_members(guild.id)
        res = members.update_one(
            {"user_id": int(member_id)},
            {
                "$inc": {"accepted": 1}
            }
        )

    def reset_scores(self, server_id):
        members = self.get_members(server_id)
        members.update_many({}, {
            "$set": {
                "points": 1000,
                "accepted": 0,
                "pending": [],
                "wins": 0,
                "losses": 0
            }
        })

    def add_match(self, game_id, winner, players, guild):
        matches = self.get_matches(guild.id)
        pending_record = {
            "game_id": game_id,
            "status": stc.PENDING,
            "winner": winner.id,
            "players": {str(user.id): stc.UNCONFIRMED for user in players},
            "decks": {str(user.id): "" for user in players},
            "timestamp": time.time()
        }
        matches.insert_one(pending_record)
        for user in players:
            self.add_pending_match(game_id, user, guild)

    def delete_match(self, game_id, guild):
        members = self.get_members(guild.id)
        members.update_many({"pending": game_id},{"$pull":{"pending": game_id}})
        matches = self.get_matches(guild.id)
        matches.delete_one({"game_id": game_id})

    def find_match(self, game_id, guild):
        matches = self.get_matches(guild.id)
        return matches.find_one({"game_id": game_id})

    def find_matches(self, query, guild, limit=0):
        matches = self.get_matches(guild.id)
        return matches.find(query, limit=limit, sort=[("timestamp", DESCENDING)])

    def find_member_matches(self, member, guild, limit=0):
        return self.find_matches(
            {"players.{}".format(member["user_id"]): {"$exists": True}}, guild, limit)

    def reset_matches(self, server_id):
        matches = self.get_matches(server_id)
        matches.delete_many({})

    def count_matches(self, server_id):
        matches = self.get_matches(server_id)
        return matches.count({"status": stc.PENDING}), matches.count({"status": stc.ACCEPTED})

    def set_match_status(self, status, game_id, guild):
        matches = self.get_matches(guild.id)
        matches.update_one(
            {"game_id": game_id},
            {
                "$set": {"status": status}
            }
        )

    def confirm_player(self, deck_name, game_id, user, guild):
        matches = self.get_matches(guild.id)
        matches.update_one(
            {"game_id": game_id},
            {
                "$set": {
                    f"players.{user.id}": stc.CONFIRMED,
                    f"decks.{user.id}": deck_name
                }
            }
        )

    def confirm_all_players(self, game_id, user_ids, guild):
        matches = self.get_matches(guild.id)
        matches.update_one(
            {"game_id": game_id},
            {
                "$set": {
                    f"players.{user_id}": stc.CONFIRMED for user_id in user_ids
                }
            }
        )

    def unconfirm_player(self, user_id, game_id, server_id):
        matches = self.get_matches(server_id)
        matches.update_one(
            {"game_id": game_id},
            {
                "$set": {"players.{}".format(user_id): stc.UNCONFIRMED}
            }
        )

    def check_match_status(self, game_id, guild):
        match = self.find_match(game_id, guild)
        players = match["players"]
        if match["status"] == stc.ACCEPTED:
            return None
        for user_id in players:
            if players[user_id] == stc.UNCONFIRMED:
                return None
        # all players have confirmed the result
        self.set_match_status(stc.ACCEPTED, game_id, guild)
        delta = self.update_scores(match, guild)
        for user_id in players:
            self.member_inc_accepted(user_id, guild)
        members = self.get_members(guild.id)
        members.update_many({"pending": game_id}, {"$pull": {"pending": game_id}})
        return delta

    def get_game_id(self, hasher, msg_id, guild):
        while(True):
            game_id = hasher.encode(msg_id)[:4].lower()
            if not self.find_match(game_id, guild):
                return game_id
            msg_id -= 1

    def update_scores(self, match, guild):
        members = self.get_members(guild.id)
        winner = self.find_member_by_id(match["winner"], guild)
        losers = [
            self.find_member_by_id(int(member_id), guild)
            for member_id in match["players"] if int(member_id) != match["winner"]]
        gains = 0
        delta = []
        for member in losers:
            avg_opponent_score = (sum([i["points"] for i in losers if i != member]) + winner["points"])/3.0
            score_diff = member["points"] - avg_opponent_score
            loss = int(round(12.0/(1+1.0065**(-score_diff)) + 4))
            gains += loss
            members.update_one(
                {"user_id": member["user_id"]},
                {
                    "$inc": {
                        "points": -loss,
                        "losses": 1
                    }
                }
            )
            delta.append({"player": member["name"], "change": -loss})
        members.update_one(
            {"user_id": match["winner"]},
            {
                "$inc": {
                    "points": gains,
                    "wins": 1
                }
            }
        )
        delta.append({"player": winner["name"], "change": gains})
        return delta

    
    # Deck methods
    def set_deck(self, user_id, deck_name, server_id):
        members = self.get_members(server_id)
        members.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "deck": deck_name
                }
            }
        )
