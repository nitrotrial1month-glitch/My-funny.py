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

    # --- মেম্বার জয়েন ট্র্যাকিং (Bot ডিটেকশন সহ) ---
    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        config = load_config()
        settings = config.get("invite_settings", {}).get(str(guild.id), {})
        if not settings.get("enabled", False): return

        invites_before = self.invites.get(guild.id)
        invites_after = await guild.invites()
        self.invites[guild.id] = invites_after
        inviter = None
        if invites_before:
            for i in invites_before:
                for a in invites_after:
                    if i.code == a.code and a.uses > i.uses:
                        inviter = i.inviter
                        break

        invite_data = config.get("invite_data", {})
        if str(guild.id) not in invite_data: invite_data[str(guild.id)] = {}
        
        if inviter:
            uid = str(inviter.id)
            if uid not in invite_data[str(guild.id)]:
                # নতুন Bots ডাটা স্ট্রাকচার
                invite_data[str(guild.id)][uid] = {"regular": 0, "fake": 0, "leave": 0, "bonus": 0, "bots": 0}
            
            # মেম্বার টাইপ চেক
            if member.bot:
                invite_data[str(guild.id)][uid]["bots"] += 1
            elif (datetime.datetime.now(datetime.timezone.utc) - member.created_at).days < 1:
                invite_data[str(guild.id)][uid]["fake"] += 1
            else:
                invite_data[str(guild.id)][uid]["regular"] += 1

        config["invite_data"] = invite_data
        save_config(config)

    # ================= 📊 STYLISH INVITE CHECK COMMAND =================
    @commands.hybrid_command(
        name="invite",
        aliases=["i"], # শর্ট ফর্ম কমান্ড
        description="📊 View detailed invite statistics with custom icons"
    )
    @app_commands.describe(member="The user whose invites you want to check")
    async def invite(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        config = load_config()
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)

        # ডাটা ফেচ করা (ডিফল্ট ভ্যালু সহ)
        data = config.get("invite_data", {}).get(guild_id, {}).get(user_id, {
            "regular": 0, "fake": 0, "leave": 0, "bonus": 0, "bots": 0
        })

        reg, fake, leave, bonus, bots = data.get("regular", 0), data.get("fake", 0), data.get("leave", 0), data.get("bonus", 0), data.get("bots", 0)
        total = max(0, (reg + bonus) - (fake + leave))

        # --- 🎨 PREMIUM STYLISH EMBED ---
        embed = discord.Embed(
            title=f"{member.name}", # টাইটেলে ইউজারের নাম
            color=get_theme_color(ctx.guild.id),
            timestamp=datetime.datetime.now()
        )
        
        # থাম্বনেইলে ইউজারের ছবি
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # ব্যাকগ্রাউন্ড ইমেজ (যদি সেট করা থাকে)
        settings = config.get("invite_settings", {}).get(guild_id, {})
        bg_image = settings.get("template", {}).get("image")
        if bg_image:
            embed.set_image(url=bg_image)

        # আপনার দেওয়া ইমোজি দিয়ে সাজানো ডেসক্রিপশন
        stats_info = (
            f"<:Star:1472268505238863945> **Total Invites:** `{total}`\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<:dot:1472268394391670855> **Join:** `{reg}`\n"
            f"<:dot:1472268394391670855> **Leave:** `{leave}`\n"
            f"<:dot:1472268394391670855> **Fake:** `{fake}`\n"
            f"<:dot:1472268394391670855> **Bonus:** `{bonus}`\n"
            f"<:dot:1472268394391670855> **Bots:** `{bots}`"
        )
        
        embed.description = stats_info
        embed.set_footer(text=f"Funny Bot Security", icon_url=self.bot.user.display_avatar.url)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(InviteTracker(bot))
        
