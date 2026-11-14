import discord
from discord.ext import commands
import time
from collections import defaultdict

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

WHITELIST = [1140339824335786065] 

spam_tracker = defaultdict(list)
join_tracker = []
raid_modus = False
admin_acties = defaultdict(list)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

async def punish_admin(guild, user, reason):
    if user.id in WHITELIST or user.id == guild.owner_id or user.id == bot.user.id:
        return
    member = guild.get_member(user.id)
    if member:
        try:
            await member.edit(roles=[], reason=reason)
        except discord.Forbidden:
            pass

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return
    if message.author.id in WHITELIST or message.author.id == message.guild.owner_id:
        await bot.process_commands(message)
        return

    now = time.time()
    user_id = message.author.id
    spam_tracker[user_id] = [t for t in spam_tracker[user_id] if now - t < 4]
    spam_tracker[user_id].append(now)

    if len(spam_tracker[user_id]) >= 5:
        try:
            await message.channel.purge(limit=5, check=lambda m: m.author.id == user_id)
            await message.author.timeout(discord.utils.utcnow() + discord.timedelta(minutes=10))
            spam_tracker[user_id].clear()
        except discord.Forbidden:
            pass

    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    global raid_modus, join_tracker
    now = time.time()
    join_tracker = [t for t in join_tracker if now - t < 10]
    join_tracker.append(now)

    if len(join_tracker) >= 5 and not raid_modus:
        raid_modus = True

    if raid_modus:
        try:
            await member.kick(reason="Anti-Raid protection active")
        except discord.Forbidden:
            pass

@bot.event
async def on_guild_channel_delete(channel):
    guild = channel.guild
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        perpetrator = entry.user
        now = time.time()
        admin_acties[perpetrator.id] = [t for t in admin_acties[perpetrator.id] if now - t < 15]
        admin_acties[perpetrator.id].append(now)

        if len(admin_acties[perpetrator.id]) > 2:
            await punish_admin(guild, perpetrator, "Mass deleting channels")

@bot.event
async def on_member_ban(guild, user):
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
        perpetrator = entry.user
        now = time.time()
        admin_acties[perpetrator.id] = [t for t in admin_acties[perpetrator.id] if now - t < 15]
        admin_acties[perpetrator.id].append(now)

        if len(admin_acties[perpetrator.id]) > 2:
            await punish_admin(guild, perpetrator, "Mass banning members")

@bot.command()
@commands.has_permissions(administrator=True)
async def raid(ctx, status: str):
    global raid_modus
    if status.lower() == "on":
        raid_modus = True
        await ctx.send("🚨 Raid mode enabled.")
    elif status.lower() == "off":
        raid_modus = False
        join_tracker.clear()
        await ctx.send("✅ Raid mode disabled.")

bot.run('')