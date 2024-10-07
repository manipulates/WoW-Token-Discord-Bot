# Required libraries: discord.py, requests
# Install them using: pip install discord.py requests

import discord
from discord.ext import commands
import requests
import os
import time
from urllib.parse import urljoin, quote
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Set up your bot with necessary intents
intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True
command_prefix = os.getenv("BOT_COMMAND_PREFIX", '/')
bot = commands.Bot(command_prefix=command_prefix, intents=intents)

# Blizzard API credentials
CLIENT_ID = os.getenv("WOW_CLIENT_ID")  # Set this environment variable with your client ID
CLIENT_SECRET = os.getenv("WOW_CLIENT_SECRET")  # Set this environment variable with your client secret
TOKEN_URL = "https://us.battle.net/oauth/token"
API_BASE_URL = os.getenv("WOW_API_BASE_URL", "https://us.api.blizzard.com/wow/some/endpoint")  # Set this environment variable with your API base URL

# Cached access token and expiry time
cached_access_token = None
cached_token_expiry = 0

# Function to get an access token
def get_access_token():
    global cached_access_token, cached_token_expiry
    current_time = time.time()
    # Check if the token is still valid
    if cached_access_token and current_time < cached_token_expiry:
        return cached_access_token

    # Set up retry logic
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))

    # Request a new token
    try:
        response = session.post(TOKEN_URL, auth=(CLIENT_ID, CLIENT_SECRET), data={"grant_type": "client_credentials"})
        response.raise_for_status()
        token_data = response.json()
        cached_access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600)
        cached_token_expiry = current_time + expires_in
        return cached_access_token
    except requests.exceptions.RequestException as e:
        print(f"Error obtaining access token: {e}")
        return None

@bot.event
async def on_ready():
    print(f'Bot is logged in as {bot.user}')

@bot.command(name='wowinfo')
async def wow_info(ctx, *, query):
    """Get World of Warcraft information from the API."""
    # Validate and sanitize input
    if not query.replace(' ', '').isalnum():
        await ctx.send("Invalid query. Please use only alphanumeric characters and spaces.")
        return

    # Get the access token
    access_token = get_access_token()
    if not access_token:
        await ctx.send("Error fetching access token. Please try again later. Contact the administrator if the issue persists.")
        return

    # Make a request to the API
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    try:
        sanitized_query = quote(query)
        url = urljoin(API_BASE_URL, sanitized_query)
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        # Extract relevant information - adjust based on the API's response structure
        info = data.get("some_key", "No data found for that query.")
        await ctx.send(f"{query} information: {info}")
    except requests.exceptions.RequestException as e:
        await ctx.send(f"Error fetching information for '{query}'. Please try again later. Error details: {e}")
        print(e)

@bot.command(name='wowtoken')
async def wow_token(ctx):
    """Get the current price of a WoW Token in gold."""
    # Get the access token
    access_token = get_access_token()
    if not access_token:
        await ctx.send("Error fetching access token. Please try again later. Contact the administrator if the issue persists.")
        return

    # Make a request to the WoW Token API
    API_URL = "https://us.api.blizzard.com/data/wow/token/index"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    try:
        response = requests.get(API_URL, headers=headers, params={"namespace": "dynamic-us", "locale": "en_US"})
        response.raise_for_status()
        data = response.json()

        # Extract the current price of the WoW Token in gold
        token_price = data.get("price", 0) // 10000  # Convert from copper to gold
        await ctx.send(f"The current price of a WoW Token is {token_price:,} gold.")
    except requests.exceptions.RequestException as e:
        await ctx.send(f"Error fetching WoW Token price. Please try again later. Error details: {e}")
        print(e)

# Get the bot token from an environment variable
bot_token = os.getenv('DISCORD_BOT_TOKEN')
if bot_token:
    bot.run(bot_token)
else:
    print("Error: DISCORD_BOT_TOKEN environment variable not set.")
