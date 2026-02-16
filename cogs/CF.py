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
        
        # ইউজারের ডিসপ্লে নেম (বোল্ড)
        u_name = f"**{user.display_name}**"

        # --- ১. ইনপুট না দিলে ---
        if arg1 is None:
            return await ctx.send(f"{u_name}, please specify an amount to bet.")

        # --- ২. স্মার্ট ইনপুট ডিটেকশন (Smart Detection) ---
        # আমরা খুঁজে বের করবো কোনটা এমাউন্ট আর কোনটা সাইড
        
        amount_raw = None
        pick_str = "h" # ডিফল্ট সব সময় হেডস (Heads)

        # সম্ভাব্য সাইড লিস্ট
        sides = ["h", "head", "heads", "t", "tail", "tails"]
        # সম্ভাব্য কিওয়ার্ড
        keywords = ["all", "max", "half"]

        # ইনপুট লিস্টে নেওয়া হলো
        inputs = []
        if arg1: inputs.append(arg1.lower())
        if arg2: inputs.append(arg2.lower())

        for i in inputs:
            if i in sides:
                pick_str = i # সাইড পাওয়া গেছে
            elif i in keywords or i.isdigit():
                amount_raw = i # এমাউন্ট পাওয়া গেছে

        # যদি ইউজার সাইড দিয়েছে কিন্তু এমাউন্ট দেয়নি (যেমন: !cf h)
        if amount_raw is None:
             # চেক করি arg1 কি সংখ্যা হতে পারে? (যদি isdigit চেক মিস হয়)
            if arg1.lower() not in sides:
                 amount_raw = arg1.lower()
            else:
                 return await ctx.send(f"{u_name}, please specify how much you want to bet.")

        # --- ৩. এমাউন্ট ক্যালকুলেশন ---
        bet = 0
        
        if amount_raw in ["all", "max"]:
            bet = min(current_bal, MAX_BET_LIMIT)
        elif amount_raw == "half":
            bet = int(current_bal / 2)
            if bet > MAX_BET_LIMIT: bet = MAX_BET_LIMIT
        else:
            try:
                bet = int(amount_raw)
            except ValueError:
                # যদি কেউ 'potato' লিখে, তখন তো আর বিট হবে না
                return await ctx.send(f"{u_name}, invalid bet amount.")

        # --- ৪. ভ্যালিডেশন ---
        if bet <= 0:
            return await ctx.send(f"{u_name}, you cannot bet 0 coins.", ephemeral=True)
        if bet > current_bal:
            return await ctx.send(f"{u_name}, you don't have enough coins! Balance: **{current_bal}**", ephemeral=True)
        if bet > MAX_BET_LIMIT:
            return await ctx.send(f"{u_name}, max bet limit is **250,000**!", ephemeral=True)

        # --- ৫. সাইড কনফার্মেশন ---
        user_choice_name = "HEADS"
        if pick_str in ["t", "tail", "tails"]:
            user_choice_name = "TAILS"

        # --- ৬. ভিজ্যুয়ালস (GIF) ---
        url_spin = "https://cdn.discordapp.com/emojis/1434413973759070372.gif?quality=lossless"
        
        # GIF Links for Results
        emoji_heads = "<:heds:1470863891671027804>"
        url_heads = "https://cdn.discordapp.com/emojis/1470863891671027804.gif?quality=lossless"
        
        emoji_tails = "<:Tails:1434414186875588639>"
        url_tails = "https://cdn.discordapp.com/emojis/1434414186875588639.gif?quality=lossless"

        # ৭. স্পিনিং এনিমেশন
        embed_spin = discord.Embed(
            description=f"{u_name} spent **{bet}** and chose **{user_choice_name}**\n**The coin spins...**",
            color=0x2b2d31
        )
        embed_spin.set_thumbnail(url=url_spin)
        msg = await ctx.send(embed=embed_spin)

        # ওয়েট
        await asyncio.sleep(2)

        # ৮. ফলাফল
        outcome = random.choice(["HEADS", "TAILS"])
        won = (user_choice_name == outcome)
        
        final_emoji = emoji_heads if outcome == "HEADS" else emoji_tails
        final_image_url = url_heads if outcome == "HEADS" else url_tails

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
                
