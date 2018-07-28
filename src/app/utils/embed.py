import discord
from app.constants.colors import C_OK, C_INFO, C_SUCCESS, C_ERR

def info(**kwargs):
    emsg = discord.Embed(color=C_INFO, **kwargs)
    return emsg

def msg(**kwargs):
    emsg = discord.Embed(color=C_OK, **kwargs)
    return emsg

def success(**kwargs):
    emsg = discord.Embed(color=C_SUCCESS, **kwargs)
    return emsg

def error(**kwargs):
    emsg = discord.Embed(color=C_ERR, **kwargs)
    return emsg

def match_delta(game_id, delta):
    emsg = msg(title=f"Game id: {game_id}")
    emsg.add_field(name="Status", value="`ACCEPTED`")
    emsg.add_field(name="Point Changes", value=(
        "\n".join([f"`{i['player']}: {i['change']:+}`" for i in delta])))
    return emsg