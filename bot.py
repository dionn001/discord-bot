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
        if antilink_enabled and ("http://" in message.content.lower() or "https://" in message.content.lower() or "discord.gg/" in message.content.lower()):
            try:
                await message.delete()
                await message.channel.send(f"🚫 {message.author.mention}, links are not allowed here!", delete_after=4)
                return
            except:
                pass

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
    global antispam_enabled
    if mode.lower() == "on":
        antispam_enabled = True
        await ctx.send("🛡️ **ANTI-SPAM ENABLED.**")
    elif mode.lower() == "off":
        antispam_enabled = False
        await ctx.send("⚠️ **ANTI-SPAM DISABLED.**")

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
