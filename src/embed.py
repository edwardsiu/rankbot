import discord
from src.colors import C_OK, C_INFO, C_SUCCESS, C_ERR

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
