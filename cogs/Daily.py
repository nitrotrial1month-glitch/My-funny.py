import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
from datetime import datetime, timedelta

# ফাইল পাথ
ECONOMY_FILE = "economy.json"
DAILY_FILE = "daily_timer.json"

class DailyReward(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- হেল্পার ফাংশন (ডাটা লোড/সেভ) ---
    def load_json(self, filename):
        if not os.path.exists(filename): return {}
        try:
            with open(filename, "r") as f: return json.load(f)
        except: return {}

    def save_json(self, filename, data):
        with open(filename, "w") as f: json.dump(data, f, indent=4)

    def update_balance(self, user_id, amount):
        data = self.load_json(ECONOMY_FILE)
        uid = str(user_id)
        if uid not in data: data[uid] = 0
        data[uid] += amount
        self.save_json(ECONOMY_FILE, data)
        return data[uid]

    # --- মেইন ডেইলি কমান্ড ---
    @commands.hybrid_command(name="daily", description="📅 Claim your daily free coins")
    async def daily(self, ctx):
        user = ctx.author
        uid = str(user.id)
        
        # ১. কুলডাউন চেক করা
        timers = self.load_json(DAILY_FILE)
        
        if uid in timers:
            last_claim = datetime.fromisoformat(timers[uid])
            # ২৪ ঘণ্টা যোগ করা
            next_claim = last_claim + timedelta(days=1)
            
            if datetime.now() < next_claim:
                # এখনো সময় হয়নি
                remaining = next_claim - datetime.now()
                # সুন্দর ফরম্যাট (ঘণ্টা ও মিনিট)
                hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                
                embed_wait = discord.Embed(
                    description=f"⏳ **Wait a bit!** You can claim again in **{hours}h {minutes}m**.",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed_wait, ephemeral=True)

        # ২. টাকা দেওয়া (৫০০ থেকে ১০০০ এর মধ্যে র‍্যান্ডম)
        amount = random.randint(500, 1000)
        new_balance = self.update_balance(uid, amount)

        # ৩. সময় সেভ করা
        timers[uid] = datetime.now().isoformat()
        self.save_json(DAILY_FILE, timers)

        # ৪. সাকসেস মেসেজ
        embed_success = discord.Embed(
            title="📅 Daily Reward Claimed!",
            description=f"You received **{amount}** coins!\n💰 **New Balance:** `{new_balance}`",
            color=discord.Color.green()
        )
        embed_success.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2953/2953363.png") # ক্যালেন্ডার আইকন
        embed_success.set_footer(text="Come back tomorrow for more!", icon_url=user.display_avatar.url)
        
        await ctx.send(embed=embed_success)

async def setup(bot):
    await bot.add_cog(DailyReward(bot))
              
