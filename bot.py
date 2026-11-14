import os
import discord
from discord.ext import commands

# Stel je bot intents in
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

@bot.command()
async def ping(ctx):
    await ctx.send('Pong! The security bot is online and operational.')

# Start de bot veilig via de Railway omgevingsvariabele
TOKEN = os.getenv('TOKEN')

if not TOKEN:
    print("ERROR: No TOKEN found in the environment variables!")
else:
    bot.run(TOKEN)
