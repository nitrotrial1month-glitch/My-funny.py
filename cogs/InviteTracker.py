import discord
from discord.ext import commands
from discord import app_commands
import datetime
from utils import load_config, save_config, get_theme_color

class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites = {}

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            try: self.invites[guild.id] = await guild.invites()
            except: pass

    # ================= 📥 ইনভাইট ট্র্যাকিং (মেম্বার ও বট) =================
    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        config = load_config()
        inviter = None

        if member.bot:
            try:
                # অডিট লগ থেকে বট ইনভাইটার খোঁজা
                async for entry in guild.audit_logs(action=discord.AuditLogAction.bot_add, limit=5):
                    if entry.target.id == member.id:
                        inviter = entry.user
                        break
            except: pass
        else:
            invites_before = self.invites.get(guild.id)
            invites_after = await guild.invites()
            self.invites[guild.id] = invites_after
            if invites_before:
                for i in invites_before:
                    for a in invites_after:
                        if i.code == a.code and a.uses > i.uses:
                            inviter = i.inviter
                            break

        if inviter:
            guild_id, user_id = str(guild.id), str(inviter.id)
            if "invite_data" not in config: config["invite_data"] = {}
            if guild_id not in config["invite_data"]: config["invite_data"][guild_id] = {}
            if user_id not in config["invite_data"][guild_id]:
                config["invite_data"][guild_id][user_id] = {"regular": 0, "fake": 0, "leave": 0, "bonus": 0, "bots": 0}
            
            if member.bot: config["invite_data"][guild_id][user_id]["bots"] += 1
            elif (datetime.datetime.now(datetime.timezone.utc) - member.created_at).days < 1:
                config["invite_data"][guild_id][user_id]["fake"] += 1
            else: config["invite_data"][guild_id][user_id]["regular"] += 1
            save_config(config)

    # ================= 📊 ইনভাইট চেক কমান্ড =================
    @commands.hybrid_command(name="invite", aliases=["i"])
    async def invite(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        config = load_config()
        data = config.get("invite_data", {}).get(str(ctx.guild.id), {}).get(str(member.id), {"regular": 0, "fake": 0, "leave": 0, "bonus": 0, "bots": 0})
        reg, fake, leave, bonus, bots = data.values()
        total = max(0, (reg + bonus) - (fake + leave))

        embed = discord.Embed(title=f"{member.name}", color=get_theme_color(ctx.guild.id))
        embed.set_thumbnail(url=member.display_avatar.url)
        # আপনার কাস্টম ইমোজি ব্যবহার
        embed.description = (
            f"<:Star:1472268505238863945> **Total Invites:** `{total}`\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<:dot:1472268394391670855> **Join:** `{reg}` | <:dot:1472268394391670855> **Leave:** `{leave}`\n"
            f"<:dot:1472268394391670855> **Fake:** `{fake}` | <:dot:1472268394391670855> **Bonus:** `{bonus}`\n"
            f"<:dot:1472268394391670855> **Bots:** `{bots}`"
        )
        embed.set_author(name=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text="Funny Bot Security", icon_url=self.bot.user.display_avatar.url)
        await ctx.send(embed=embed)

    # ================= 🎁 অ্যাডমিন ম্যানেজমেন্ট কমান্ডস =================
    @commands.hybrid_command(name="addinvite", description="🎁 মেম্বারকে বোনাস ইনভাইট যোগ করে দিন")
    @commands.has_permissions(administrator=True)
    async def addinvite(self, ctx, member: discord.Member, amount: int):
        config = load_config()
        gid, uid = str(ctx.guild.id), str(member.id)
        if gid not in config.setdefault("invite_data", {}): config["invite_data"][gid] = {}
        data = config["invite_data"][gid].setdefault(uid, {"regular": 0, "fake": 0, "leave": 0, "bonus": 0, "bots": 0})
        data["bonus"] += amount
        save_config(config)
        embed = discord.Embed(description=f"<:Star:1472268505238863945> Added **{amount}** bonus invites to {member.mention}!", color=discord.Color.green())
        embed.set_author(name=f"Action by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="removeinvite", description="🗑️ বোনাস ইনভাইট কমিয়ে দিন")
    @commands.has_permissions(administrator=True)
    async def removeinvite(self, ctx, member: discord.Member, amount: int):
        config = load_config()
        gid, uid = str(ctx.guild.id), str(member.id)
        if gid in config.get("invite_data", {}) and uid in config["invite_data"][gid]:
            config["invite_data"][gid][uid]["bonus"] -= amount
            save_config(config)
            embed = discord.Embed(description=f"<:dot:1472268394391670855> Removed **{amount}** bonus invites from {member.mention}!", color=discord.Color.orange())
            embed.set_author(name=f"Action by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

    @commands.hybrid_command(name="resetallinvite", description="⚠️ পুরো সার্ভারের ইনভাইট ডাটা রিসেট করুন")
    @commands.has_permissions(administrator=True)
    async def resetallinvite(self, ctx):
        config = load_config()
        if str(ctx.guild.id) in config.get("invite_data", {}):
            config["invite_data"][str(ctx.guild.id)] = {}
            save_config(config)
        embed = discord.Embed(description="<:dot:1472268394391670855> All server invite data has been cleared!", color=discord.Color.red())
        embed.set_author(name=f"Action by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(InviteTracker(bot))
    
