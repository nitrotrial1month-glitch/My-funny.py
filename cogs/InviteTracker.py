import discord
from discord.ext import commands
from discord import app_commands
import datetime
from utils import load_config, save_config, get_theme_color

class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= 📊 HYBRID INVITE COMMAND =================
    @commands.hybrid_command(
        name="invite",
        aliases=["i"], # শর্ট ফর্ম প্রেফিক্স কমান্ডের জন্য
        description="📊 View your or another member's stylish invite stats"
    )
    @app_commands.describe(member="The user whose invites you want to check")
    async def invite(self, ctx: commands.Context, member: discord.Member = None):
        # যদি কেউ মেনশন না থাকে, তবে নিজের ডাটা দেখাবে
        member = member or ctx.author
        config = load_config()
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)

        # ডাটাবেস থেকে তথ্য সংগ্রহ
        data = config.get("invite_data", {}).get(guild_id, {}).get(user_id, {
            "regular": 0, "fake": 0, "leave": 0, "bonus": 0, "bots": 0
        })

        reg, fake, leave, bonus, bots = data.get("regular", 0), data.get("fake", 0), data.get("leave", 0), data.get("bonus", 0), data.get("bots", 0)
        
        # টোটাল ইনভাইট ক্যালকুলেশন
        total = max(0, (reg + bonus) - (fake + leave))

        # --- 🎨 PREMIUM EMBED DESIGN ---
        embed = discord.Embed(
            title=f"{member.name}", # টাইটেলে ইউজারের নাম
            color=get_theme_color(ctx.guild.id),
            timestamp=datetime.datetime.now()
        )
        
        # থাম্বনেইলে ইউজারের প্রোফাইল পিকচার
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # আপনার সেট করা ব্যাকগ্রাউন্ড ইমেজ (যদি থাকে)
        settings = config.get("invite_settings", {}).get(guild_id, {})
        bg_image = settings.get("template", {}).get("image")
        if bg_image:
            embed.set_image(url=bg_image)

        # আপনার দেওয়া ইমোজি এবং ফ্যালকন বটের স্টাইলে সাজানো
        stats_box = (
            f"<:Star:1472268505238863945> **Total Invites:** `{total}`\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<:dot:1472268394391670855> **Join:** `{reg}`\n"
            f"<:dot:1472268394391670855> **Leave:** `{leave}`\n"
            f"<:dot:1472268394391670855> **Fake:** `{fake}`\n"
            f"<:dot:1472268394391670855> **Bonus:** `{bonus}`\n"
            f"<:dot:1472268394391670855> **Bots:** `{bots}`"
        )
        
        embed.description = stats_box
        
        embed.set_footer(
            text=f"Funny Bot Security • Requested by {ctx.author.name}", 
            icon_url=self.bot.user.display_avatar.url
        )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(InviteTracker(bot))
    
