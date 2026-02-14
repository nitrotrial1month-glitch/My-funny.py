import discord
from discord.ext import commands
from discord import app_commands
import datetime
from utils import load_config, save_config, get_theme_color

class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites = {} # ইনভাইট ক্যাশ

    # ================= 🛡️ AUTO-ENABLE & CACHE =================
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """বট জয়েন করলে অটোমেটিক সেটিংস কনফিগার করবে"""
        config = load_config()
        guild_id = str(guild.id)
        if guild_id not in config["invite_settings"]:
            config["invite_settings"][guild_id] = {"enabled": True, "log_channel": None}
            save_config(config)
        try:
            self.invites[guild.id] = await guild.invites()
        except: pass

    # ================= 📊 THE INVITES COMMAND (NO RANK) =================
    @commands.hybrid_command(
        name="invites",
        description="📊 View detailed invite statistics (Regular, Fake, Leave, Bonus)"
    )
    @app_commands.describe(member="The member whose invites you want to check")
    async def invites(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        config = load_config()
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)

        # ডাটা সংগ্রহ করা
        user_data = config.get("invite_data", {}).get(guild_id, {}).get(user_id, {
            "regular": 0, "fake": 0, "leave": 0, "bonus": 0
        })

        reg = user_data.get("regular", 0)
        fake = user_data.get("fake", 0)
        leave = user_data.get("leave", 0)
        bonus = user_data.get("bonus", 0)
        
        # টোটাল ক্যালকুলেশন: (Regular + Bonus) - (Fake + Leave)
        total = max(0, (reg + bonus) - (fake + leave))

        # --- PREMIUM MINIMALIST EMBED ---
        embed = discord.Embed(
            title=f"📊 Invite Analytics: {member.display_name}",
            color=get_theme_color(ctx.guild.id),
            timestamp=datetime.datetime.now()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # ডাটা প্রেজেন্টেশন (কার্টুনিশ নয়, প্রফেশনাল লুক)
        stats_box = (
            f"🎯 **Total Success:** `{total}`\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✅ **Regular:** `{reg}`\n"
            f"🚫 **Fake:** `{fake}`\n"
            f"📤 **Leave:** `{leave}`\n"
            f"🎁 **Bonus:** `{bonus}`"
        )
        
        embed.description = stats_box
        
        embed.set_footer(
            text=f"Requested by {ctx.author.name} • Wow Bot Security", 
            icon_url=self.bot.user.display_avatar.url
        )

        await ctx.send(embed=embed)

    # ================= 🎁 BONUS SYSTEM (ADMIN ONLY) =================
    @commands.hybrid_command(name="addbonus", description="🎁 Manually add bonus invites to a user")
    @commands.has_permissions(administrator=True)
    async def addbonus(self, ctx, member: discord.Member, amount: int):
        """ইকোনমি সিস্টেমের সাথে সামঞ্জস্য রেখে বোনাস দেওয়ার ব্যবস্থা"""
        config = load_config()
        gid, uid = str(ctx.guild.id), str(member.id)

        if "invite_data" not in config: config["invite_data"] = {}
        if gid not in config["invite_data"]: config["invite_data"][gid] = {}
        if uid not in config["invite_data"][gid]: 
            config["invite_data"][gid][uid] = {"regular": 0, "fake": 0, "leave": 0, "bonus": 0}

        config["invite_data"][gid][uid]["bonus"] += amount
        save_config(config)
        
        await ctx.send(f"✅ Added **{amount}** bonus invites to {member.mention}!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(InviteTracker(bot))
  
