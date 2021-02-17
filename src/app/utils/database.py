import time

import discord
from pymongo import MongoClient, DESCENDING
from app.constants import status_codes as stc
from app.constants import system
from app.utils import utils

"""PRECOND: All messages that are to be processed are received in a server rather than DM

Config: {
    admin: str,
    player_match_threshold: int,
    deck_match_threshold: int
}

Seasons: {
    start_time: int,
    end_time: int,
    season_number: int,
    season_leaders: [
        {user_id: int}
    ]
}

Member: {
    name: str,
    user_id: int,
    points: int,
    pending: [str],
    accepted: int,
    wins: int,
    losses: int,
    deck: str,
    season_gold_badges: int,
    season_silver_badges: int,
    season_bronze_badges: int
}

Match: {
    game_id: str,
    winner: int,
    winning_deck: str,
    status: str,
    timestamp: float,
    players: [
        player: {
            name: str,
            user_id: int,
            deck: str,
            confirmed: bool
        }
    ]
}

Deck: {
    name: str,
    aliases: [str],
    canonical_aliases: [str],
    description: str,
    color: str,
    color_name: str
}
"""

class RankDB(MongoClient):
    def guild(self, guild):
        return self[str(guild.id)]

    def members(self, guild):
        db = self.guild(guild)
        return db.members

    def matches(self, guild):
        db = self.guild(guild)
        return db.matches

    def config(self, guild):
        db = self.guild(guild)
        return db.config

    def seasons(self, guild):
        db = self.guild(guild)
        return db.seasons

    def decks(self):
        return self["decks"].decks

    def setup_indices(self, guild):
        self.members(guild).create_index("user_id")
        self.matches(guild).create_index("game_id")
        self.matches(guild).create_index("status")
        self.config(guild).insert_one({
            "admin": "",
            "player_match_threshold": 10,
            "deck_match_threshold": 10
        })
        self.seasons(guild).insert_one({
            "start_time": time.time(),
            "season_number": 1
        })


    # Member methods
    def add_member(self, user, guild):
        if not self.find_member(user.id, guild):
            document = {
                "name": user.name,  # string
                "user_id": user.id, # int (was string)
                "points": system.base_points,
                "pending": [],
                "accepted": 0,
                "wins": 0,
                "losses": 0,
                "deck": "",
                "season_gold_badges": 0,
                "season_silver_badges": 0,
                "season_bronze_badges": 0
            }
            return self.members(guild).insert_one(document)
        return False

    def delete_member(self, user_id, guild):
        return self.members(guild).find_one_and_delete({"user_id": user_id})

    def find_member(self, user_id, guild):
        return self.members(guild).find_one({"user_id": int(user_id)})

    def find_members(self, query, guild, limit=0):
        return self.members(guild).find(query, limit=limit)

    def find_top_members_by(self, sort_key, guild, limit=0, threshold=None):
        if not threshold:
            threshold = self.get_player_match_threshold(guild)
        if sort_key == "winrate":
            members = self.members(guild).find(
                {"accepted": {"$gte": threshold}})
            members = [member for member in members]
            results = sorted(members, key=(lambda o: o['wins']/o['accepted']), reverse=True)
            if not limit:
                return results
            return results[:limit]
        else:
            members = self.members(guild).find(
                {"accepted": {"$gte": threshold}}, 
                limit=limit, sort=[(sort_key, DESCENDING)]
            )
            members = [member for member in members]
            return members

    def push_pending_match(self, game_id, user_ids, guild):
        self.members(guild).update_many(
            {"user_id": {"$in": user_ids}},
            {
                "$push": {"pending": game_id}
            }
        )
    
    def pull_pending_match(self, game_id, guild):
        self.members(guild).update_many(
            {"pending": game_id},
            {
                "$pull": {"pending": game_id}
            }
        )

    # Match methods
    def get_game_id(self, hasher, msg_id, guild):
        while(True):
            game_id = hasher.encode(msg_id)[:4].lower()
            if not self.find_match(game_id, guild):
                return game_id
            msg_id -= 1

    def add_match(self, ctx, winner, users):
        game_id = self.get_game_id(ctx.bot.hasher, ctx.message.id, ctx.message.guild)
        pending_record = {
            "game_id": game_id,
            "status": stc.PENDING,
            "winner": winner.id,
            "winning_deck": "",
            "players": [
                {
                    "user_id": user.id,
                    "name": user.name,
                    "deck": "",
                    "confirmed": False
                } for user in users
            ],
            "timestamp": time.time(),
            "replay_link": ""
        }
        self.matches(ctx.message.guild).insert_one(pending_record)
        self.push_pending_match(game_id, [user.id for user in users], ctx.message.guild)
        return game_id

    def delete_match(self, game_id, guild):
        """This should only be used on unconfirmed matches."""

        self.pull_pending_match(game_id, guild)
        self.matches(guild).delete_one({"game_id": game_id})

    def find_match(self, game_id, guild):
        return self.matches(guild).find_one({"game_id": game_id})

    def find_matches(self, query, guild, limit=0, season=None):
        """season arg will return recent matches by default."""

        if not season:
            return self.matches(guild).find(query, limit=limit, sort=[("timestamp", DESCENDING)])
        else:
            season_info = self.get_season(guild, season)
            if not season_info:
                return None
            if "end_time" in season_info:
                query["timestamp"] = {"$gte": season_info["start_time"], "$lt": season_info["end_time"]}
                return self.matches(guild).find(query, limit=limit, sort=[("timestamp", DESCENDING)])
            query["timestamp"] = {"$gte": season_info["start_time"]}
            return self.matches(guild).find(query, limit=limit, sort=[("timestamp", DESCENDING)])

    def find_matches_with_deck(self, deck_name, guild, limit=0, season=None):
        """season arg will return current season matches by default."""

        return self.find_matches({"players.deck": deck_name}, guild, limit, season)

    def find_user_matches(self, user_id, guild, limit=0):
        return self.find_matches(
            {"players.user_id": user_id}, guild, limit)

    def update_match(self, query, modifier, guild):
        return self.matches(guild).update_one(query, modifier)

    def count_matches(self, query, guild):
        return self.matches(guild).count(query)

    def set_match_status(self, status, game_id, guild):
        self.matches(guild).update_one(
            {"game_id": game_id},
            {
                "$set": {"status": status}
            }
        )

    def confirm_match_for_user(self, game_id, user_id, deck_name, guild):
        match = self.find_match(game_id, guild)
        if user_id == match["winner"]:
            return self.matches(guild).update_one(
                {"game_id": game_id, "players.user_id": user_id},
                {
                    "$set": {
                        "players.$.confirmed": True,
                        "players.$.deck": deck_name,
                        "winning_deck": deck_name
                    }
                }
            )
        else:
            return self.matches(guild).update_one(
                {"game_id": game_id, "players.user_id": user_id},
                {
                    "$set": {
                        "players.$.confirmed": True,
                        "players.$.deck": deck_name
                    }
                }
            )

    def confirm_match_for_users(self, game_id, guild):
        self.matches(guild).update_one(
            {"game_id": game_id, "players.confirmed": False},
            {
                "$set": {
                    "players.$[].confirmed": True
                }
            }
        )

    def unconfirm_match_for_user(self, game_id, user_id, guild):
        self.matches(guild).update_one(
            {"game_id": game_id, "players.user_id": user_id},
            {
                "$set": {
                    "players.$.confirmed": False
                }
            }
        )

    def _find_unconfirmed_player(self, players):
        """Returns the first player that hasn't confirmed a match. Returns None if no players found."""

        return next((i for i in players if not i["confirmed"]), None)

    def check_match_status(self, game_id, guild):
        match = self.find_match(game_id, guild)
        if match["status"] == stc.ACCEPTED:
            return False
        if self._find_unconfirmed_player(match["players"]):
            return False
        # all players have confirmed the result
        self.set_match_status(stc.ACCEPTED, game_id, guild)
        self.members(guild).update_many({"pending": game_id}, {"$inc": {"accepted": 1}})
        delta = self.update_scores(match, guild)
        self.pull_pending_match(game_id, guild)
        return delta

    def update_scores(self, match, guild):
        winner = self.find_member(match["winner"], guild)
        losers = [
            self.find_member(player["user_id"], guild)
            for player in match["players"] if player["user_id"] != match["winner"]]
        gains = 0
        delta = []
        for member in losers:
            avg_opponent_score = (sum([i["points"] for i in losers if i != member]) + winner["points"])/3.0
            score_diff = member["points"] - avg_opponent_score
            loss = int(round(12.0/(1+1.0065**(-score_diff)) + 4))
            gains += loss
            self.members(guild).update_one(
                {"user_id": member["user_id"]},
                {
                    "$inc": {
                        "points": -loss,
                        "losses": 1
                    }
                }
            )
            delta.append({"player": member["name"], "change": -loss})
        self.members(guild).update_one(
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
    def set_deck(self, deck_name, user, guild):
        self.members(guild).update_one(
            {"user_id": user.id},
            {
                "$set": {
                    "deck": deck_name
                }
            }
        )

    def add_deck(self, color, color_name, deck_name, aliases, commanders, link=""):
        decks = self.decks()
        document = {
            "name": deck_name,
            "color": utils.sort_color_str(color),
            "color_name": color_name,
            "link": link,
            "aliases": aliases,
            "canonical_aliases": [utils.transform_deck_name(alias) for alias in aliases],
            "commanders": commanders
        }
        if not decks.find_one({"name": deck_name}):
            decks.insert_one(document)
            return 1
        else:
            decks.find_one_and_replace({"name": deck_name}, document)
            return 0

    def remove_deck(self, deck_name):
        decks = self.decks()
        if not decks.find_one({"name": deck_name}):
            return 0
        decks.delete_one({"name": deck_name})
        return 1

    def find_deck(self, alias):
        if alias.lower() == "rogue":
            return {"name": "Rogue"}
        canonical_name = utils.transform_deck_name(alias)
        return self.decks().find_one({"canonical_aliases": canonical_name})

    def find_decks(self, query):
        return self.decks().find(query)

    def add_deck_aliases(self, alias, new_aliases):
        canonical_name = utils.transform_deck_name(alias)
        new_canonical_aliases = list({utils.transform_deck_name(name) for name in new_aliases})
        return self.decks().update_one({"canonical_aliases": canonical_name}, {
            "$addToSet": {
                "aliases": {
                    "$each": new_aliases
                },
                "canonical_aliases": {
                    "$each": new_canonical_aliases
                }
            }
        })

    def add_deck_link(self, alias, link):
        canonical_name = utils.transform_deck_name(alias)
        return self.decks().update_one({"canonical_aliases": canonical_name}, {
            "$set": { "link": link }
        })

    def find_one_deck_by_color(self, color):
        return self.decks().find_one({"color": utils.sort_color_str(color)})

    def find_decks_by_color(self, color):
        return self.decks().find({"color": utils.sort_color_str(color)})

    def get_deck_short_name(self, alias):
        deck = self.find_deck(alias)
        if not deck:
            return None
        shortest_name = sorted(deck['aliases'], key=(lambda n: len(n)))[0]
        return shortest_name

    # Config
    def get_config(self, guild):
        return self.config(guild).find_one()

    def set_admin_role(self, role_name, guild):
        self.config(guild).update_one({}, {
            "$set": {
                "admin": role_name
            }
        })

    def get_admin_role(self, guild):
        config = self.get_config(guild)
        if "admin" in config and config["admin"]:
            return discord.utils.find(lambda r: r.name == config["admin"], guild.roles)
        return None

    def set_player_match_threshold(self, threshold, guild):
        self.config(guild).update_one({}, {
            "$set": {
                "player_match_threshold": threshold
            }
        })

    def get_player_match_threshold(self, guild):
        config = self.get_config(guild)
        if "player_match_threshold" in config:
            return config["player_match_threshold"]
        return system.min_matches

    def set_deck_match_threshold(self, threshold, guild):
        self.config(guild).update_one({}, {
            "$set": {
                "deck_match_threshold": threshold
            }
        })

    def get_deck_match_threshold(self, guild):
        config = self.get_config(guild)
        if "deck_match_threshold" in config:
            return config["deck_match_threshold"]
        return system.min_matches

    # Seasons
    def get_season(self, guild, season=None):
        seasons = self.seasons(guild)
        if not season:
            return seasons.find({}, limit=1, sort=[("start_time", DESCENDING)])[0]
        else:
            return seasons.find_one({"season_number": season})

    def reset_scores(self, guild):
        self.members(guild).update_many({}, 
            {
                "$set": {
                    "points": system.base_points,
                    "wins": 0,
                    "accepted": 0,
                    "losses": 0
                }
            })

    def reset_season(self, guild):
        # Record results from the current season
        current_season = self.get_season(guild)
        end_time = time.time()
        leaders = list(self.find_top_members_by("points", guild, limit=3))
        if not leaders:
            self.seasons(guild).update_one(
                {"season_number": current_season["season_number"]},
                {
                    "$set": {
                        "end_time": end_time
                    }
                }
            )
        else:
            self.seasons(guild).update_one(
                {"season_number": current_season["season_number"]},
                {
                    "$set": {
                        "end_time": end_time,
                        "season_leaders": [player["user_id"] for player in leaders]
                    }
                }
            )

        # Give season rewards
        if leaders:
            for i, badge in enumerate(["gold", "silver", "bronze"]):
                self.members(guild).update_one(
                    {"user_id": leaders[i]["user_id"]},
                    {"$inc": {f"season_{badge}_badges": 1}}
                )

        self.reset_scores(guild)

        # Create new season
        new_season = {
            "start_time": end_time,
            "season_number": current_season["season_number"]+1
        }
        self.seasons(guild).insert_one(new_season)
        return current_season["season_number"], leaders
