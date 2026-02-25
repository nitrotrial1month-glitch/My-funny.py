import discord
from discord.ext import commands
import random
import asyncio
from database import Database
from utils import get_theme_color

class DiceSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # ডাইসের স্ট্যাটিক ইমোজি সেট
        self.dice_emojis = {
            1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"
        }
        # আপনার দেওয়া অ্যানিমেটেড ডাইস ইমোজি
        self.rolling_emoji = "<a:emoji_108:1439795917451431966>"
        # আপনার কাস্টম ক্যাশ ইমোজি
        self.cash_emoji = "<:Nova:1453460518764548186>"

    @commands.hybrid_command(name="dice", aliases=["roll"], description="🎲 Bet coins on a dice roll!")
    @commands.cooldown(1, 10, commands.BucketType.user) # ১০ সেকেন্ড কুলডাউন
    async def dice(self, ctx: commands.Context, amount: str, guess: int):
        user = ctx.author
        uid = str(user.id)
        
        # ১. ডাটাবেস থেকে সিঙ্ক করা সঠিক ব্যালেন্স নেওয়া
        current_bal = Database.get_balance(uid)

        # ২. অ্যামাউন্ট নির্ধারণ
        if amount.lower() in ["all", "max"]:
            bet = current_bal
        elif amount.lower() == "half":
            bet = int(current_bal / 2)
        else:
            try:
                bet = int(amount)
            except ValueError:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send(f"❌ **{user.display_name}**, valid amount দিন!")

        # ৩. ভ্যালিডেশন চেক
        if guess < 1 or guess > 6:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("❌ Please choose a number between 1 and 6!")
        if bet <= 0: 
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("❌ You cannot bet 0!")
        if bet > current_bal: 
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"❌ Not enough balance! Balance: {self.cash_emoji} `{current_bal:,}`")

        # ৪. রোলিং অ্যানিমেশন এম্বেড (OwO স্টাইল)
        theme_color = get_theme_color(ctx.guild.id)
        embed = discord.Embed(color=theme_color)
        embed.set_author(name="🎲  D I C E  R O L L  🎲")
        embed.description = (
            f"**`╭─────────────╮`**\n"
            f"**`│      `** {self.rolling_emoji} **`      │`**\n"
            f"**`╰─────────────╯`**\n"
            f"**{user.display_name}** bet {self.cash_emoji} **{bet:,}** on `{guess}`\n\n"
            f"`The dice is rolling...`"
        )
        msg = await ctx.send(embed=embed)

        await asyncio.sleep(2) # অ্যানিমেশন টাইম

        # ৫. ফলাফল নির্ধারণ
        roll_result = random.randint(1, 6)
        won = (guess == roll_result)
        
        # ৬. জেতার লজিক ও ডাটাবেস আপডেট
        multiplier = 6 # ১টি সংখ্যা মিলে গেলে ৬ গুণ
        if won:
            winnings = int(bet * multiplier)
            net_change = winnings - bet
            status_msg = f"and won {self.cash_emoji} **{winnings:,}** (x{multiplier}) 🎉"
            final_color = discord.Color.green()
        else:
            net_change = -bet
            status_msg = f"and lost {self.cash_emoji} **{bet:,}**... 💀"
            final_color = discord.Color.red()

        # নতুন সিঙ্কড ফাংশন দিয়ে ডাটাবেস আপডেট
        new_bal = Database.update_balance(uid, net_change)

        # ৭. ফাইনাল রেজাল্ট এম্বেড (OwO স্টাইল ফুটারসহ)
        final_embed = discord.Embed(color=final_color)
        final_embed.set_author(name="🎲  D I C E  R O L L  🎲")
        
        dice_icon = self.dice_emojis.get(roll_result, "🎲")
        
        final_embed.description = (
            f"**`╭─────────────╮`**\n"
            f"**`│      `** {dice_icon} **`      │`**\n"
            f"**`╰─────────────╯`**\n"
            f"The dice rolled `{roll_result}`\n"
            f"**{user.display_name}** bet {self.cash_emoji} **{bet:,}** {status_msg}"
        )
        final_embed.set_footer(text=f"New Balance: {new_bal:,} • Global Economy")
        
        await msg.edit(embed=final_embed)

    # কুলডাউন এরর হ্যান্ডেলার
    @dice.error
    async def dice_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ **{ctx.author.display_name}**, please wait `{error.retry_after:.1f}s` before rolling again!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(DiceSystem(bot))
      
