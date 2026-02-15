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

    # ================= 📥 মেম্বার ও বট জয়েন ট্র্যাকিং =================
    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        config = load_config()
        inviter = None

        # ১. যদি মেম্বারটি একটি 'বট' হয়
        if member.bot:
            try:
                # অডিট লগ চেক করে ইনভাইটার খোঁজা
                async for entry in guild.audit_logs(action=discord.AuditLogAction.bot_add, limit=5):
                    if entry.target.id == member.id:
                        inviter = entry.user
                        break
            except Exception as e:
                print(f"Audit log error: {e}")

        # ২. যদি মেম্বারটি সাধারণ মানুষ হয়
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

        # ৩. ডাটাবেসে সেভ করা
        if inviter:
            guild_id, user_id = str(guild.id), str(inviter.id)
            if "invite_data" not in config: config["invite_data"] = {}
            if guild_id not in config["invite_data"]: config["invite_data"][guild_id] = {}
            if user_id not in config["invite_data"][guild_id]:
                config["invite_data"][guild_id][user_id] = {"regular": 0, "fake": 0, "leave": 0, "bonus": 0, "bots": 0}
            
            if member.bot:
                config["invite_data"][guild_id][user_id]["bots"] += 1
            elif (datetime.datetime.now(datetime.timezone.utc) - member.created_at).days < 1:
                config["invite_data"][guild_id][user_id]["fake"] += 1
            else:
                config["invite_data"][guild_id][user_id]["regular"] += 1
            
            save_config(config)

    # ================= 📊 স্টাইলিশ ইনভাইট চেক কমান্ড =================
    @commands.hybrid_command(name="invite", aliases=["i"])
    async def invite(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        config = load_config()
        data = config.get("invite_data", {}).get(str(ctx.guild.id), {}).get(str(member.id), {
            "regular": 0, "fake": 0, "leave": 0, "bonus": 0, "bots": 0
        })

        reg, fake, leave, bonus, bots = data.get("regular", 0), data.get("fake", 0), data.get("leave", 0), data.get("bonus", 0), data.get("bots", 0)
        total = max(0, (reg + bonus) - (fake + leave))

        embed = discord.Embed(title=f"{member.name}", color=get_theme_color(ctx.guild.id))
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.description = (
            f"<:Star:1472268505238863945> **Total Invites:** `{total}`\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<:dot:1472268394391670855> **Join:** `{reg}`\n"
            f"<:dot:1472268394391670855> **Leave:** `{leave}`\n"
            f"<:dot:1472268394391670855> **Fake:** `{fake}`\n"
            f"<:dot:1472268394391670855> **Bonus:** `{bonus}`\n"
            f"<:dot:1472268394391670855> **Bots:** `{bots}`"
        )
        embed.set_author(name=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text="Funny Bot Security", icon_url=self.bot.user.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(InviteTracker(bot))
                    
