import discord
from discord.ext import commands
import random
import asyncio
from database import Database
from utils import get_theme_color

class SlotSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emojis = ["🍎", "🍒", "🍇", "🍊", "🍋", "💎", "🔔", "7️⃣"]
        self.spin_emoji = "<a:slot:1470669361155932230>"
        self.cash_emoji = "<:Nova:1453460518764548186>"

    @commands.hybrid_command(name="slots", aliases=["s", "slot"], description="🎰 Spin the slot machine!")
    @commands.cooldown(1, 10, commands.BucketType.user) # ১০ সেকেন্ড কুলডাউন
    async def slots(self, ctx: commands.Context, amount: str):
        user = ctx.author
        uid = str(user.id)
        
        # ডাটাবেস থেকে ব্যালেন্স নেওয়া
        current_bal = Database.get_balance(uid)

        # অ্যামাউন্ট লজিক
        if amount.lower() in ["all", "max"]: 
            bet = current_bal
        elif amount.lower() == "half": 
            bet = int(current_bal / 2)
        else:
            try: 
                bet = int(amount)
            except ValueError: 
                ctx.command.reset_cooldown(ctx) # ভুল ইনপুট দিলে কুলডাউন রিসেট হবে
                return await ctx.send(f"❌ **{user.display_name}**, valid amount দিন!")

        # ভ্যালিডেশন
        if bet <= 0: 
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("❌ আপনি ০ বাজি ধরতে পারবেন না!")
        if bet > current_bal: 
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"❌ পর্যাপ্ত ব্যালেন্স নেই! ব্যালেন্স: {self.cash_emoji} `{current_bal:,}`")

        # অ্যানিমেশন ও রেজাল্ট জেনারেট
        res = [random.choice(self.emojis) for _ in range(3)]
        theme_color = get_theme_color(ctx.guild.id)
        
        def make_embed(reels, status="Spinning..."):
            embed = discord.Embed(color=theme_color)
            embed.set_author(name="🎰  S L O T S  🎰")
            embed.description = (
                f"**`╭─────────────╮`**\n"
                f"**`│`** {reels[0]} **`│`** {reels[1]} **`│`** {reels[2]} **`│`**\n"
                f"**`╰─────────────╯`**\n"
                f"**{user.display_name}** bet {self.cash_emoji} **{bet:,}**...\n\n"
                f"`{status}`"
            )
            return embed

        msg = await ctx.send(embed=make_embed([self.spin_emoji, self.spin_emoji, self.spin_emoji]))
        await asyncio.sleep(1.2)
        await msg.edit(embed=make_embed([res[0], self.spin_emoji, self.spin_emoji]))
        await asyncio.sleep(0.8)
        await msg.edit(embed=make_embed([res[0], res[1], self.spin_emoji]))
        await asyncio.sleep(0.8)

        # জেতার লজিক
        if res[0] == res[1] == res[2]:
            multiplier = 5
            status_msg = f"and won {self.cash_emoji} **{int(bet*multiplier):,}** (x{multiplier}) 🎉"
            final_color = discord.Color.green()
        elif res[0] == res[1] or res[1] == res[2] or res[0] == res[2]:
            multiplier = 2
            status_msg = f"and won {self.cash_emoji} **{int(bet*multiplier):,}** (x{multiplier}) 🎊"
            final_color = discord.Color.green()
        else:
            multiplier = 0
            status_msg = "and lost it all... 💀"
            final_color = discord.Color.red()

        # ডাটাবেস আপডেট (সিঙ্কড ফাংশন দিয়ে)
        net_change = (bet * multiplier) - bet
        new_bal = Database.update_balance(uid, net_change)

        final_embed = discord.Embed(color=final_color)
        final_embed.set_author(name="🎰  S L O T S  🎰")
        final_embed.description = (
            f"**`╭─────────────╮`**\n"
            f"**`│`** {res[0]} **`│`** {res[1]} **`│`** {res[2]} **`│`**\n"
            f"**`╰─────────────╯`**\n"
            f"**{user.display_name}** bet {self.cash_emoji} **{bet:,}** {status_msg}"
        )
        final_embed.set_footer(text=f"New Balance: {new_bal:,} • Global Economy")
        await msg.edit(embed=final_embed)

    # স্লট কুলডাউন এরর হ্যান্ডেলার
    @slots.error
    async def slots_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ **{ctx.author.display_name}**, please wait `{error.retry_after:.1f}s` before spinning again!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SlotSystem(bot))
    
