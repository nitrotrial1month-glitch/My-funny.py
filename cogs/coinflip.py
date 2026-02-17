import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import json
import os
import time  # কুলডাউন হ্যান্ডেল করার জন্য

# utils.py থেকে প্রিমিয়াম চেকার ইমপোর্ট করা হচ্ছে
# যদি আপনার ফোল্ডার স্ট্রাকচার আলাদা হয়, তবে পাথ ঠিক করে নিন
try:
    from utils import check_premium
except ImportError:
    # যদি utils না পায়, তবে বাইপাস করার জন্য ডামি ফাংশন
    def check_premium(user_id, type): return False

ECONOMY_FILE = "economy.json"

class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}  # কুলডাউন ডাটা সেভ রাখার জন্য ডিকশনারি

    # ---------------- Economy ---------------- #

    def get_data(self):
        if not os.path.exists(ECONOMY_FILE):
            return {}
        try:
            with open(ECONOMY_FILE, "r") as f:
                return json.load(f)
        except:
            return {}

    def save_data(self, data):
        with open(ECONOMY_FILE, "w") as f:
            json.dump(data, f, indent=4)

    def update_balance(self, user_id, amount):
        data = self.get_data()
        uid = str(user_id)
        if uid not in data: data[uid] = 0
        data[uid] += amount
        self.save_data(data)
        return data[uid]

    def get_balance(self, user_id):
        data = self.get_data()
        return data.get(str(user_id), 0)

    # ---------------- Safe Send Helper ---------------- #
    async def safe_send(self, ctx, content=None, embed=None, ephemeral=False):
        if ctx.interaction:
            if not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message(content=content, embed=embed, ephemeral=ephemeral)
            else:
                await ctx.followup.send(content=content, embed=embed, ephemeral=ephemeral)
        else:
            await ctx.send(content=content, embed=embed)

    # ---------------- Coinflip Command ---------------- #

    @commands.hybrid_command(name="cf", aliases=["coinflip", "flip"], description="Bet coins (Normal: 250k, Premium: 500k)")
    @app_commands.describe(arg1="Amount OR Side (h/t)", arg2="Side OR Amount (Optional)")
    async def cf(self, ctx: commands.Context, arg1: str, arg2: str | None = None):

        user = ctx.author
        uid = str(user.id)
        u_name = f"**{user.display_name}**"

        # -------- ১. প্রিমিয়াম চেক এবং সেটিং নির্ধারণ -------- #
        # প্রিমিয়াম চেক করা হচ্ছে
        is_premium = check_premium(uid, "user")

        # লিমিট এবং কুলডাউন সেট করা
        MAX_BET_LIMIT = 500000 if is_premium else 250000
        COOLDOWN_TIME = 6 if is_premium else 15

        # -------- ২. কাস্টম কুলডাউন লজিক -------- #
        current_time = time.time()
        
        if uid in self.cooldowns:
            time_passed = current_time - self.cooldowns[uid]
            if time_passed < COOLDOWN_TIME:
                retry_after = round(COOLDOWN_TIME - time_passed, 1)
                return await self.safe_send(ctx, f"{u_name}, please wait **{retry_after}s** before betting again!", ephemeral=True)
        
        # কুলডাউন আপডেট করা (যদি ভ্যালিডেশন ফেইল না করে তবেই সেভ হবে নিচে)
        
        current_bal = self.get_balance(uid)

        # -------- ৩. ইনপুট লজিক -------- #
        amount_str = None
        pick_str = "h"
        valid_sides = ["h", "head", "heads", "t", "tail", "tails"]

        a1 = arg1.lower()
        a2 = arg2.lower() if arg2 else None

        if a1 in valid_sides:
            pick_str = a1
            amount_str = a2
        elif a2 and a2 in valid_sides:
            pick_str = a2
            amount_str = a1
        else:
            amount_str = a1

        # এরর মেসেজ
        if not amount_str:
            return await self.safe_send(ctx, f"{u_name}, please specify an amount! Example: `!cf 100`", ephemeral=True)

        # -------- ৪. এমাউন্ট লজিক (লিমিট সহ) -------- #
        if amount_str in ["all", "max"]:
            bet = min(current_bal, MAX_BET_LIMIT)
        elif amount_str == "half":
            bet = min(int(current_bal / 2), MAX_BET_LIMIT)
        else:
            try:
                bet = int(amount_str)
            except ValueError:
                return await self.safe_send(ctx, f"{u_name}, invalid amount. Use number, 'all', or 'half'.", ephemeral=True)

        if bet <= 0:
            return await self.safe_send(ctx, f"{u_name}, you cannot bet 0 or negative coins.", ephemeral=True)
        if bet > current_bal:
            return await self.safe_send(ctx, f"{u_name}, not enough cash! Balance: **{current_bal}**", ephemeral=True)
        
        # ডায়নামিক লিমিট চেক
        if bet > MAX_BET_LIMIT:
            limit_formatted = "{:,}".format(MAX_BET_LIMIT) # কমা দিয়ে সুন্দর করে দেখাবে (Eg: 500,000)
            return await self.safe_send(ctx, f"{u_name}, your max bet limit is **{limit_formatted}**!", ephemeral=True)

        # সব চেক ঠিক থাকলে কুলডাউন অ্যাপ্লাই করা হবে
        self.cooldowns[uid] = current_time

        # -------- ৫. সাইড এবং ইমোজি সেটআপ -------- #
        user_choice_name = "HEADS"
        if pick_str in ["t", "tail", "tails"]:
            user_choice_name = "TAILS"

        # আপনার দেওয়া ইমোজি
        emoji_spin = "<a:cf:1434413973759070372>"
        emoji_heads = "<:heds:1470863891671027804>"
        emoji_tails = "<:Tails:1434414186875588639>"

        # -------- ৬. স্পিনিং এনিমেশন -------- #
        
        embed_spin = discord.Embed(
            description=f"{u_name} spent **{bet}** and chose **{user_choice_name}**\n{emoji_spin} **The coin spins...**",
            color=0x2b2d31
        )
        
        msg = await ctx.send(embed=embed_spin)

        # ২ সেকেন্ড অপেক্ষা
        await asyncio.sleep(2)

        # -------- ৭. ফলাফল -------- #
        outcome = random.choice(["HEADS", "TAILS"])
        won = (user_choice_name == outcome)
        
        final_emoji = emoji_heads if outcome == "HEADS" else emoji_tails

        if won:
            new_bal = self.update_balance(uid, bet)
            color = discord.Color.green()
            result_text = f"**You won {bet} coins**"
        else:
            new_bal = self.update_balance(uid, -bet)
            color = discord.Color.red()
            result_text = f"**You lost {bet} coins**"

        # -------- ৮. রেজাল্ট এডিট -------- #
        
        embed_result = discord.Embed(
            description=(
                f"{u_name} spent **{bet}** and chose **{user_choice_name}**\n"
                f"{final_emoji} {outcome} {result_text}\n" 
                f"Balance: {new_bal}"
            ),
            color=color
        )

        await msg.edit(embed=embed_result)

# ---------------- Setup ---------------- #

async def setup(bot):
    await bot.add_cog(Gambling(bot))
    
