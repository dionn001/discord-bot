import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Ingelogd als {bot.user} (ID: {bot.user.id})')
    print('------')

@bot.command()
async def ping(ctx):
    await ctx.send('Pong! De beveiligingsbot is online en operationeel.')

# Start de bot veilig via de Railway omgevingsvariabele
TOKEN = os.getenv('TOKEN')

if not TOKEN:
    print("FOUT: Geen TOKEN gevonden in de environment variables!")
else:
    bot.run(TOKEN)
