from time import time

import discord
from pymongo import MongoClient, DESCENDING
from src import status_codes as stc

"""PRECOND: All messages that are to be processed are received in a server rather than DM"""

class RankDB(MongoClient):
    def get_db(self, server_id):
        return self[server_id]

    def get_members(self, server_id):
        db = self.get_db(server_id)
        return db.members

    def get_matches(self, server_id):
        db = self.get_db(server_id)
        return db.matches

    def get_server(self, server_id):
        db = self.get_db(server_id)
        return db.server

    def set_admin_role(self, role_name, server_id):
        server_settings = self.get_server(server_id)
        if not server_settings.find_one({}):
            server_settings.insert_one({"admin": role_name})
        else:
            server_settings.update_one(
                {},
                {
                    "$set": {"admin": role_name}
                }
            )

    def get_admin_role(self, server):
        server_settings = self.get_server(server.id)
        setting = server_settings.find_one({})
        if not setting or "admin" not in setting:
            return None
        return discord.utils.get(server.roles, name=setting["admin"])

    def is_admin(self, user_roles, server_id):
        server_settings = self.get_server(server_id)
        setting = server_settings.find_one({})
        if not setting or not setting["admin"]:
            return False
        return setting["admin"] in user_roles

    def add_member(self, user, server_id):
        members = self.get_members(server_id)
        if not self.find_member(user.id, server_id):
            data = {
                "user": user.name,
                "user_id": user.id,
                "points": 1000,
                "pending": [],
                "accepted": 0,
                "wins": 0,
                "losses": 0
            }
            members.insert_one(data)
            return True
        return False

    def count_members(self, server_id):
        members = self.get_members(server_id)
        return members.count()

    def delete_member(self, user, server_id):
        members = self.get_members(server_id)
        return members.find_one_and_delete({"user_id": user.id})

    def find_member(self, user_id, server_id):
        members = self.get_members(server_id)
        return members.find_one({"user_id": user_id})

    def find_all_members(self, server_id):
        members = self.get_members(server_id)
        return members.find()

    def find_top_players(self, limit, server_id, key):
        members = self.get_members(server_id)
        return members.find({"accepted": {"$gt": 0}}, limit=limit, sort=[(key, DESCENDING)])

    def add_pending_match(self, user_id, game_id, server_id):
        members = self.get_members(server_id)
        members.update_one(
            {"user_id": user_id},
            {
                "$push": {"pending": game_id}
            }
        )
    
    def remove_pending_match(self, user_id, game_id, server_id):
        members = self.get_members(server_id)
        members.update_one(
            {"user_id": user_id},
            {
                "$pull": {"pending": game_id}
            }
        )
    
    def member_inc_accepted(self, user_id, server_id):
        members = self.get_members(server_id)
        members.update_one(
            {"user_id": user_id},
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

    def add_match(self, game_id, winner, players, server_id):
        matches = self.get_matches(server_id)
        pending_record = {
            "game_id": game_id,
            "status": stc.PENDING,
            "winner": winner.id,
            "players": {u.id: stc.UNCONFIRMED for u in players},
            "timestamp": time()
        }
        pending_record["players"][winner.id] = stc.CONFIRMED
        matches.insert_one(pending_record)
        for player in players:
            self.add_pending_match(player.id, game_id, server_id)

    def delete_match(self, game_id, server_id):
        members = self.get_members(server_id)
        members.update_many({"pending": game_id},{"$pull":{"pending": game_id}})
        matches = self.get_matches(server_id)
        matches.delete_one({"game_id": game_id})

    def find_match(self, game_id, server_id):
        matches = self.get_matches(server_id)
        return matches.find_one({"game_id": game_id})

    def find_matches(self, match_filter, server_id):
        matches = self.get_matches(server_id)
        return matches.find(match_filter)

    def find_recent_player_matches(self, user_id, limit, server_id):
        matches = self.get_matches(server_id)
        return matches.find({"players.{}".format(user_id): {"$exists": True}}, limit=limit, sort=[("timestamp", DESCENDING)])

    def find_player_pending(self, user_id, server_id):
        player = self.find_member(user_id, server_id)
        if not player:
            return []
        matches = [self.find_match(game_id, server_id) for game_id in player["pending"]]
        return matches

    def reset_matches(self, server_id):
        matches = self.get_matches(server_id)
        matches.delete_many({})

    def count_matches(self, server_id):
        matches = self.get_matches(server_id)
        return matches.count({"status": stc.PENDING}), matches.count({"status": stc.ACCEPTED})

    def set_match_status(self, status, game_id, server_id):
        matches = self.get_matches(server_id)
        matches.update_one(
            {"game_id": game_id},
            {
                "$set": {"status": status}
            }
        )

    def confirm_player(self, user_id, game_id, server_id):
        matches = self.get_matches(server_id)
        matches.update_one(
            {"game_id": game_id},
            {
                "$set": {"players.{}".format(user_id): stc.CONFIRMED}
            }
        )

    def confirm_all_players(self, players, game_id, server_id):
        matches = self.get_matches(server_id)
        matches.update_one(
            {"game_id": game_id},
            {
                "$set": {
                    "players.{}".format(p_id): stc.CONFIRMED for p_id in players
                }
            }
        )

    def unconfirm_player(self, user_id, game_id, server_id):
        matches = self.get_matches(server_id)
        matches.update_one(
            {"game_id": game_id},
            {
                "$set": {"players.{}".format(user_id): stc.CONFIRMED}
            }
        )

    def check_match_status(self, game_id, server_id):
        match = self.find_match(game_id, server_id)
        players = match["players"]
        if match["status"] == stc.ACCEPTED:
            return None
        for player in players:
            if players[player] == stc.UNCONFIRMED:
                return None
        # all players have confirmed the result
        self.set_match_status(stc.ACCEPTED, game_id, server_id)
        delta = self.update_scores(match, server_id)
        for player_id in players:
            self.member_inc_accepted(player_id, server_id)
        members = self.get_members(server_id)
        members.update_many({"pending": game_id}, {"$pull": {"pending": game_id}})
        return delta

    def get_game_id(self, hasher, msg_id, server_id):
        msg_id = int(msg_id)
        while(True):
            game_id = hasher.encode(msg_id)[:4].lower()
            if not self.find_match(game_id, server_id):
                return game_id
            msg_id -= 1

    def update_scores(self, match, server_id):
        members = self.get_members(server_id)
        winner = self.find_member(match["winner"], server_id)
        losers = [
            self.find_member(player, server_id)
            for player in match["players"] if player != match["winner"]]
        gains = 0
        delta = []
        for player in losers:
            avg_opponent_score = (sum([i["points"] for i in losers if i != player]) + winner["points"])/3.0
            score_diff = player["points"] - avg_opponent_score
            loss = int(round(6.0/(1+1.025**(-score_diff)) + 7))
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
