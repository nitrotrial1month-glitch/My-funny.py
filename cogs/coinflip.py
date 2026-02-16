import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import json
import os

ECONOMY_FILE = "economy.json"
MAX_BET_LIMIT = 250000  # সর্বোচ্চ ২৫০k লিমিট

class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Economy Helper Functions ---
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
        if uid not in data:
            data[uid] = 0
        data[uid] += amount
        self.save_data(data)
        return data[uid]

    def get_balance(self, user_id):
        data = self.get_data()
        return data.get(str(user_id), 0)

    # --- Main Coinflip Command ---
    @commands.hybrid_command(name="cf", aliases=["coinflip", "flip", "CF", "Cf"], description="Bet coins (Max 250k)")
    @app_commands.describe(arg1="Amount OR Side (h/t)", arg2="Side OR Amount (Optional)")
    async def cf(self, ctx, arg1: str, arg2: str = None):
        user = ctx.author
        uid = str(user.id)
        current_bal = self.get_balance(uid)
        
        # ইউজারের ডিসপ্লে নেম (এরর এবং ডিজাইনের জন্য)
        u_name = f"**{user.display_name}**"

        # --- ১. আপনার দেওয়া ইনপুট লজিক (হুবহু রাখা হয়েছে) ---
        amount_str = None
        pick_str = "h" # ডিফল্ট হেডস
        
        valid_sides = ["h", "head", "heads", "t", "tail", "tails"]
        
        # ইনপুট লোয়ারকেস করা
        a1 = arg1.lower()
        a2 = arg2.lower() if arg2 else None

        # লজিক চেক:
        if a1 in valid_sides:
            pick_str = a1
            amount_str = a2 
        elif a2 and a2 in valid_sides:
            pick_str = a2
            amount_str = a1 
        else:
            amount_str = a1

        # এরর মেসেজ (নাম সহ)
        if not amount_str:
            return await ctx.send(f"{u_name}, please specify an amount! Example: `!cf 100`")

        # --- ২. এমাউন্ট ক্যালকুলেশন এবং লিমিট ---
        bet = 0
        
        if amount_str in ["all", "max"]:
            bet = min(current_bal, MAX_BET_LIMIT)
        elif amount_str == "half":
            bet = int(current_bal / 2)
            if bet > MAX_BET_LIMIT: bet = MAX_BET_LIMIT
        else:
            try:
                bet = int(amount_str)
            except ValueError:
                return await ctx.send(f"{u_name}, invalid amount. Use a number, 'all', or 'half'.")

        # ভ্যালিডেশন (নাম সহ)
        if bet <= 0:
            return await ctx.send(f"{u_name}, you cannot bet 0 or negative coins.", ephemeral=True)
        if bet > current_bal:
            return await ctx.send(f"{u_name}, not enough cash! Your Balance: **{current_bal}**", ephemeral=True)
        if bet > MAX_BET_LIMIT:
            return await ctx.send(f"{u_name}, max bet limit is **250,000**!", ephemeral=True)

        # --- ৩. সাইড কনফার্মেশন ---
        user_choice_name = "HEADS" # ডিজাইনের জন্য বড় হাতের
        if pick_str in ["t", "tail", "tails"]:
            user_choice_name = "TAILS"

        # --- ৪. ভিজ্যুয়াল সেটআপ (GIF Links) ---
        url_spin = "https://cdn.discordapp.com/emojis/1434413973759070372.gif?quality=lossless"
        
        # রেজাল্ট ইমোজি এবং GIF
        emoji_heads = "<:heds:1470863891671027804>"
        url_heads = "https://cdn.discordapp.com/emojis/1470863891671027804.gif?quality=lossless"
        
        emoji_tails = "<:Tails:1434414186875588639>"
        url_tails = "https://cdn.discordapp.com/emojis/1434414186875588639.gif?quality=lossless"

        # ৫. স্পিনিং এনিমেশন (আপনার চাওয়া নতুন ডিজাইন)
        embed_spin = discord.Embed(
            description=f"{u_name} spent **{bet}** and chose **{user_choice_name}**\n**The coin spins...**",
            color=0x2b2d31
        )
        embed_spin.set_thumbnail(url=url_spin)
        msg = await ctx.send(embed=embed_spin)

        # ২ সেকেন্ড ওয়েট
        await asyncio.sleep(2)

        # ৬. ফলাফল
        outcome = random.choice(["HEADS", "TAILS"])
        won = (user_choice_name == outcome)
        
        final_emoji = emoji_heads if outcome == "HEADS" else emoji_tails
        final_image_url = url_heads if outcome == "HEADS" else url_tails

        # ৭. রেজাল্ট ডিসপ্লে (আপনার চাওয়া নতুন ডিজাইন)
        if won:
            new_bal = self.update_balance(uid, bet)
            
            embed_win = discord.Embed(
                description=f"{u_name} spent **{bet}** and chose **{user_choice_name}**\n## {final_emoji}  {outcome}\n**You won {bet} coins**\nBalance: {new_bal}",
                color=discord.Color.green()
            )
            embed_win.set_thumbnail(url=final_image_url)
            await msg.edit(embed=embed_win)
        else:
            new_bal = self.update_balance(uid, -bet)
            
            embed_lose = discord.Embed(
                description=f"{u_name} spent **{bet}** and chose **{user_choice_name}**\n## {final_emoji}  {outcome}\n**You lost {bet} coins**\nBalance: {new_bal}",
                color=discord.Color.red()
            )
            embed_lose.set_thumbnail(url=final_image_url)
            await msg.edit(embed=embed_lose)

async def setup(bot):
    await bot.add_cog(Gambling(bot))
        
