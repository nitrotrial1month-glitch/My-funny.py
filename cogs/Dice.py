import discord
from discord.ext import commands
import random
import asyncio
from database import Database
from utils import get_theme_color

class DiceSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dice_results = {1: 0, 2: 1, 3: 1.5, 4: 2, 5: 3, 6: 5}
        self.numbers = list(self.dice_results.keys())
        self.weights = [35, 30, 18, 10, 5, 2] # Balanced probability
        self.dice_faces = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
        self.rolling_emoji = "<a:emoji_108:1439795917451431966>"
        self.cash_emoji = "<:Nova:1453460518764548186>"

    @commands.hybrid_command(name="dice", aliases=["roll"], description="Roll the dice and win rewards!")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def dice(self, ctx: commands.Context, amount: str):
        user = ctx.author
        uid = str(user.id)
        current_bal = Database.get_balance(uid)

        if amount.lower() in ["all", "max"]: bet = current_bal
        elif amount.lower() == "half": bet = int(current_bal / 2)
        else:
            try: bet = int(amount)
            except ValueError: 
                ctx.command.reset_cooldown(ctx)
                return await ctx.send(f"❌ **{user.display_name}**, please provide a valid amount!")

        if bet <= 0: 
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("❌ You cannot bet 0 coins!")
        if bet > current_bal: 
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"❌ Insufficient balance! Your balance: {self.cash_emoji} `{current_bal:,}`")

        theme_color = get_theme_color(ctx.guild.id)
        embed = discord.Embed(color=theme_color)
        embed.set_author(name="🎲  D I C E  R O L L  🎲")
        embed.description = (
            f"**`╭─────────────╮`**\n"
            f"**`│      `** {self.rolling_emoji} **`      │`**\n"
            f"**`╰─────────────╯`**\n"
            f"**{user.display_name}** bet {self.cash_emoji} **{bet:,}**\n\n"
            f"`The dice is rolling...`"
        )
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(2) 

        roll_result = random.choices(self.numbers, weights=self.weights, k=1)[0]
        multiplier = self.dice_results[roll_result]
        
        if multiplier > 0:
            winnings = int(bet * multiplier)
            net_change = winnings - bet
            status_msg = f"and you won {self.cash_emoji} **{winnings:,}**! (x{multiplier}) 🎉"
            final_color = discord.Color.green()
        else:
            net_change = -bet
            status_msg = f"It's a 1! You lost {self.cash_emoji} **{bet:,}**. 💀"
            final_color = discord.Color.red()

        new_bal = Database.update_balance(uid, net_change)
        final_embed = discord.Embed(color=final_color)
        final_embed.set_author(name="🎲  D I C E  R O L L  🎲")
        final_embed.description = (
            f"**`╭─────────────╮`**\n"
            f"**`│      `** {self.dice_faces[roll_result]} **`      │`**\n"
            f"**`╰─────────────╯`**\n"
            f"The dice rolled `{roll_result}`\n"
            f"**{user.display_name}** bet {self.cash_emoji} **{bet:,}** {status_msg}"
        )
        final_embed.set_footer(text=f"New Balance: {new_bal:,} • Global Economy")
        await msg.edit(embed=final_embed)

    @dice.error
    async def dice_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ **{ctx.author.display_name}**, please wait `{error.retry_after:.1f}s`!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(DiceSystem(bot))
    
