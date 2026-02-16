import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import json
import os

ECONOMY_FILE = "economy.json"

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
    @commands.hybrid_command(name="cf", aliases=["coinflip", "flip"], description="Bet coins on Heads or Tails")
    @app_commands.describe(amount="Amount to bet", pick="h (Heads) or t (Tails)")
    async def cf(self, ctx, amount: str, pick: str = "h"):
        user = ctx.author
        uid = str(user.id)
        current_bal = self.get_balance(uid)

        # 1. Bet Amount Logic
        bet = 0
        if amount.lower() in ["all", "max"]:
            bet = current_bal
        elif amount.lower() == "half":
            bet = int(current_bal / 2)
        else:
            try:
                bet = int(amount)
            except ValueError:
                return await ctx.send("Invalid amount. Use a number or 'all'.")

        if bet <= 0:
            return await ctx.send("You cannot bet 0 or negative coins.", ephemeral=True)
        if bet > current_bal:
            return await ctx.send(f"Not enough cash. Balance: {current_bal}", ephemeral=True)

        # 2. Pick Side
        pick = pick.lower()
        user_choice_name = "Heads"
        if pick in ["t", "tail", "tails"]:
            user_choice_name = "Tails"
        elif pick not in ["h", "head", "heads"]:
            return await ctx.send("Invalid choice. Type 'h' or 't'.")

        # --- 3. Custom Emojis Setup ---
        # Animated Spin Emoji
        emoji_spin = "<a:cf:1434413973759070372>"
        url_spin = "https://cdn.discordapp.com/emojis/1434413973759070372.gif?quality=lossless"
        
        # Heads Emoji
        emoji_heads = "<:heds:1470863891671027804>"
        url_heads = "https://cdn.discordapp.com/emojis/1470863891671027804.png?quality=lossless"
        
        # Tails Emoji
        emoji_tails = "<:Tails:1434414186875588639>"
        url_tails = "https://cdn.discordapp.com/emojis/1434414186875588639.png?quality=lossless"

        # 4. Spinning Animation
        embed_spin = discord.Embed(
            description=f"{emoji_spin} **{user.name}** chose **{user_choice_name}**\nBetting **{bet}** coins...",
            color=0x2b2d31
        )
        embed_spin.set_thumbnail(url=url_spin)
        msg = await ctx.send(embed=embed_spin)

        # Wait for animation
        await asyncio.sleep(2)

        # 5. Result Logic
        outcome = random.choice(["Heads", "Tails"])
        won = (user_choice_name == outcome)
        
        final_emoji = emoji_heads if outcome == "Heads" else emoji_tails
        final_image_url = url_heads if outcome == "Heads" else url_tails

        if won:
            new_bal = self.update_balance(uid, bet)
            
            embed_win = discord.Embed(
                description=f"## {final_emoji}  {outcome}\n\n**You won {bet} coins**\nBalance: {new_bal}",
                color=discord.Color.green()
            )
            embed_win.set_thumbnail(url=final_image_url)
            await msg.edit(embed=embed_win)
        
        else:
            new_bal = self.update_balance(uid, -bet)
            
            embed_lose = discord.Embed(
                description=f"## {final_emoji}  {outcome}\n\n**You lost {bet} coins**\nBalance: {new_bal}",
                color=discord.Color.red()
            )
            embed_lose.set_thumbnail(url=final_image_url)
            await msg.edit(embed=embed_lose)

async def setup(bot):
    await bot.add_cog(Gambling(bot))
          
