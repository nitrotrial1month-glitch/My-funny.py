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

    def get_balance(self, user_id):
        col = Database.get_collection("inventory")
        data = col.find_one({"_id": str(user_id)}) or {}
        return data.get("balance", 0)

    def update_balance(self, user_id, amount):
        col = Database.get_collection("inventory")
        col.update_one({"_id": str(user_id)}, {"$inc": {"balance": amount}}, upsert=True)

    @commands.hybrid_command(name="slots", aliases=["s", "slot"])
    async def slots(self, ctx: commands.Context, amount: str):
        user = ctx.author
        uid = str(user.id)
        current_bal = self.get_balance(uid)

        # অ্যামাউন্ট নির্ধারণ
        if amount.lower() in ["all", "max"]: bet = current_bal
        elif amount.lower() == "half": bet = int(current_bal / 2)
        else:
            try: bet = int(amount)
            except ValueError: return await ctx.send(f"❌ **{user.display_name}**, invalid amount!")

        if bet <= 0: return await ctx.send("❌ You can't bet 0!")
        if bet > current_bal: return await ctx.send(f"❌ Insufficient balance! `{current_bal:,}`")

        theme_color = get_theme_color(ctx.guild.id)
        
        # অ্যানিমেশন স্টেজ
        embed = discord.Embed(color=theme_color)
        embed.set_author(name="🎰 SLOTS 🎰")
        embed.description = f"_SLOTS_\n║ {self.spin_emoji} {self.spin_emoji} {self.spin_emoji} ║\n**{user.display_name}** bet 💵 **{bet:,}**...\n\n`Spinning...`"
        msg = await ctx.send(embed=embed)

        await asyncio.sleep(1.2)
        res = [random.choice(self.emojis) for _ in range(3)]
        
        # ধাপে ধাপে প্রকাশ
        stages = [
            f"║ {res[0]} {self.spin_emoji} {self.spin_emoji} ║",
            f"║ {res[0]} {res[1]} {self.spin_emoji} ║"
        ]
        for stage in stages:
            embed.description = f"_SLOTS_\n{stage}\n**{user.display_name}** bet 💵 **{bet:,}**...\n\n`Spinning...`"
            await msg.edit(embed=embed)
            await asyncio.sleep(0.8)

        # ফলাফল নির্ধারণ
        if res[0] == res[1] == res[2]:
            multiplier = 5
            win_text = f"and won 💵 **{int(bet*multiplier):,}** (x{multiplier}) 🎉"
            final_color = discord.Color.green()
        elif res[0] == res[1] or res[1] == res[2] or res[0] == res[2]:
            multiplier = 2
            win_text = f"and won 💵 **{int(bet*multiplier):,}** (x{multiplier}) 🎊"
            final_color = discord.Color.green()
        else:
            multiplier = 0
            win_text = f"and lost it all... 💀"
            final_color = discord.Color.red()

        # আপডেট
        self.update_balance(uid, (bet * multiplier) - bet)
        new_bal = self.get_balance(uid)

        final_embed = discord.Embed(color=final_color)
        final_embed.set_author(name="🎰 SLOTS 🎰")
        final_embed.description = f"_SLOTS_\n║ {res[0]} {res[1]} {res[2]} ║\n**{user.display_name}** bet 💵 **{bet:,}** {win_text}"
        final_embed.set_footer(text=f"New Balance: {new_bal:,} • Global Economy")
        await msg.edit(embed=final_embed)

async def setup(bot):
    await bot.add_cog(SlotSystem(bot))
    
