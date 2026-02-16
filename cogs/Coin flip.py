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
    @app_commands.describe(arg1="Amount or Side", arg2="Side or Amount")
    async def cf(self, ctx, arg1: str = None, arg2: str = None):
        user = ctx.author
        uid = str(user.id)
        current_bal = self.get_balance(uid)
        
        # ইউজারের ডিসপ্লে নেম (এরর মেসেজ ও ডিজাইনের জন্য)
        u_name = f"**{user.display_name}**"

        # --- ১. ইনপুট হ্যান্ডলিং (সব ফরম্যাট সাপোর্ট করার জন্য) ---
        amount_str = None
        pick_str = "h" # ডিফল্ট হেডস (যদি কিছু না বলে)

        valid_sides = ["h", "head", "heads", "t", "tail", "tails"]
        valid_amounts = ["all", "max", "half"]

        # ইনপুট ভেরিফিকেশন ফাংশন
        def is_amount(s):
            return s.isdigit() or s.lower() in valid_amounts
        
        def is_side(s):
            return s.lower() in valid_sides

        # ইনপুট লজিক চেক
        if arg1 and not arg2:
            # কেস ১: শুধু একটা আর্গুমেন্ট (যেমন: !cf 100 বা !cf all)
            if is_amount(arg1):
                amount_str = arg1
            elif is_side(arg1):
                # যদি কেউ শুধু !cf h লেখে, তখন এমাউন্ট মিসিং
                return await ctx.send(f"{u_name}, please specify an amount to bet.")
            else:
                return await ctx.send(f"{u_name}, invalid input format.")
                
        elif arg1 and arg2:
            # কেস ২: দুইটা আর্গুমেন্ট (যেমন: !cf 100 t বা !cf t 100)
            if is_amount(arg1) and is_side(arg2):
                amount_str = arg1
                pick_str = arg2
            elif is_side(arg1) and is_amount(arg2):
                pick_str = arg1
                amount_str = arg2
            else:
                 return await ctx.send(f"{u_name}, invalid input. Use `!cf <amount> <side>`.")
        else:
            # কেস ৩: কোনো আর্গুমেন্ট নেই (!cf)
            return await ctx.send(f"{u_name}, please specify an amount.")

        # --- ২. এমাউন্ট ক্যালকুলেশন এবং লিমিট ---
        bet = 0
        amount_str = amount_str.lower()
        
        if amount_str in ["all", "max"]:
            bet = min(current_bal, MAX_BET_LIMIT)
        elif amount_str == "half":
            bet = int(current_bal / 2)
            if bet > MAX_BET_LIMIT: bet = MAX_BET_LIMIT
        else:
            try:
                bet = int(amount_str)
            except ValueError:
                return await ctx.send(f"{u_name}, invalid amount.")

        # --- ৩. এরর চেকিং (নাম সহ) ---
        if bet <= 0:
            return await ctx.send(f"{u_name}, you cannot bet 0 coins.", ephemeral=True)
        if bet > current_bal:
            return await ctx.send(f"{u_name}, you don't have enough coins! Balance: **{current_bal}**", ephemeral=True)
        if bet > MAX_BET_LIMIT:
            # এখানে user.display_name ইউজ করা হচ্ছে, ইমোজি নেই
            return await ctx.send(f"{u_name}, max bet limit is **250,000**!", ephemeral=True)

        # --- ৪. সাইড কনফার্মেশন ---
        user_choice_name = "HEADS"
        if pick_str.lower() in ["t", "tail", "tails"]:
            user_choice_name = "TAILS"

        # --- ৫. ভিজ্যুয়াল সেটআপ (GIF Links) ---
        url_spin = "https://cdn.discordapp.com/emojis/1434413973759070372.gif?quality=lossless"
        
        emoji_heads = "<:heds:1470863891671027804>"
        url_heads = "https://cdn.discordapp.com/emojis/1470863891671027804.gif?quality=lossless"
        
        emoji_tails = "<:Tails:1434414186875588639>"
        url_tails = "https://cdn.discordapp.com/emojis/1434414186875588639.gif?quality=lossless"

        # --- ৬. স্পিনিং এনিমেশন (আপনার নির্দিষ্ট ফরম্যাট) ---
        # ফরম্যাট:
        # **Name** spent **Amount** and chose **SIDE**
        # **The coin spins...**
        embed_spin = discord.Embed(
            description=f"{u_name} spent **{bet}** and chose **{user_choice_name}**\n**The coin spins...**",
            color=0x2b2d31
        )
        embed_spin.set_thumbnail(url=url_spin)
        msg = await ctx.send(embed=embed_spin)

        # ২ সেকেন্ড ওয়েট
        await asyncio.sleep(2)

        # --- ৭. ফলাফল লজিক ---
        outcome = random.choice(["HEADS", "TAILS"])
        won = (user_choice_name == outcome)
        
        final_emoji = emoji_heads if outcome == "HEADS" else emoji_tails
        final_image_url = url_heads if outcome == "HEADS" else url_tails

        # --- ৮. রেজাল্ট ডিসপ্লে ---
        # ফরম্যাট:
        # **Name** spent **Amount** and chose **SIDE** (আগের লাইন সেইম থাকবে)
        # ## Emoji RESULT
        # **You won/lost Amount coins**
        # Balance: NewBalance
        
        if won:
            new_bal = self.update_balance(uid, bet)
            
            embed_win = discord.Embed(
                description=f"{u_name} spent **{bet}** and chose **{user_choice_name}**\n## {final_emoji}  {outcome} \n**You won {bet} coins**\nBalance: {new_bal}",
                color=discord.Color.green()
            )
            embed_win.set_thumbnail(url=final_image_url)
            await msg.edit(embed=embed_win)
        
        else:
            new_bal = self.update_balance(uid, -bet)
            
            embed_lose = discord.Embed(
                description=f"{u_name} spent **{bet}** and chose **{user_choice_name}**\n## {final_emoji}  {outcome} \n**You lost {bet} coins**\nBalance: {new_bal}",
                color=discord.Color.red()
            )
            embed_lose.set_thumbnail(url=final_image_url)
            await msg.edit(embed=embed_lose)

async def setup(bot):
    await bot.add_cog(Gambling(bot))
    
