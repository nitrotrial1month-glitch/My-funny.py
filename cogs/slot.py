import discord
from discord.ext import commands
import random
import asyncio
from database import Database # আপনার MongoDB Database ক্লাস ইমপোর্ট করা হলো

class Slots(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cash_emoji = "<:Nova:1453460518764548186>"
        self.spin_emoji = "<a:slot:1470669361155932230>"
        self.symbols = ["💎", "🍎", "🍋", "🍇", "🍒", "⭐"]

    @commands.hybrid_command(name="slot", aliases=["s", "sl"], description="Play a high-quality MongoDB slots!")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def slot(self, ctx, amount: str):
        user_id = str(ctx.author.id)
        
        # 👇 MongoDB থেকে ব্যালেন্স নেওয়া
        balance = Database.get_balance(user_id)

        # বাজি ক্যালকুলেশন
        if amount.lower() == "all":
            bet = min(balance, 50000)
        else:
            try:
                bet = int(amount.replace('k', '000').replace(',', ''))
            except:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("❌ Enter the correct amount! (Example: `!sl 500`)", ephemeral=True)

        if bet <= 0 or bet > balance:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"❌ You do not have enough balance! (Balance: {balance:,})", ephemeral=True)

        # 👇 MongoDB থেকে টাকা কেটে নেওয়া
        Database.update_balance(user_id, -bet)

        # রেজাল্ট জেনারেট (৩x৩ গ্রিড)
        if random.random() < 0.35: # ৩৫% জয়ের সম্ভাবনা
            win_sym = random.choice(self.symbols)
            mid_row = [win_sym, win_sym, win_sym]
        else:
            mid_row = [random.choice(self.symbols) for _ in range(3)]
            if mid_row[0] == mid_row[1] == mid_row[2]:
                mid_row[2] = random.choice([s for s in self.symbols if s != mid_row[0]])

        full_grid = [
            [random.choice(self.symbols) for _ in range(3)],
            mid_row,
            [random.choice(self.symbols) for _ in range(3)]
        ]

        # এমবেড এবং অ্যানিমেশন
        embed = discord.Embed(title="🎰 MONGODB SLOTS 🎰", color=0x5865F2)
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

        await asyncio.sleep(2) # ২ সেকেন্ড স্পিন হবে
        
        # ফলাফল ক্যালকুলেশন
        is_win = mid_row[0] == mid_row[1] == mid_row[2]
        if is_win:
            mult = {"💎": 10, "⭐": 7, "🍎": 5}.get(mid_row[0], 3)
            winnings = bet * mult
            # 👇 MongoDB-তে উইনিং অ্যামাউন্ট যোগ করা
            new_bal = Database.update_balance(user_id, winnings)
            status = f"Winner! You won {self.cash_emoji} **{winnings:,}** 🎉"
            embed.color = 0x2ecc71
        else:
            new_bal = Database.get_balance(user_id)
            status = "You lost it all... 💀"
            embed.color = 0xe74c3c

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
        embed.set_footer(text=f"Balance: {new_bal:,} • Cloud Database")
        await msg.edit(embed=embed)

    @slot.error
    async def slot_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏱ | **{ctx.author.display_name}**, শান্ত হও! **{error.retry_after:.1f}s** পর চেষ্টা করো।", delete_after=5)

async def setup(bot):
    await bot.add_cog(Slots(bot))
        
