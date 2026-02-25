import discord
from discord.ext import commands
import random
import asyncio
import database # আপনার তৈরিকৃত database.py

class Slots(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cash_emoji = "<:Nova:1453460518764548186>"
        self.spin_emoji = "<a:slot:1470669361155932230>" # আপনার এনিমেটেড ইমোজি
        self.symbols = ["💎", "🍎", "🍋", "🍇", "🍒", "⭐"]

    @commands.hybrid_command(name="slot", aliases=["s", "sl"], description="Play a premium slot machine!")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def slot(self, ctx, amount: str):
        user_id = str(ctx.author.id)
        balance = database.get_balance(user_id)

        # বাজি ক্যালকুলেশন
        if amount.lower() == "all":
            bet = min(balance, 50000)
        else:
            try:
                bet = int(amount.replace('k', '000').replace(',', ''))
            except:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("❌ সঠিক অ্যামাউন্ট দিন! (যেমন: `!sl 500`)", ephemeral=True)

        if bet <= 0 or bet > balance:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"❌ আপনার ব্যালেন্স নেই! (ব্যালেন্স: {balance:,})", ephemeral=True)

        # বাজি কেটে নেওয়া
        database.update_balance(user_id, -bet)

        # রেজাল্ট জেনারেট (৩x৩ গ্রিড)
        # মাঝখানের সারি (Row 2) হলো জেতার মেইন লাইন
        if random.random() < 0.30: # ৩০% জেতার সম্ভাবনা
            win_sym = random.choice(self.symbols)
            mid_row = [win_sym, win_sym, win_sym]
        else:
            mid_row = [random.choice(self.symbols) for _ in range(3)]
            if mid_row[0] == mid_row[1] == mid_row[2]: # ভুল করে উইন হলে রেন্ডম করা
                mid_row[2] = random.choice([s for s in self.symbols if s != mid_row[0]])

        # পুরো গ্রিড তৈরি
        full_grid = [
            [random.choice(self.symbols) for _ in range(3)], # Row 1
            mid_row,                                        # Row 2 (Winning Row)
            [random.choice(self.symbols) for _ in range(3)]  # Row 3
        ]

        # প্রাথমিক এমবেড (Spinning Phase)
        embed = discord.Embed(title="🎰 SLOT MACHINE 🎰", color=0x5865F2)
        embed.description = (
            f"**{ctx.author.display_name}** bet {self.cash_emoji} **{bet:,}**\n\n"
            f"┏━━━┳━━━┳━━━┓\n"
            f"┃ {self.spin_emoji} ┃ {self.spin_emoji} ┃ {self.spin_emoji} ┃\n"
            f"┃ {self.spin_emoji} ┃ {self.spin_emoji} ┃ {self.spin_emoji} ┃ ◀\n"
            f"┃ {self.spin_emoji} ┃ {self.spin_emoji} ┃ {self.spin_emoji} ┃\n"
            f"┗━━━┻━━━┻━━━┛\n\n"
            "**Spinning...**"
        )
        msg = await ctx.send(embed=embed)

        # এনিমেশন ইফেক্ট (Sequential reveal)
        await asyncio.sleep(2)
        
        # ফলাফল ক্যালকুলেশন
        is_win = mid_row[0] == mid_row[1] == mid_row[2]
        if is_win:
            mult = {"💎": 10, "⭐": 7, "🍎": 5}.get(mid_row[0], 3)
            winnings = bet * mult
            new_bal = database.update_balance(user_id, winnings)
            status = f"Winner! You won {self.cash_emoji} **{winnings:,}** 🎉"
            embed.color = 0x2ecc71 # Green for win
        else:
            new_bal = database.get_balance(user_id)
            status = "You lost it all... 💀"
            embed.color = 0xe74c3c # Red for loss

        # ফাইনাল গ্রিড ডিসপ্লে
        final_desc = (
            f"**{ctx.author.display_name}** bet {self.cash_emoji} **{bet:,}**\n\n"
            f"┏━━━┳━━━┳━━━┓\n"
            f"┃ {full_grid[0][0]} ┃ {full_grid[0][1]} ┃ {full_grid[0][2]} ┃\n"
            f"┃ {full_grid[1][0]} ┃ {full_grid[1][1]} ┃ {full_grid[1][2]} ┃ ◀\n"
            f"┃ {full_grid[2][0]} ┃ {full_grid[2][1]} ┃ {full_grid[2][2]} ┃\n"
            f"┗━━━┻━━━┻━━━┛\n\n"
            f"**{status}**"
        )
        
        embed.description = final_desc
        embed.set_footer(text=f"Balance: {new_bal:,} • Economy System")
        await msg.edit(embed=embed)

    @slot.error
    async def slot_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏱ | **{ctx.author.display_name}**, শান্ত হও! আবার চেষ্টা করো **{error.retry_after:.1f}s** পর।", delete_after=5)

async def setup(bot):
    await bot.add_cog(Slots(bot))
    
