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
    """Creates a visual progress bar for streaks"""
    filled = min(level, max_level)
    empty = max_level - filled
    return "🟦" * filled + "⬛" * empty

class DailySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="daily", description="✨ Claim your daily rewards!")
    async def daily(self, ctx: commands.Context):
        user = ctx.author
        uid = str(user.id)
        
        # 1. Load Database using the "inventory" collection to match hunt.py
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        
        # Load daily info
        daily_info = user_data.get("daily", {})
        now = datetime.datetime.now(datetime.timezone.utc)
        last_claim_str = daily_info.get("last_claim")
        last_claim_time = datetime.datetime.fromisoformat(last_claim_str) if last_claim_str else None

        # 2. Cooldown Check (24 Hours)
        if last_claim_time:
            diff = now - last_claim_time
            if diff.total_seconds() < 86400: # 86,400 seconds = 24 hours
                next_claim_ts = int(last_claim_time.timestamp() + 86400)
                
                embed = discord.Embed(
                    description=f"⏳ **Wait!** Your daily reward refreshes <t:{next_claim_ts}:R>.",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed, ephemeral=True)

        # 3. Streak Logic (Reset if gap is more than 48 hours)
        streak = daily_info.get("streak", 0)
        if last_claim_time and (now - last_claim_time).total_seconds() > 172800:
            streak = 1
            streak_status = "⚠️ **Streak Lost!** Started over."
        else:
            streak += 1
            streak_status = "🔥 **Streak Active!**"

        # 4. Reward Calculation
        base_amount = 1000
        streak_bonus = (streak - 1) * 500
        total_cash = base_amount + streak_bonus
        lootboxes = random.randint(2, 3) 

        # 5. Premium Boost (2x Boost)
        is_premium = check_premium(user.id)
        premium_text = ""
        if is_premium:
            total_cash *= 2
            premium_text = "\n💎 **Premium Boost:** `2x Rewards Applied`"
        
        # 6. Database Update (Aligned with HuntSystem)
        # Update Balance
        Database.update_balance(uid, total_cash)
        
        # Update Daily info and Lootboxes in the correct path
        col.update_one(
            {"_id": uid},
            {
                "$set": {
                    "daily.last_claim": now.isoformat(),
                    "daily.streak": streak
                },
                "$inc": {
                    # This path MUST match inventory.lootbox from hunt.py
                    "inventory.lootbox": lootboxes 
                }
            },
            upsert=True
        )

        # 7. Stylish Embed Design
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

        # Cash Reward Field
        embed.add_field(
            name="💰 Cash Reward",
            value=f"```yaml\n+ {total_cash:,} Coins\n``` {premium_text}",
            inline=True
        )

        # Lootbox Reward Field
        embed.add_field(
            name="📦 Lootboxes",
            value=f"```fix\n+ {lootboxes} Boxes\n```",
            inline=True
        )

        # Streak Progress
        bar = create_streak_bar(streak)
        embed.add_field(
            name=f"🔥 Daily Streak: {streak}",
            value=f"{bar}\n*Next Reward:* `{1000 + (streak * 500)}` Coins",
            inline=False
        )

        # Next Claim Timer
        embed.add_field(
            name="⏰ Next Reward",
            value=f"Refreshes **<t:{next_claim_ts}:R>**",
            inline=True
        )
        
        embed.set_footer(text="Economy System • Stay Active!", icon_url=self.bot.user.display_avatar.url)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(DailySystem(bot))
        
