import discord
from discord.ext import commands
import random
import asyncio
from database import Database
from utils import get_theme_color, check_premium

class SlotSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # স্লট মেশিনের ফল হিসেবে এই ইমোজিগুলো আসবে
        self.emojis = ["🍎", "🍒", "🍇", "🍊", "🍋", "💎", "🔔", "7️⃣"]
        # আপনার দেওয়া অ্যানিমেটেড স্পিনিং ইমোজি
        self.spinning_emoji = "<a:slot:1470669361155932230>"

    # ---------------- 🏹 Database Helpers ---------------- #
    
    def get_balance(self, user_id):
        """ডাটাবেস থেকে ইউজার ব্যালেন্স চেক করে"""
        col = Database.get_collection("inventory")
        data = col.find_one({"_id": str(user_id)}) or {}
        return data.get("balance", 0)

    def update_balance(self, user_id, amount):
        """ডাটাবেসে ইউজার ব্যালেন্স আপডেট করে"""
        col = Database.get_collection("inventory")
        col.update_one(
            {"_id": str(user_id)},
            {"$inc": {"balance": amount}},
            upsert=True
        )

    # ---------------- 🎰 Slot Command ---------------- #

    @commands.hybrid_command(name="slots", aliases=["s", "slot"], description="🎰 Bet coins in the slot machine")
    async def slots(self, ctx: commands.Context, amount: str):
        user = ctx.author
        uid = str(user.id)
        current_bal = self.get_balance(uid)

        # ১. প্রিমিয়াম চেক এবং বেটিং লিমিট সেট করা
        is_premium = check_premium(user.id)
        MAX_BET = 500000 if is_premium else 250000

        # ২. বেটিং অ্যামাউন্ট নির্ধারণ
        if amount.lower() in ["all", "max"]:
            bet = min(current_bal, MAX_BET)
        elif amount.lower() == "half":
            bet = min(int(current_bal / 2), MAX_BET)
        else:
            try:
                bet = int(amount)
            except ValueError:
                return await ctx.send(f"❌ **{user.display_name}**, please provide a valid number!")

        # ৩. ভ্যালিডেশন চেক
        if bet <= 0:
            return await ctx.send(f"❌ **{user.display_name}**, you can't bet nothing!")
        if bet > current_bal:
            return await ctx.send(f"❌ **{user.display_name}**, you don't have enough coins! Balance: `{current_bal:,}`")
        if bet > MAX_BET:
            return await ctx.send(f"❌ **{user.display_name}**, max bet limit is `{MAX_BET:,}`!")

        # ৪. স্পিনিং অ্যানিমেশন এম্বেড (OwO স্টাইল)
        theme_color = get_theme_color(ctx.guild.id)
        initial_embed = discord.Embed(color=theme_color)
        initial_embed.set_author(name="🎰 SLOTS 🎰")
        initial_embed.description = (
            f"_SLOTS_\n"
            f"║ {self.spinning_emoji} {self.spinning_emoji} {self.spinning_emoji} ║\n"
            f"**{user.display_name}** bet 💵 **{bet:,}**..."
        )
        msg = await ctx.send(embed=initial_embed)

        # অ্যানিমেশনের জন্য ২ সেকেন্ড অপেক্ষা
        await asyncio.sleep(2)
        
        # ৫. ফলাফল নির্ধারণ
        res = [random.choice(self.emojis) for _ in range(3)]
        
        # মাল্টিপ্লায়ার লজিক (OwO-এর মতো)
        if res[0] == res[1] == res[2]:
            # তিনটিই এক হলে Jackpot!
            multiplier = 10 if res[0] == "7️⃣" else 5
        elif res[0] == res[1] or res[1] == res[2] or res[0] == res[2]:
            # যেকোনো দুটি এক হলে
            multiplier = 2
        else:
            # কোনোটিই না মিললে
            multiplier = 0

        # জেতা/হারার হিসাব
        winnings = int(bet * multiplier)
        net_change = winnings - bet
        self.update_balance(uid, net_change)
        new_bal = self.get_balance(uid)

        # ৬. ফাইনাল এম্বেড তৈরি (হুবহু OwO স্টাইল)
        final_embed = discord.Embed()
        final_embed.set_author(name="🎰 SLOTS 🎰")
        
        result_line = f"║ {res[0]} {res[1]} {res[2]} ║"
        
        if multiplier > 0:
            # জিতলে সবুজ রঙ এবং জেতার মেসেজ
            final_embed.color = discord.Color.green()
            win_line = f"and won 💵 **{winnings:,}** (x{multiplier}) 🎉"
        else:
            # হারলে লাল রঙ এবং হারার মেসেজ
            final_embed.color = discord.Color.red()
            win_line = f"and lost 💵 **{bet:,}**"

        # OwO-এর মতো হুবহু ডেসক্রিপশন ফরম্যাট
        final_embed.description = (
            f"_SLOTS_\n"
            f"{result_line}\n"
            f"**{user.display_name}** bet 💵 **{bet:,}** {win_line}"
        )
        
        # OwO-এর মতো ফুটার ফরম্যাট
        final_embed.set_footer(text=f"New Balance: {new_bal:,} • Global Economy")
        
        # মেসেজটি এডিট করে ফাইনাল রেজাল্ট দেখানো
        await msg.edit(embed=final_embed)

async def setup(bot):
    await bot.add_cog(SlotSystem(bot))
      
