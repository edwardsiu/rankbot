import discord
from discord.ext import commands
from app.utils import embed

class Help():
    def __init__(self, bot):
        self.bot = bot

    def _user_help(self):
        emsg = embed.info(title="Command Help")
        emsg.add_field(name="help", inline=False, value=(
            f"Show the command list. `{self.bot.command_prefix}help [command]` for detail"
        ))
        emsg.add_field(name="info", inline=False, value=(
            "Show an overview of the league"
        ))
        emsg.add_field(name="register", inline=False, value=(
            "Register to the server ranked league"
        ))
        emsg.add_field(name="log", inline=False, value=(
            "Log a match result into the ranked system"
        ))
        emsg.add_field(name="confirm", inline=False, value=(
            "Verify the most recent match result"
        ))
        emsg.add_field(name="deny", inline=False, value=(
            "Dispute the most recent match result"
        ))
        emsg.add_field(name="status", inline=False, value=(
            "Check the details of the most recent match"
        ))
        emsg.add_field(name="pending", inline=False, value=(
            "List your pending unconfirmed matches"
        ))
        emsg.add_field(name="remind", inline=False, value=(
            "Remind players to confirm your pending matches"
        ))
        emsg.add_field(name="top", inline=False, value=(
            "List the top players in the league"
        ))
        emsg.add_field(name="profile", inline=False, value=(
            "Show your league profile card"
        ))
        emsg.add_field(name="history", inline=False, value=(
            "Show your recent match results"
        ))
        emsg.add_field(name="use", inline=False, value=(
            "Set your current deck"
        ))
        emsg.add_field(name="decks", inline=False, value=(
            "Show all registered decks that are being tracked"
        ))
        emsg.add_field(name="stat", inline=False, value=(
            "Show league statistics"
        ))
        return emsg

    def _admin_help(self):
        emsg = discord.Embed(title="Admin Command Help")
        emsg.add_field(name="admin", inline=False, value=(
            "Set the mentioned role as the league admin role"
        ))
        emsg.add_field(name="disputed", inline=False, value=(
            "List all disputed matches"
        ))
        emsg.add_field(name="accept", inline=False, value=(
            "Override a disputed match by confirming it"
        ))
        emsg.add_field(name="reject", inline=False, value=(
            "Override a disputed match by deleting it"
        ))
        return emsg

    def _help_detail(self, command, usage, description):
        emsg = discord.Embed(title="Command: {}".format(command))
        emsg.add_field(name="Usage", value=usage)
        emsg.add_field(name="Description", value=description)
        return emsg

    @commands.group()
    async def help(self, ctx):
        user = ctx.message.author
        if ctx.invoked_subcommand is None:
            emsg = self._user_help()
            await self.bot.send_help(user, emsg)
            if self.bot.is_admin(ctx):
                emsg = self._admin_help()
                await self.bot.send_help(user, emsg)

    @help.command(name='log')
    async def help_log(self, ctx):
        usage = "`{}log @player1 @player2 @player3`".format(ctx.prefix)
        description = (
            "Logs a match result into the league. The winner of the match must be the one to log " \
            "the result, and mention exactly 3 losers. Upon logging the result, each player must " \
            "confirm the match result via the `{0}confirm` command, or dispute it via `{0}deny`.".format(ctx.prefix)
        )
        await self.bot.send_help(ctx.message.channel, self._help_detail(ctx.invoked_with, usage, description))

    @help.command(name='confirm')
    async def help_confirm(self, ctx):
        usage = "`{0}confirm`\n`{0}confirm [game id]`".format(ctx.prefix)
        description = (
            "Confirm a match with the given game id. If no game id is given, confirms "
            + "the most recent unconfirmed match. All match results logged with the "
            + "`{}log` command must be confirmed by all players for the result to be ".format(ctx.prefix)
            + "accepted."
        )
        await self.bot.send_help(ctx.message.channel, self._help_detail(ctx.invoked_with, usage, description))

    @help.command(name='deny')
    async def help_deny(self, ctx):
        usage = "`{0}deny`\n`{0}deny [game id]`".format(ctx.prefix)
        description = (
            "Dispute a match with the given game id. If no game id is given, disputes "
            + "the most recent unconfirmed match. A match marked as `DISPUTED` cannot be "
            + "resolved except by a league admin."
        )
        await self.bot.send_help(ctx.message.channel, self._help_detail(ctx.invoked_with, usage, description))

    @help.command(name='score')
    async def help_score(self, ctx):
        usage = "`{0}score`\n`{0}score @user1 @user2 ...`".format(ctx.prefix)
        description = (
            "Displays the score card for the given user(s), or the current user if no user "
            + "is mentioned. The score card contains the user's league points, total wins, "
            + "total losses, and win percentage. League point changes are calculated based "
            + "on the score difference between the winner and each loser, such that losing "
            + "to someone worse than you causes a greater loss in points while losing to "
            + "someone with a higher score than you causes a lesser loss in points.\n\n"
        )
        await self.bot.send_help(ctx.message.channel, self._help_detail(ctx.invoked_with, usage, description))

    @help.command(name='top')
    async def help_top(self, ctx):
        usage = "`{0}top`\n" \
                "`{0}top [wins|games|points]`\n" \
                "`{0}top [wins|games|points] [count]".format(ctx.prefix)
        description = "Displays the top 10 players in the league by points, wins, or games played. " \
                      "If a category is not specified, ranking by points will be shown. " \
                      "The count indicates how many players to display. " \
                      "A count of `all` will display all players in the league. " \
                      "Players that have played less than 5 matches will not be included in the leaderboard."
        await self.bot.send_help(ctx.message.channel, self._help_detail(ctx.invoked_with, usage, description))

    @help.command(name='remind')
    async def help_remind(self, ctx):
        usage = "`{}remind`".format(ctx.prefix)
        description = (
            "Pings players that need to confirm/deny a pending match in your pending queue."
        )
        await self.bot.send_help(ctx.message.channel, self._help_detail(ctx.invoked_with, usage, description))

    @help.command(name='status')
    async def help_status(self, ctx):
        usage = "`{}status [game id]`".format(ctx.prefix)
        description = (
            "Shows details about the match with the given game id, including the match status, "
            + "winner, players, and each players' confirmation status."
        )
        await self.bot.send_help(ctx.message.channel, self._help_detail(ctx.invoked_with, usage, description))

    @help.command(name='history')
    async def help_history(self, ctx):
        usage = "`{0}history`\n`{0}history @user1 @user2 ...`".format(ctx.prefix)
        description = (
            "Show your last 5 matches and their result. If there are mentioned users, show "
            + "their last 5 matches instead."
        )
        await self.bot.send_help(ctx.message.channel, self._help_detail(ctx.invoked_with, usage, description))

    @help.command(name='use')
    async def help_use(self, ctx):
        usage = "`{}use [deck name]`".format(ctx.prefix)
        description = (
            "Set your last played deck to `deck name`. Short hand names are allowed. If no "
            + "deck name is specified or the deck is not a recognized deck, the deck will "
            + "default to Rogue."
        )
        await self.bot.send_help(ctx.message.channel, self._help_detail(ctx.invoked_with, usage, description))

    @help.command(name='decks')
    async def help_decks(self, ctx):
        usage = "`{0}decks`\n`{0}decks [color combo]`".format(ctx.prefix)
        description = (
            "Show a list of all registered decks tracked by Isperia. If a color combination "
            + "is specified, shows a list of decks with the given color combination. "
            + "Otherwise, a list of all decks will be displayed. Color combinations should "
            + "be in WUBRG format."
        )
        await self.bot.send_help(ctx.message.channel, self._help_detail(ctx.invoked_with, usage, description))

    @help.command(name='stats')
    async def help_stats(self, ctx):
        usage = "`{0}stats decks`\n" \
                "`{0}stats decks [wins|winrate|popularity]`".format(ctx.prefix)
        description = (
            "Show match statistics of decks tracked by Isperia. The default sort is by deck "
            + "meta share. Wins will sort by total wins. Winrate sorts by win %. Popularity "
            + "sorts by number of unique players playing the deck."
        )
        await self.bot.send_help(ctx.message.channel, self._help_detail(ctx.invoked_with, usage, description))

    @help.command(name='reset')
    async def help_reset(self, ctx):
        usage = "`{}reset`".format(ctx.prefix)
        description = (
            "Resets all points to the default and clears all match results. Asks for "
            + "confirmation before resetting."
        )
        await self.bot.send_help(ctx.message.channel, self._help_detail(ctx.invoked_with, usage, description))

    @help.command(name='accept')
    async def help_accept(self, ctx):
        usage = "`{}accept [game_id]`".format(ctx.prefix)
        description = "League admins can resolve a disputed match as confirmed via the accept command. " \
                      "A list of disputed matches can be produced via the `{}disputed` command.".format(ctx.prefix)
        await self.bot.send_help(ctx.message.channel, self._help_detail(ctx.invoked_with, usage, description))

    @help.command(name='reject')
    async def help_reject(self, ctx):
        usage = "`{}reject [game_id]`".format(ctx.prefix)
        description = "League admins can resolve a disputed match by removing it via the reject command. " \
                      "A list of disputed matches can be produced via the `{}disputed` command.".format(ctx.prefix)
        await self.bot.send_help(ctx.message.channel, self._help_detail(ctx.invoked_with, usage, description))

def setup(bot):
    bot.remove_command('help')
    bot.add_cog(Help(bot))
