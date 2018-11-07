import discord
from discord.ext import commands
from app.constants import status_codes as stc
from app.utils import checks, embed

class Admin():
    def __init__(self, bot):
        self.bot = bot

    @commands.group(
        brief="Configure settings for the league",
        usage=("`{0}config`\n" \
               "`{0}config [admin|threshold]`")
    )
    @commands.guild_only()
    @commands.check(checks.is_admin)
    async def config(self, ctx):
        """Configure or view settings for the league"""

        if ctx.invoked_subcommand is None:
            settings = self.bot.db.get_config(ctx.message.guild)
            emsg = embed.info(title="League Configuration")
            for setting in settings:
                if setting != "_id":
                    emsg.add_field(name=setting, value=settings[setting])
            await ctx.send(embed=emsg)
            return

    @config.command(
        name="admin", 
        brief="Set the league admin role",
        usage="`{0}config admin @role`"
    )
    async def _config_admin(self, ctx, *, role: discord.Role):
        """Sets the league admin role to the mentioned role.
        League admins can audit, accept, and remove matches."""

        self.bot.db.set_admin_role(role.name, ctx.message.guild)
        await ctx.send(embed=embed.success(description=f"**SUCCESS** - {role.mention} set to league admin"))

    @config.command(
        name="threshold",
        brief="Set player or deck leaderboard match threshold",
        usage="`{0}config threshold [player|deck] [value]`"
    )
    async def _config_threshold(self, ctx, *args):
        """Set the player or deck threshold to appear on the leaderboard."""

        if len(args) < 2:
            await ctx.send(embed=embed.error(description="Not enough args, include a threshold type and threshold value"))
            return
        if not args[1].isdigit():
            await ctx.send(embed=embed.error(description="Threshold value should be a number"))
            return
        thresh_t = args[0]
        value = int(args[1])
        if thresh_t == "player":
            self.bot.db.set_player_match_threshold(value, ctx.message.guild)
        elif thresh_t == "deck":
            self.bot.db.set_deck_match_threshold(value, ctx.message.guild)
        else:
            await ctx.send(embed=embed.error(description="Unrecognized threshold type."))
            return
        await ctx.send(embed=embed.success(description=f"**SUCCESS** - {thresh_t.upper()} threshold set to {value}"))

    @commands.command(
        name="update",
        brief="Update a player's deck for a given match",
        usage=("`{0}update [game id] @user [deck name]`\n" \
               "`{0}update [game_id1,game_id2,game_id3] @user [deck1,deck2,deck3]`"
        )
    )
    async def _set_user_deck(self, ctx, *args):
        """Update a match by setting a user's deck to the specified deck name."""

        if len(args) < 3:
            await ctx.send(embed=embed.error(description=f"Not enough args. See `{ctx.prefix}help update`."))
            return

        game_ids = args[0].split(",")
        deck_names = args[2].split(",")
        if len(game_ids) != len(deck_names):
            await ctx.send(embed=embed.error(description="There must be the same number of decks as games specified."))
            return
        if not ctx.message.mentions:
            await ctx.send(embed=embed.error(description=f"Please include the player to adjust."))
            return
        user = ctx.message.mentions[0]
        nupdates = len(game_ids)
        for i in range(nupdates):
            deck = self.bot.db.find_deck(deck_names[i])
            if not deck:
                await ctx.send(embed=embed.error(
                    description=f"Deck name \"{deck_names[i]}\" not recognized. See `{ctx.prefix}decks` for a list of all decks."))
                continue
            if not self.bot.db.confirm_match_for_user(game_ids[i], user.id, deck['name'], ctx.message.guild):
                await ctx.send(embed=embed.error(
                    description=f"No game found for `{game_ids[i]}` with the given user as a participant."
                ))
            else:
                await ctx.send(embed=embed.success(
                    title=f"Game id: {game_id}",
                    description=f"Set deck to **{deck['name']}** for **{user.name}**"
                ))


    @commands.command(
        brief="Force a match into accepted state",
        usage="`{0}accept [game id]`"
    )
    @commands.guild_only()
    @commands.check(checks.is_admin)
    async def accept(self, ctx, *, game_id: str=""):
        """Force a match into accepted state.
        This should only be used if a match is known to be valid but one or more of the participants is unwilling or unavailable to confirm. This command can only be used by an admin."""

        if not game_id:
            await ctx.send(embed=embed.error(description="No game id specified"))
            return
        match = self.bot.db.find_match(game_id, ctx.message.guild)
        if not match:
            await ctx.send(embed=embed.error(description=f"`{game_id}` does not exist"))
            return
        if match["status"] == stc.ACCEPTED:
            return

        self.bot.db.confirm_match_for_users(game_id, ctx.message.guild)
        delta = self.bot.db.check_match_status(game_id, ctx.message.guild)
        if delta:
            await ctx.send(embed=embed.match_delta(game_id, delta))


    @commands.command(
        brief="Remove a match",
        usage="`{0}remove [game id]`"
    )
    @commands.guild_only()
    @commands.check(checks.is_registered)
    async def remove(self, ctx, *, game_id: str=""):
        """Removes a match from the tracking system.
        This should only be used if a match is known to be invalid. Only pending matches can be rejected. This command can only be used by an admin or the player who logged the match."""

        if not game_id:
            await ctx.send(embed=embed.error(description="No game id specified"))
            return
        match = self.bot.db.find_match(game_id, ctx.message.guild)
        if not match:
            await ctx.send(embed=embed.error(description=f"`{game_id}` does not exist"))
            return
        if match["status"] == stc.ACCEPTED:
            await ctx.send(embed=embed.error(description="Cannot override an accepted match"))
            return
        if not (match["winner"] == ctx.message.author.id or checks.is_admin(ctx)):
            await ctx.send(embed=embed.error(description="Only a league admin or the match winner can remove a match"))
            return

        self.bot.db.delete_match(game_id, ctx.message.guild)
        await ctx.send(embed=embed.msg(description=f"`{game_id}` has been removed"))


    @commands.command(
        name="link",
        brief="Add a replay link to a game",
        usage="`{0}link [game id] [replay link]`"
    )
    @commands.guild_only()
    @commands.check(checks.is_admin)
    async def _link(self, ctx, *args):
        """Add a replay link to a game. Links can later be discovered and filtered with the `replay` command."""

        if len(args) < 2:
            await ctx.send(embed=embed.error(description="Not enough args. Please include a game id and a replay link."))
            return

        game_id = args[0]
        replay_link = args[1]

        if not self.bot.db.update_match(
            {"game_id": game_id},
            {"$set": {"replay_link": replay_link}},
            ctx.message.guild):
            await ctx.send(embed=embed.error(description=f"**{game_id}** not found"))
        else:
            await ctx.send(embed=embed.success(description=f"Replay link updated for **{game_id}**"))
    

def setup(bot):
    bot.add_cog(Admin(bot))
