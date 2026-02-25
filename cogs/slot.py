import discord
from discord.ext import commands
import random
import asyncio
from database import Database
from utils import get_theme_color

class SlotSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # স্লটের ইমোজি সেট
        self.emojis = ["🍎", "🍒", "🍇", "🍊", "🍋", "💎", "🔔", "7️⃣"]
        # আপনার দেওয়া অ্যানিমেটেড স্পিন ইমোজি
        self.spin_emoji = "<a:slot:1470669361155932230>"

    @commands.hybrid_command(name="slots", aliases=["s", "slot"], description="🎰 Bet coins in the slot machine")
    async def slots(self, ctx: commands.Context, amount: str):
        user = ctx.author
        uid = str(user.id)
        
        # ১. ডাটাবেস থেকে ব্যালেন্স নেওয়া (আপনার database.py এর ফাংশন ব্যবহার করে)
        current_bal = Database.get_balance(uid)

        # ২. অ্যামাউন্ট লজিক
        if amount.lower() in ["all", "max"]:
            bet = current_bal
        elif amount.lower() == "half":
            bet = int(current_bal / 2)
        else:
            try:
                bet = int(amount)
            except ValueError:
                return await ctx.send(f"❌ **{user.display_name}**, valid amount দিন!")

        # ৩. ভ্যালিডেশন
        if bet <= 0: return await ctx.send("❌ You can't bet 0!")
        if bet > current_bal: 
            return await ctx.send(f"❌ আপনার পর্যাপ্ত কয়েন নেই! ব্যালেন্স: `{current_bal:,}`")

        # ৪. রেজাল্ট জেনারেট করা
        res = [random.choice(self.emojis) for _ in range(3)]
        
        # ৫. প্রফেশনাল অ্যানিমেশন এম্বেড (One-by-one reveal)
        theme_color = get_theme_color(ctx.guild.id)
        
        def make_embed(reels, status="Spinning..."):
            embed = discord.Embed(color=theme_color)
            embed.set_author(name="🎰  S L O T S  🎰")
            # স্ক্রিনশটের মত সুন্দর ডিজাইন
            embed.description = (
                f"**`╭─────────────╮`**\n"
                f"**`│`** {reels[0]} **`│`** {reels[1]} **`│`** {reels[2]} **`│`**\n"
                f"**`╰─────────────╯`**\n"
                f"**{user.display_name}** bet 💵 **{bet:,}**...\n\n"
                f"`{status}`"
            )
            return embed

        # অ্যানিমেশন স্টেজ শুরু
        # স্টেজ ১: সব স্পিন করছে
        msg = await ctx.send(embed=make_embed([self.spin_emoji, self.spin_emoji, self.spin_emoji]))
        await asyncio.sleep(1.2)

        # স্টেজ ২: প্রথম ইমোজি স্থির
        await msg.edit(embed=make_embed([res[0], self.spin_emoji, self.spin_emoji]))
        await asyncio.sleep(0.8)

        # স্টেজ ৩: দ্বিতীয় ইমোজি স্থির
        await msg.edit(embed=make_embed([res[0], res[1], self.spin_emoji]))
        await asyncio.sleep(0.8)

        # ৬. জেতার লজিক ও মাল্টিপ্লায়ার
        if res[0] == res[1] == res[2]:
            multiplier = 5 # ৩টি মিললে ৫ গুণ
            status_msg = f"and won 💵 **{int(bet*multiplier):,}** (x{multiplier}) 🎉"
            final_color = discord.Color.green()
        elif res[0] == res[1] or res[1] == res[2] or res[0] == res[2]:
            multiplier = 2 # ২টিতে ২ গুণ
            status_msg = f"and won 💵 **{int(bet*multiplier):,}** (x{multiplier}) 🎊"
            final_color = discord.Color.green()
        else:
            multiplier = 0
            status_msg = "and lost it all... 💀"
            final_color = discord.Color.red()

        # ৭. ডাটাবেস আপডেট (Database.update_balance ব্যবহার করে)
        net_change = (bet * multiplier) - bet
        new_bal = Database.update_balance(uid, net_change)

        # ৮. ফাইনাল রেজাল্ট এম্বেড (OwO স্টাইল ফুটারসহ)
        final_embed = discord.Embed(color=final_color)
        final_embed.set_author(name="🎰  S L O T S  🎰")
        final_embed.description = (
            f"**`╭─────────────╮`**\n"
            f"**`│`** {res[0]} **`│`** {res[1]} **`│`** {res[2]} **`│`**\n"
            f"**`╰─────────────╯`**\n"
            f"**{user.display_name}** bet 💵 **{bet:,}** {status_msg}"
        )
        final_embed.set_footer(text=f"New Balance: {new_bal:,} • Global Economy")
        
        await msg.edit(embed=final_embed)

async def setup(bot):
    await bot.add_cog(SlotSystem(bot))

