import discord
from discord.ext import commands
import random
import asyncio
from database import Database # Uses your MongoDB Database class

class Slots(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Your specific emojis
        self.cash_emoji = "<:Nova:1453460518764548186>"
        self.spin_emoji = "<a:slot:1470669361155932230>"
        self.symbols = ["🍒", "🍇", "🍋", "🍊", "🍎", "💎", "⭐"]

    @commands.hybrid_command(name="slot", aliases=["s", "sl"], description="Play the slots!")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def slots(self, ctx, amount: str):
        # Isolate balance to the command user
        user_id = str(ctx.author.id)
        balance = Database.get_balance(user_id)

        # Bet Calculation
        if amount.lower() == "all":
            bet = min(balance, 100000)
        else:
            try:
                bet = int(amount.replace('k', '000').replace(',', ''))
            except ValueError:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send(f"❌ **{ctx.author.display_name}**, usage: `!sl 100`", ephemeral=True)

        if bet <= 0:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("❌ You must bet more than 0!", ephemeral=True)
            
        if bet > balance:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"❌ You don't have enough balance! (Balance: {balance:,})", ephemeral=True)

        # Deduct bet from MongoDB
        Database.update_balance(user_id, -bet)

        # Generate result (35% Win Chance)
        if random.random() < 0.35: 
            winning_item = random.choice(self.symbols)
            final_result = [winning_item, winning_item, winning_item]
            is_win = True
        else:
            final_result = [random.choice(self.symbols) for _ in range(3)]
            # Ensure no accidental wins during a loss
            if final_result[0] == final_result[1] == final_result[2]:
                final_result[2] = random.choice([i for i in self.symbols if i != final_result[0]])
            is_win = False

        # --- Initial Message (Spinning Phase) ---
        current_slots = [self.spin_emoji, self.spin_emoji, self.spin_emoji]
        
        embed = discord.Embed(color=0x5865F2)
        embed.description = (
            f"**___ SLOTS ___**\n"
            f"║ {' '.join(current_slots)} ║\n"
            f"╚═══════╝  **{ctx.author.display_name}** bet {self.cash_emoji} **{bet:,}**\n\n"
            f"**Spinning...**"
        )
        msg = await ctx.send(embed=embed)

        # --- Sequential Reveal (1s delay per slot) ---
        for i in range(3):
            await asyncio.sleep(1) #
            current_slots[i] = final_result[i]
            
            embed.description = (
                f"**___ SLOTS ___**\n"
                f"║ {' '.join(current_slots)} ║\n"
                f"╚═══════╝  **{ctx.author.display_name}** bet {self.cash_emoji} **{bet:,}**\n\n"
                f"**Revealing...**"
            )
            await msg.edit(embed=embed)

        # --- Final Logic ---
        if is_win:
            # Multipliers based on items
            mult = {"⭐": 6, "💎": 4, "🍎": 3}.get(final_result[0], 2)
            winnings = bet * mult
            new_bal = Database.update_balance(user_id, winnings)
            
            status = f"and won {self.cash_emoji} **{winnings:,}** (x{mult}) 🎉"
            embed.color = 0x2ecc71
        else:
            new_bal = Database.get_balance(user_id)
            status = "and won nothing... :c"
            embed.color = 0xe74c3c

        embed.description = (
            f"**___ SLOTS ___**\n"
            f"║ {' '.join(final_result)} ║\n"
            f"╚═══════╝  **{ctx.author.display_name}** bet {self.cash_emoji} **{bet:,}**\n\n"
            f"{status}"
        )
        embed.set_footer(text=f"Balance for {ctx.author.name}: {new_bal:,} • Economy System")
        await msg.edit(embed=embed)

    @slots.error
    async def slots_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏱ | **{ctx.author.display_name}**! Try again in **{error.retry_after:.1f}s**", delete_after=5)

async def setup(bot):
    await bot.add_cog(Slots(bot))
    
