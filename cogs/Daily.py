import discord
from discord.ext import commands
from discord import app_commands
import datetime
import random
import time
from database import Database
from utils import get_theme_color, check_premium

# ================= 🎨 PROGRESS BAR FUNCTION =================
def create_streak_bar(level, max_level=10):
    """স্ট্রাইক অনুযায়ী একটি সুন্দর প্রোগ্রেস বার তৈরি করে"""
    filled = min(level, max_level)
    empty = max_level - filled
    return "🟦" * filled + "⬛" * empty

class DailySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="daily", description="✨ Claim your premium daily rewards!")
    async def daily(self, ctx: commands.Context):
        user = ctx.author
        uid = str(user.id)
        
        # ১. হান্ট সিস্টেমের সাথে মিল রেখে "inventory" কালেকশন ব্যবহার করা হয়েছে
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        
        # ডেইলি ইনফো লোড
        daily_info = user_data.get("daily", {})
        now = datetime.datetime.now(datetime.timezone.utc)
        last_claim_str = daily_info.get("last_claim")
        last_claim_time = datetime.datetime.fromisoformat(last_claim_str) if last_claim_str else None

        # ২. কুলডাউন চেক (২৪ ঘন্টা)
        if last_claim_time:
            diff = now - last_claim_time
            if diff.total_seconds() < 86400: # ৮৬৪০০ সেকেন্ড = ২৪ ঘন্টা
                next_claim_ts = int(last_claim_time.timestamp() + 86400)
                
                embed = discord.Embed(
                    description=f"⏳ **Wait!** Your daily reward refreshes <t:{next_claim_ts}:R>.",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed, ephemeral=True)

        # ৩. স্ট্রাইক লজিক (৪৮ ঘন্টার বেশি গ্যাপ হলে রিসেট)
        streak = daily_info.get("streak", 0)
        if last_claim_time and (now - last_claim_time).total_seconds() > 172800:
            streak = 1
            streak_status = "⚠️ **Streak Lost!** Started over."
        else:
            streak += 1
            streak_status = "🔥 **Streak Active!**"

        # ৪. রিওয়ার্ড ক্যালকুলেশন
        base_amount = 1000
        streak_bonus = (streak - 1) * 500
        total_cash = base_amount + streak_bonus
        lootboxes = random.randint(2, 3) # ২ থেকে ৩ টি লুটবক্স

        # ৫. প্রিমিয়াম বুস্ট (2x Boost)
        is_premium = check_premium(user.id)
        premium_text = ""
        if is_premium:
            total_cash *= 2
            premium_text = "\n💎 **Premium Boost:** `2x Rewards Applied`"
        
        # ৬. ডাটাবেস আপডেট (HuntSystem এর সাথে মিলিয়ে)
        # টাকা আপডেট
        Database.update_balance(uid, total_cash)
        
        # ডেইলি স্ট্রাইক এবং লুটবক্স আপডেট (items.Lootbox পাথে)
        col.update_one(
            {"_id": uid},
            {
                "$set": {
                    "daily.last_claim": now.isoformat(),
                    "daily.streak": streak
                },
                "$inc": {
                    "items.Lootbox": lootboxes # আপনার HuntSystem এর Items.Lootbox এর সাথে মিলবে
                }
            },
            upsert=True
        )

        # ৭. 🔥 স্টাইলিশ এম্বেড ডিজাইন 🔥
        theme_color = get_theme_color(ctx.guild.id)
        next_claim_ts = int(time.time() + 86400)
        
        embed = discord.Embed(title=f"📅 Daily Check-In", color=theme_color)
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/9496/9496016.png") # Gift Icon

        embed.description = (
            f"Here is your daily reward, **{user.name}**!\n"
            f"{streak_status}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )

        # 💰 ক্যাশ রিওয়ার্ড
        embed.add_field(
            name="💰 Cash Reward",
            value=f"```yaml\n+ {total_cash:,} Coins\n``` {premium_text}",
            inline=True
        )

        # 📦 লুটবক্স রিওয়ার্ড
        embed.add_field(
            name="📦 Lootboxes",
            value=f"```fix\n+ {lootboxes} Boxes\n```",
            inline=True
        )

        # 🔥 স্ট্রাইক প্রোগ্রেস
        bar = create_streak_bar(streak)
        embed.add_field(
            name=f"🔥 Daily Streak: {streak}",
            value=f"{bar}\n*Next Reward:* `{1000 + (streak * 500)}` Coins",
            inline=False
        )

        # ⏰ নেক্সট ক্লেইম টাইমার
        embed.add_field(
            name="⏰ Next Reward",
            value=f"Refreshes **<t:{next_claim_ts}:R>**",
            inline=True
        )
        
        embed.set_footer(text="Economy System • Stay Active!", icon_url=self.bot.user.display_avatar.url)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(DailySystem(bot))
    
