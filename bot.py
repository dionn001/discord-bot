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

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

join_tracker = defaultdict(list)
admin_acties = defaultdict(list)
spam_tracker = defaultdict(list)
mention_tracker = defaultdict(list)
caps_tracker = defaultdict(list)
warns = defaultdict(list)
muted_users = set()

raid_modus = False
antilink_enabled = True
antispam_enabled = True
antimention_enabled = True
anticaps_enabled = True
antislur_enabled = True

# Lijst met slechte woorden / scheldwoorden om te filteren
BAD_WORDS = ["badword1", "badword2", "scheldwoord1", "scheldwoord2", "kanker", "tyfus", "kkr"]

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
        now = time.time()
        content_lower = message.content.lower()

        # 1. Anti-Bad Words / Profanity Filter
        if antislur_enabled:
            if any(word in content_lower for word in BAD_WORDS):
                try:
                    await message.delete()
                    await message.channel.send(f"🚫 {message.author.mention}, watch your language! That word is not allowed.", delete_after=4)
                    return
                except:
                    pass

        # 2. Anti-Link
        if antilink_enabled and ("http://" in content_lower or "https://" in content_lower or "discord.gg/" in content_lower):
            try:
                await message.delete()
                await message.channel.send(f"🚫 {message.author.mention}, links and invites are strictly prohibited!", delete_after=4)
                return
            except:
                pass

        # 3. Advanced Anti-Spam
        if antispam_enabled:
            spam_tracker[message.author.id].append(now)
            spam_tracker[message.author.id] = [t for t in spam_tracker[message.author.id] if now - t < 4]
            if len(spam_tracker[message.author.id]) > 4:
                try:
                    await message.delete()
                    await message.author.timeout(datetime.timedelta(minutes=10), reason="Automated Anti-Spam: Message spamming")
                    await message.channel.send(f"🔇 {message.author.mention} has been timed out for 10 minutes for spamming messages.", delete_after=5)
                    spam_tracker[message.author.id].clear()
                    return
                except:
                    pass

        # 4. Anti-Mass Mentions
        if antimention_enabled and len(message.mentions) >= 4:
            try:
                await message.delete()
                await message.author.timeout(datetime.timedelta(minutes=15), reason="Automated Anti-Spam: Mass mentions")
                await message.channel.send(f"🔇 {message.author.mention} has been timed out for mass mentioning users.", delete_after=5)
                return
            except:
                pass

        # 5. Anti-Caps Lock
        if anticaps_enabled and len(message.content) > 8:
            letters = [c for c in message.content if c.isalpha()]
            if letters:
                caps_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
                if caps_ratio > 0.7:
                    try:
                        await message.delete()
                        await message.channel.send(f"⚠️ {message.author.mention}, please turn off Caps Lock!", delete_after=4)
                        return
                    except:
                        pass

    await bot.process_commands(message)

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="🛡️ Advanced Security & Moderation Suite", color=discord.Color.dark_blue())
    embed.add_field(name="General & Info", value="`!ping`, `!serverinfo`, `!userinfo [@user]`, `!avatar [@user]`, `!botstats`", inline=False)
    embed.add_field(name="Security Controls", value="`!addadmin @user`, `!removeadmin @user`, `!raidmode <on/off>`, `!antilink <on/off>`, `!antispam <on/off>`, `!antimention <on/off>`, `!anticaps <on/off>`, `!antibadwords <on/off>`", inline=False)
    embed.add_field(name="Moderation & Punishments", value="`!kick`, `!ban`, `!softban`, `!unban <id>`, `!mute <mins>`, `!unmute`, `!warn`, `!warnings`, `!clearwarns`, `!tempmute <mins>`", inline=False)
    embed.add_field(name="Server & Channel Ops", value="`!clear <amount>`, `!lock`, `!unlock`, `!lockdown`, `!unlockdown`, `!slowmode <sec>`, `!nuke`, `!nick`, `!role`, `!say`, `!announce`, `!poll`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    await ctx.send(f'🏓 Pong! Latency: {round(bot.latency * 1000)}ms. All protection shields active.')

@bot.command()
async def botstats(ctx):
    embed = discord.Embed(title="📊 Bot Status & Protections", color=discord.Color.green())
    embed.add_field(name="Servers Protected", value=len(bot.guilds), inline=True)
    embed.add_field(name="Anti-Raid Mode", value="Enabled" if raid_modus else "Standby", inline=True)
    embed.add_field(name="Anti-Link", value="Active" if antilink_enabled else "Off", inline=True)
    embed.add_field(name="Anti-Spam", value="Active" if antispam_enabled else "Off", inline=True)
    embed.add_field(name="Anti-Mention", value="Active" if antimention_enabled else "Off", inline=True)
    embed.add_field(name="Anti-Caps", value="Active" if anticaps_enabled else "Off", inline=True)
    embed.add_field(name="Bad Word Filter", value="Active" if antislur_enabled else "Off", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 Server Info: {guild.name}", color=discord.Color.blue())
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
        await ctx.send("🔗 **ANTI-LINK ENABLED:** Unauthorized links and invites will be scrubbed.")
    elif mode.lower() == "off":
        antilink_enabled = False
        await ctx.send("🔓 **ANTI-LINK DISABLED.**")

@bot.command()
@admin_or_botadmin()
async def antispam(ctx, mode: str):
    global antispam_enabled
    if mode.lower() == "on":
        antispam_enabled = True
        await ctx.send("🛡️ **ANTI-SPAM SHIELD ENABLED.**")
    elif mode.lower() == "off":
        antispam_enabled = False
        await ctx.send("⚠️ **ANTI-SPAM SHIELD DISABLED.**")

@bot.command()
@admin_or_botadmin()
async def antimention(ctx, mode: str):
    global antimention_enabled
    if mode.lower() == "on":
        antimention_enabled = True
        await ctx.send("🛡️ **ANTI-MENTION SPAM ENABLED.**")
    elif mode.lower() == "off":
        antimention_enabled = False
        await ctx.send("⚠️ **ANTI-MENTION SPAM DISABLED.**")

@bot.command()
@admin_or_botadmin()
async def anticaps(ctx, mode: str):
    global anticaps_enabled
    if mode.lower() == "on":
        anticaps_enabled = True
        await ctx.send("🔠 **ANTI-CAPS PROTECTION ENABLED.**")
    elif mode.lower() == "off":
        anticaps_enabled = False
        await ctx.send("lowercase mode unlocked.")

@bot.command()
@admin_or_botadmin()
async def antibadwords(ctx, mode: str):
    global antislur_enabled
    if mode.lower() == "on":
        antislur_enabled = True
        await ctx.send("🤬 **BAD WORD FILTER ENABLED.**")
    elif mode.lower() == "off":
        antislur_enabled = False
        await ctx.send("⚠️ **BAD WORD FILTER DISABLED.**")

@bot.command()
@admin_or_botadmin()
async def kick(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    await member.kick(reason=reason)
    await ctx.send(f'👢 Kicked {member.mention}. Reason: {reason}')

@bot.command()
@admin_or_botadmin()
async def ban(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    await member.ban(reason=reason)
    await ctx.send(f'🔨 Banned {member.mention}. Reason: {reason}')

@bot.command()
@admin_or_botadmin()
async def softban(ctx, member: discord.Member, *, reason: str = "Softban message cleanup"):
    await member.ban(reason=reason, delete_message_days=1)
    await ctx.guild.unban(member)
    await ctx.send(f'🧹 Softbanned {member.mention} (messages cleared).')

@bot.command()
@admin_or_botadmin()
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f'🕊️ Unbanned {user.name}.')

@bot.command()
@admin_or_botadmin()
async def mute(ctx, member: discord.Member, minutes: int = 10, *, reason: str = "No reason provided"):
    duration = datetime.timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await ctx.send(f'🔇 Muted {member.mention} for {minutes} minutes. Reason: {reason}')

@bot.command()
@admin_or_botadmin()
async def tempmute(ctx, member: discord.Member, minutes: int = 5, *, reason: str = "Quick mute"):
    duration = datetime.timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await ctx.send(f'🔇 Temporarily muted {member.mention} for {minutes} minutes.')

@bot.command()
@admin_or_botadmin()
async def unmute(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(f'🔊 Unmuted {member.mention}.')

@bot.command()
@admin_or_botadmin()
async def warn(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    warns[member.id].append(reason)
    count = len(warns[member.id])
    await ctx.send(f'⚠️ Warned {member.mention} (Total warnings: {count}). Reason: {reason}')

@bot.command()
@admin_or_botadmin()
async def warnings(ctx, member: discord.Member):
    user_warns = warns[member.id]
    if not user_warns:
        await ctx.send(f'✅ {member.mention} has 0 warnings.')
    else:
        formatted = "\n".join([f"{i+1}. {w}" for i, w in enumerate(user_warns)])
        await ctx.send(f'📋 **Warnings for {member.name}:**\n{formatted}')

@bot.command()
@admin_or_botadmin()
async def clearwarns(ctx, member: discord.Member):
    warns[member.id].clear()
    await ctx.send(f'🧹 Cleared all warnings for {member.mention}.')

@bot.command()
@admin_or_botadmin()
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f'🧹 Cleared {amount} messages.', delete_after=3)

@bot.command()
@admin_or_botadmin()
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send('🔒 Channel locked.')

@bot.command()
@admin_or_botadmin()
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send('🔓 Channel unlocked.')

@bot.command()
@admin_or_botadmin()
async def lockdown(ctx):
    for channel in ctx.guild.text_channels:
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        except:
            pass
    await ctx.send('🚨 **SERVER LOCKDOWN ACTIVATED:** All text channels have been locked!')

@bot.command()
@admin_or_botadmin()
async def unlockdown(ctx):
    for channel in ctx.guild.text_channels:
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=True)
        except:
            pass
    await ctx.send('🟢 **SERVER LOCKDOWN LIFTED:** All text channels are unlocked.')

@bot.command()
@admin_or_botadmin()
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f'⏱️ Slowmode set to {seconds} seconds.')

@bot.command()
@admin_or_botadmin()
async def nuke(ctx):
    new_channel = await ctx.channel.clone(reason="Channel nuked by admin")
    await ctx.channel.delete()
    await new_channel.send("💥 **Channel has been nuked!**")

@bot.command()
@admin_or_botadmin()
async def nick(ctx, member: discord.Member, *, nickname: str = None):
    await member.edit(nick=nickname)
    await ctx.send(f'✏️ Updated nickname for {member.mention}.')

@bot.command()
@admin_or_botadmin()
async def role(ctx, member: discord.Member, role: discord.Role):
    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f'➖ Removed role **{role.name}** from {member.mention}.')
    else:
        await member.add_roles(role)
        await ctx.send(f'➕ Added role **{role.name}** to {member.mention}.')

@bot.command()
@admin_or_botadmin()
async def say(ctx, *, message: str):
    await ctx.message.delete()
    await ctx.send(message)

@bot.command()
@admin_or_botadmin()
async def announce(ctx, *, message: str):
    await ctx.message.delete()
    embed = discord.Embed(title="📢 Server Announcement", description=message, color=discord.Color.gold())
    await ctx.send(embed=embed)

@bot.command()
@admin_or_botadmin()
async def poll(ctx, *, question: str):
    await ctx.message.delete()
    embed = discord.Embed(title="📊 Server Poll", description=question, color=discord.Color.blurple())
    poll_msg = await ctx.send(embed=embed)
    await poll_msg.add_reaction("👍")
    await poll_msg.add_reaction("👎")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You don't have permission to use this command!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("⚠️ Missing required arguments! Type `!help` to see command usage.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ User not found.")

TOKEN = os.getenv('TOKEN')

if not TOKEN:
    print("ERROR: No TOKEN found in the environment variables!")
else:
    bot.run(TOKEN)
