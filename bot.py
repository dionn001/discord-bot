import os
import time
import datetime
from collections import defaultdict
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.moderation = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

join_tracker = defaultdict(list)
admin_acties = defaultdict(list)
spam_tracker = defaultdict(list)
warns = defaultdict(list)
raid_modus = False
antilink_enabled = False
antispam_enabled = True

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

# --- PASSIVE SECURITY & ANTI-RAID ---

@bot.event
async def on_member_join(member):
    global raid_modus
    now = time.time()
    join_tracker[member.guild.id].append(now)
    join_tracker[member.guild.id] = [t for t in join_tracker[member.guild.id] if now - t < 10]
    
    if len(join_tracker[member.guild.id]) >= 5 and not raid_modus:
        raid_modus = True
        for channel in member.guild.text_channels:
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
            if perpetrator == bot.user or perpetrator == guild.owner:
                return
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

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    is_admin = message.author.guild_permissions.administrator or any(r.name == "BotAdmin" for r in message.author.roles)

    if not is_admin:
        # Anti-Link
        if antilink_enabled and ("http://" in message.content.lower() or "https://" in message.content.lower() or "discord.gg/" in message.content.lower()):
            try:
                await message.delete()
                await message.channel.send(f"🚫 {message.author.mention}, links are not allowed here!", delete_after=4)
                return
            except:
                pass

        # Anti-Spam
        if antispam_enabled:
            now = time.time()
            spam_tracker[message.author.id].append(now)
            spam_tracker[message.author.id] = [t for t in spam_tracker[message.author.id] if now - t < 5]
            if len(spam_tracker[message.author.id]) > 5:
                try:
                    await message.author.timeout(datetime.timedelta(minutes=5), reason="Anti-Spam protection triggered")
                    await message.channel.send(f"🔇 {message.author.mention} has been timed out for 5 minutes for spamming.")
                    spam_tracker[message.author.id].clear()
                    return
                except:
                    pass

    await bot.process_commands(message)

# --- GENERAL & INFO COMMANDS ---

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="🛡️ Security & Moderation Commands", color=discord.Color.blue())
    embed.add_field(name="General", value="`!ping`, `!serverinfo`, `!userinfo [@user]`, `!avatar [@user]`", inline=False)
    embed.add_field(name="Admin Setup", value="`!addadmin @user`, `!removeadmin @user`, `!raidmode <on/off>`, `!antilink <on/off>`, `!antispam <on/off>`", inline=False)
    embed.add_field(name="Moderation", value="`!kick`, `!ban`, `!unban <id>`, `!softban`, `!mute <mins>`, `!unmute`, `!warn`, `!warnings`, `!clearwarns`", inline=False)
    embed.add_field(name="Channel & Server", value="`!clear <amount>`, `!lock`, `!unlock`, `!lockdown`, `!unlockdown`, `!slowmode <sec>`, `!nuke`, `!nick`, `!role`, `!say`, `!announce`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    await ctx.send(f'🏓 Pong! Latency: {round(bot.latency * 1000)}ms. Security systems operational.')

@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 Server Info: {guild.name}", color=discord.Color.green())
    embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Created At", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"👤 User Info: {member.name}", color=member.color)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Nickname", value=member.nick or "None", inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"🖼️ {member.name}'s Avatar", color=discord.Color.purple())
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

# --- ADMIN & SECURITY TOGGLES ---

@bot.command()
@commands.has_permissions(administrator=True)
async def addadmin(ctx, member: discord.Member):
    role_name = "BotAdmin"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        role = await ctx.guild.create_role(name=role_name, reason="Bot Admin role created automatically")
    await member.add_roles(role)
    await ctx.send(f'✅ Granted BotAdmin privileges to {member.mention}!')

@bot.command()
@commands.has_permissions(administrator=True)
async def removeadmin(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="BotAdmin")
    if role and role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f'🗑️ Removed BotAdmin privileges from {member.mention}.')
    else:
        await ctx.send('❌ That user does not have the BotAdmin role.')

@bot.command()
@admin_or_botadmin()
async def raidmode(ctx, mode: str):
    global raid_modus
    if mode.lower() == "on":
        raid_modus = True
        await ctx.send("🚨 **ANTI-RAID MODE ENABLED:** All new joins will be automatically kicked!")
    elif mode.lower() == "off":
        raid_modus = False
        await ctx.send("🟢 **ANTI-RAID MODE DISABLED:** Server joins returned to normal.")
    else:
        await ctx.send("❌ Use `!raidmode on` or `!raidmode off`.")

@bot.command()
@admin_or_botadmin()
async def antilink(ctx, mode: str):
    global antilink_enabled
    if mode.lower() == "on":
        antilink_enabled = True
        await ctx.send("🔗 **ANTI-LINK ENABLED:** Links from non-admins will be deleted.")
    elif mode.lower() == "off":
        antilink_enabled = False
        await ctx.send("🔓 **ANTI-LINK DISABLED.**")

@bot.command()
@admin_or_botadmin()
async def antispam(ctx, mode: str):
    global
