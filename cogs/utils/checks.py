from discord.ext import commands
try:
    from lxml import etree
except ImportError:
    from bs4 import BeautifulSoup
from urllib.parse import parse_qs, quote_plus
import json
import time
import discord
import os
import aiohttp
from urllib.parse import quote as uriquote
import config

# The permission system of the bot is based on a "just works" basis
# You have permissions and the bot has permissions. If you meet the permissions
# required to execute the command (and the bot does as well) then it goes through
# and you can execute the command.
# Certain permissions signify if the person is a moderator (Manage Server) or an
# admin (Administrator). Having these signify certain bypasses.
# Of course, the owner will always be able to execute commands.

async def check_permissions(ctx, perms, *, check=all):
    is_owner = await ctx.bot.is_owner(ctx.author)
    if is_owner:
        return True

    resolved = ctx.channel.permissions_for(ctx.author)
    return check(getattr(resolved, name, None) == value for name, value in perms.items())

def has_permissions(*, check=all, **perms):
    async def pred(ctx):
        return await check_permissions(ctx, perms, check=check)
    return commands.check(pred)

async def check_guild_permissions(ctx, perms, *, check=all):
    is_owner = await ctx.bot.is_owner(ctx.author)
    if is_owner:
        return True

    if ctx.guild is None:
        return False

    resolved = ctx.author.guild_permissions
    return check(getattr(resolved, name, None) == value for name, value in perms.items())

def has_guild_permissions(*, check=all, **perms):
    async def pred(ctx):
        return await check_guild_permissions(ctx, perms, check=check)
    return commands.check(pred)

# These do not take channel overrides into account

def is_mod():
    async def pred(ctx):
        return await check_guild_permissions(ctx, {'manage_guild': True})
    return commands.check(pred)

def is_admin():
    async def pred(ctx):
        return await check_guild_permissions(ctx, {'administrator': True})
    return commands.check(pred)

def mod_or_permissions(**perms):
    perms['manage_guild'] = True
    async def predicate(ctx):
        return await check_guild_permissions(ctx, perms, check=any)
    return commands.check(predicate)

def admin_or_permissions(**perms):
    perms['administrator'] = True
    async def predicate(ctx):
        return await check_guild_permissions(ctx, perms, check=any)
    return commands.check(predicate)

def is_in_guilds(*guild_ids):
    def predicate(ctx):
        guild = ctx.guild
        if guild is None:
            return False
        return guild.id in guild_ids
    return commands.check(predicate)

def embed_perms(message):
    try:
        check = message.author.permissions_in(message.channel).embed_links
    except:
        check = True

    return check


async def get_google_entries(query, session=None):
    if not session:
        session = aiohttp.ClientSession()
    url = 'https://www.google.com/search?q={}'.format(uriquote(query))
    params = {
        'safe': 'off',
        'lr': 'lang_en',
        'h1': 'en'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64)'
    }
    entries = []
    async with session.get(url, params=params, headers=headers) as resp:
        if resp.status != 200:
            async with session.get("https://www.googleapis.com/customsearch/v1?q=" + quote_plus(query) + "&start=" + '1' + "&key=" + config.GOOGLE_API_KEY + "&cx=" + config.CUSTOM_SEARCH_ENGINE) as resp:
                result = json.loads(await resp.text())
            return None, result['items'][0]['link']

        try:
            root = etree.fromstring(await resp.text(), etree.HTMLParser())
            search_nodes = root.findall(".//div[@class='g']")
            for node in search_nodes:
                url_node = node.find('.//h3/a')
                if url_node is None:
                    continue
                url = url_node.attrib['href']
                if not url.startswith('/url?'):
                    continue
                url = parse_qs(url[5:])['q'][0]
                entries.append(url)
        except NameError:
            root = BeautifulSoup(await resp.text(), 'html.parser')
            for result in root.find_all("div", class_='g'):
                url_node = result.find('h3')
                if url_node:
                    for link in url_node.find_all('a', href=True):
                        url = link['href']
                        if not url.startswith('/url?'):
                            continue
                        url = parse_qs(url[5:])['q'][0]
                        entries.append(url)
    return entries, root