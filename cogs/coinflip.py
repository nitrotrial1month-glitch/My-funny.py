import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import json
import os

ECONOMY_FILE = "economy.json"
MAX_BET_LIMIT = 250000

class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

        if uid not in data:
            data[uid] = 0

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

    @commands.hybrid_command(
        name="cf",
        aliases=["coinflip", "flip"],
        description="Bet coins (Max 250k)"
    )
    @app_commands.describe(arg1="Amount OR Side (h/t)", arg2="Side OR Amount (Optional)")
    async def cf(self, ctx: commands.Context, arg1: str, arg2: str | None = None):

        user = ctx.author
        uid = str(user.id)
        current_bal = self.get_balance(uid)
        u_name = f"**{user.display_name}**"

        # -------- Input Logic -------- #

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

        if not amount_str:
            return await self.safe_send(ctx, f"{u_name}, please specify an amount! Example: `!cf 100`", ephemeral=True)

        # -------- Amount Logic -------- #

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

        if bet > MAX_BET_LIMIT:
            return await self.safe_send(ctx, f"{u_name}, max bet limit is **250,000**!", ephemeral=True)

        # -------- Side Setup -------- #

        user_choice_name = "HEADS"
        if pick_str in ["t", "tail", "tails"]:
            user_choice_name = "TAILS"

        # -------- Animation -------- #

        spin_gif = "https://cdn.discordapp.com/emojis/1434413973759070372.gif?quality=lossless"
        heads_gif = "https://cdn.discordapp.com/emojis/1470863891671027804.gif?quality=lossless"
        tails_gif = "https://cdn.discordapp.com/emojis/1434414186875588639.gif?quality=lossless"

        embed_spin = discord.Embed(
            description=f"{u_name} spent **{bet}** and chose **{user_choice_name}**\n**The coin spins...**",
            color=0x2b2d31
        )
        embed_spin.set_thumbnail(url=spin_gif)

        await self.safe_send(ctx, embed=embed_spin)
        await asyncio.sleep(2)

        # -------- Result -------- #

        outcome = random.choice(["HEADS", "TAILS"])
        won = (user_choice_name == outcome)

        final_image = heads_gif if outcome == "HEADS" else tails_gif

        if won:
            new_bal = self.update_balance(uid, bet)
            color = discord.Color.green()
            result_text = f"**You won {bet} coins**"
        else:
            new_bal = self.update_balance(uid, -bet)
            color = discord.Color.red()
            result_text = f"**You lost {bet} coins**"

        embed_result = discord.Embed(
            description=(
                f"{u_name} spent **{bet}** and chose **{user_choice_name}**\n"
                f"## {outcome}\n"
                f"{result_text}\n"
                f"Balance: {new_bal}"
            ),
            color=color
        )
        embed_result.set_thumbnail(url=final_image)

        await ctx.send(embed=embed_result)

# ---------------- Setup ---------------- #

async def setup(bot):
    await bot.add_cog(Gambling(bot))
