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

join_tracker = defaultdict(list)
admin_acties = defaultdict(list)
raid_modus = False

def admin_or_botadmin():
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        if any(role.name == "BotAdmin" for role in ctx.author.roles):
            return True
        return False
    return commands.check(predicate)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

@bot.event
async def on_member_join(member):
    global raid_modus
    now = time.time()
    join_tracker[member.guild.id].append(now)
    join_tracker[member.guild.id] = [t for t in join_tracker[member.guild.id] if now - t < 10]
    
    if len(join_tracker[member.guild.id]) >= 5 and not raid_modus:
        raid_modus = True
        for guild in bot.guilds:
            for channel in guild.text_channels:
                try:
                    await channel.send("🚨 **ANTI-RAID ACTIVATED:** Mass joins detected. New accounts are being restricted/kicked.")
                except:
                    pass

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
            
            if len(admin_acties[perpetrator.id]) > 2:
                for c in guild.text_channels:
                    try:
                        await c.send(f"🚨 **SECURITY ALERT:** {perpetrator.mention} is mass deleting channels! Action taken.")
                    except:
                        pass
                await perpetrator.kick(reason="Mass deleting channels - Security Protection")
    except:
        pass

@bot.command()
async def ping(ctx):
    await ctx.send('Pong! The security bot is online and operational.')

@bot.command()
@commands.has_permissions(administrator=True)
async def addadmin(ctx, member: discord.Member):
    role_name = "BotAdmin"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        try:
            role = await ctx.guild.create_role(name=role_name, reason="Bot Admin role created automatically")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to create roles!")
            return
    await member.add_roles(role)
    await ctx.send(f'✅ Successfully granted Bot Admin privileges to {member.mention}!')

@addadmin.error
async def addadmin_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need Server Administrator permissions to use this command!")

@bot.command()
@admin_or_botadmin()
async def kick(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    await member.kick(reason=reason)
    await ctx.send(f'👢 Successfully kicked {member.mention}. Reason: {reason}')

@kick.error
async def kick_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You don't have permission to use this command!")

@bot.command()
@admin_or_botadmin()
async def ban(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    await member.ban(reason=reason)
    await ctx.send(f'🔨 Successfully banned {member.mention}. Reason: {reason}')

@ban.error
async def ban_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You don't have permission to use this command!")

@bot.command()
@admin_or_botadmin()
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f'🧹 Cleared {amount} messages.')
    await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=3))
    await msg.delete()

@clear.error
async def clear_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You don't have permission to use this command!")

@bot.command()
@admin_or_botadmin()
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send('🔒 Channel locked successfully.')

@lock.error
async def lock_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You don't have permission to use this command!")

@bot.command()
@admin_or_botadmin()
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send('🔓 Channel unlocked successfully.')

@unlock.error
async def unlock_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You don't have permission to use this command!")

@bot.command()
@admin_or_botadmin()
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f'⏱️ Slowmode set to {seconds} seconds.')

@slowmode.error
async def slowmode_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You don't have permission to use this command!")

TOKEN = os.getenv('TOKEN')

if not TOKEN:
    print("ERROR: No TOKEN found in the environment variables!")
else:
    bot.run(TOKEN)
