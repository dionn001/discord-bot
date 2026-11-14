import os
import time
from collections import defaultdict
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.moderation = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Opslag voor anti-raid en beveiliging
join_tracker = defaultdict(list)
admin_acties = defaultdict(list)
raid_modus = False

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

# --- BEVEILIGING OP DE ACHTERGROND ---

@bot.event
async def on_member_join(member):
    global raid_modus
    now = time.time()
    join_tracker[member.guild.id].append(now)
    
    # Filter joins van de laatste 10 seconden
    join_tracker[member.guild.id] = [t for t in join_tracker[member.guild.id] if now - t < 10]
    
    # Als er 5 of meer joins binnen 10 seconden zijn -> Activeer Anti-Raid
    if len(join_tracker[member.guild.id]) >= 5 and not raid_modus:
        raid_modus = True
        for guild in bot.guilds:
            for channel in guild.text_channels:
                try:
                    await channel.send("🚨 **ANTI-RAID ACTIVATED:** Mass joins detected. New accounts are being restricted/kicked.")
                except:
                    pass

    # Als raid modus aan staat, kick nieuwe accounts direct
    if raid_modus:
        try:
            await member.kick(reason="Anti-Raid protection active: Mass join detected")
        except:
            pass

@bot.event
async def on_guild_channel_delete(channel):
    guild = channel.guild
    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            perpetrator = entry.user
            now = time.time()
            admin_acties[perpetrator.id].append(now)
            admin_acties[perpetrator.id] = [t for t in admin_acties[perpetrator.id] if now - t < 15]
            
            # Als iemand meer dan 2 kanalen verwijdert binnen 15 seconden
            if len(admin_acties[perpetrator.id]) > 2:
                for c in guild.text_channels:
                    try:
                        await c.send(f"🚨 **SECURITY ALERT:** {perpetrator.mention} is mass deleting channels! Action taken.")
                    except:
                        pass
                # Probeer de permissies af te pakken of te kicken
                await perpetrator.kick(reason="Mass deleting channels - Security Protection")
    except:
        pass


# --- COMMANDO'S ---

@bot.command()
async def ping(ctx):
    await ctx.send('Pong! The security bot is online and operational.')

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    await member.kick(reason=reason)
    await ctx.send(f'👢 Successfully kicked {member.mention}. Reason: {reason}')

@kick.error
async def kick_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command!")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    await member.ban(reason=reason)
    await ctx.send(f'🔨 Successfully banned {member.mention}. Reason: {reason}')

@ban.error
async def ban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command!")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f'🧹 Cleared {amount} messages.')
    await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=3))
    await msg.delete()

@clear.error
async def clear_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command!")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send('🔒 Channel locked successfully.')

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send('🔓 Channel unlocked successfully.')

@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f'⏱️ Slowmode set to {seconds} seconds.')

TOKEN = os.getenv('TOKEN')

if not TOKEN:
    print("ERROR: No TOKEN found in the environment variables!")
else:
    bot.run(TOKEN)
