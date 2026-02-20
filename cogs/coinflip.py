import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import time
from database import Database
from utils import get_theme_color, check_premium

class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}  # Manual dictionary for dynamic cooldowns

    # ---------------- 🏹 Database Helpers ---------------- #
    
    def get_user_balance(self, user_id):
        col = Database.get_collection("inventory")
        data = col.find_one({"_id": str(user_id)}) or {}
        return data.get("balance", 0)

    def update_user_balance(self, user_id, amount):
        col = Database.get_collection("inventory")
        col.update_one(
            {"_id": str(user_id)},
            {"$inc": {"balance": amount}},
            upsert=True
        )
        # Return new balance
        data = col.find_one({"_id": str(user_id)})
        return data.get("balance", 0)

    # ---------------- 🪙 Coinflip Command ---------------- #

    @commands.hybrid_command(name="cf", aliases=["coinflip", "flip"], description="Bet coins (Normal: 250k, Premium: 500k)")
    @app_commands.describe(arg1="Amount OR Side (h/t)", arg2="Side OR Amount (Optional)")
    async def cf(self, ctx: commands.Context, arg1: str, arg2: str | None = None):
        user = ctx.author
        uid = str(user.id)
        u_name = f"**{user.display_name}**"

        # 1. Premium Check & Settings
        is_premium = check_premium(user.id) # utils logic based on your system
        MAX_BET_LIMIT = 500000 if is_premium else 250000
        COOLDOWN_TIME = 6 if is_premium else 15

        # 2. Dynamic Cooldown Logic
        current_time = time.time()
        if uid in self.cooldowns:
            time_passed = current_time - self.cooldowns[uid]
            if time_passed < COOLDOWN_TIME:
                retry_after = round(COOLDOWN_TIME - time_passed, 1)
                return await ctx.send(f"⏳ {u_name}, please wait **{retry_after}s** before betting again!", ephemeral=True)

        # 3. Balance & Input Logic
        current_bal = self.get_user_balance(uid)
        
        # Determine side and amount from arguments
        valid_sides = ["h", "head", "heads", "t", "tail", "tails"]
        pick_str = "heads"
        amount_str = None

        a1 = arg1.lower()
        a2 = arg2.lower() if arg2 else None

        if a1 in valid_sides:
            pick_str = "heads" if a1 in ["h", "head", "heads"] else "tails"
            amount_str = a2
        elif a2 and a2 in valid_sides:
            pick_str = "heads" if a2 in ["h", "head", "heads"] else "tails"
            amount_str = a1
        else:
            amount_str = a1

        if not amount_str:
            return await ctx.send(f"❌ {u_name}, please specify an amount! Example: `!cf 100 h`", ephemeral=True)

        # 4. Amount Calculation
        if amount_str in ["all", "max"]:
            bet = min(current_bal, MAX_BET_LIMIT)
        elif amount_str == "half":
            bet = min(int(current_bal / 2), MAX_BET_LIMIT)
        else:
            try:
                bet = int(amount_str)
            except ValueError:
                return await ctx.send(f"❌ {u_name}, invalid amount. Use numbers, 'all', or 'half'.", ephemeral=True)

        # Validation Checks
        if bet <= 0:
            return await ctx.send(f"❌ {u_name}, you cannot bet 0 or negative coins.", ephemeral=True)
        if bet > current_bal:
            return await ctx.send(f"❌ {u_name}, not enough cash! Balance: `{current_bal:,}`", ephemeral=True)
        if bet > MAX_BET_LIMIT:
            limit_formatted = "{:,}".format(MAX_BET_LIMIT)
            return await ctx.send(f"❌ {u_name}, your max bet limit is **{limit_formatted}**!", ephemeral=True)

        # Apply Cooldown after validation
        self.cooldowns[uid] = current_time

        # 5. Visual Setup (Emojis)
        emoji_spin = "<a:cf:1434413973759070372>"
        emoji_heads = "<:heds:1470863891671027804>"
        emoji_tails = "<:Tails:1434414186875588639>"
        theme_color = get_theme_color(ctx.guild.id)

        # 6. Animation Embed
        embed_spin = discord.Embed(
            description=f"{u_name} spent **{bet:,}** and chose **{pick_str.upper()}**\n{emoji_spin} **The coin spins...**",
            color=theme_color
        )
        msg = await ctx.send(embed=embed_spin)

        await asyncio.sleep(2) # Animation delay

        # 7. Outcome Calculation
        outcome = random.choice(["heads", "tails"])
        won = (pick_str == outcome)
        final_emoji = emoji_heads if outcome == "heads" else emoji_tails

        if won:
            new_bal = self.update_user_balance(uid, bet)
            result_color = discord.Color.green()
            result_text = f"**You won {bet:,} coins**"
        else:
            new_bal = self.update_user_balance(uid, -bet)
            result_color = discord.Color.red()
            result_text = f"**You lost {bet:,} coins**"

        # 8. Final Result Edit
        embed_result = discord.Embed(
            description=(
                f"{u_name} spent **{bet:,}** and chose **{pick_str.upper()}**\n"
                f"{final_emoji} **{outcome.upper()}** | {result_text}\n" 
                f"**New Balance:** `{new_bal:,}` coins"
            ),
            color=result_color
        )
        embed_result.set_footer(text=f"Requested by {user.name}", icon_url=user.display_avatar.url)

        await msg.edit(embed=embed_result)

async def setup(bot):
    await bot.add_cog(Gambling(bot))
    
