import discord
from discord.ext import commands
import random
import asyncio
from database import Database
from utils import get_theme_color

class SlotSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # ইমোজি এবং তাদের উইনিং মাল্টিপ্লায়ার
        self.emoji_data = {
            "🍎": 1,   # টাকা ফেরত (সবচেয়ে বেশি হবে)
            "🍒": 2,   
            "🍇": 3,   
            "🍊": 5,   
            "🍋": 10,  
            "🔔": 20,  
            "💎": 50,  
            "7️⃣": 100  # জ্যাকপট (সবচেয়ে কঠিন)
        }
        
        # সম্ভাব্যতা সেট করা (Weights) - এটি ব্যালেন্স ঠিক রাখবে
        # 🍎 আসার চান্স সবচেয়ে বেশি রাখা হয়েছে যাতে বেশিরভাগ সময় 1x বা লস হয়
        self.emojis = list(self.emoji_data.keys())
        self.weights = [60, 15, 10, 7, 4, 2, 1.5, 0.5] 

        self.spin_emoji = "<a:slot:1470669361155932230>"
        self.cash_emoji = "<:Nova:1453460518764548186>"

    @commands.hybrid_command(name="slots", aliases=["s", "slot"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def slots(self, ctx: commands.Context, amount: str):
        user = ctx.author
        uid = str(user.id)
        current_bal = Database.get_balance(uid)

        # বাজি ধরার অ্যামাউন্ট চেক
        if amount.lower() in ["all", "max"]: bet = current_bal
        elif amount.lower() == "half": bet = int(current_bal / 2)
        else:
            try: bet = int(amount)
            except ValueError: 
                ctx.command.reset_cooldown(ctx)
                return await ctx.send(f"❌ **{user.display_name}**, Enter valid amount!")

        if bet <= 0: 
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("❌ You can't bet 0!")
        if bet > current_bal: 
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"❌ No balance! {self.cash_emoji} `{current_bal:,}`")

        # Weights অনুযায়ী র‍্যান্ডম ইমোজি সিলেক্ট করা
        res = random.choices(self.emojis, weights=self.weights, k=3)
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

        # অ্যানিমেশন (One-by-one Reveal)
        msg = await ctx.send(embed=make_embed([self.spin_emoji, self.spin_emoji, self.spin_emoji]))
        await asyncio.sleep(1.2)
        await msg.edit(embed=make_embed([res[0], self.spin_emoji, self.spin_emoji]))
        await asyncio.sleep(0.8)
        await msg.edit(embed=make_embed([res[0], res[1], self.spin_emoji]))
        await asyncio.sleep(0.8)

        # উইনিং লজিক (শুধুমাত্র ৩টি মিললে)
        if res[0] == res[1] == res[2]:
            multiplier = self.emoji_data.get(res[0], 0)
            status_msg = f"and won {self.cash_emoji} **{int(bet*multiplier):,}** (x{multiplier}) 🎉"
            final_color = discord.Color.green()
        else:
            multiplier = 0
            status_msg = "and lost it all... 💀"
            final_color = discord.Color.red()

        # ডাটাবেস আপডেট (সিঙ্কড ব্যালেন্স)
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

    @slots.error
    async def slots_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ **{ctx.author.display_name}**, please wait `{error.retry_after:.1f}s`!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SlotSystem(bot))
    
