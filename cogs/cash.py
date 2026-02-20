import discord
from discord.ext import commands
from database import Database
from utils import get_theme_color

class EconomySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="balance", aliases=["bal", "cash"], description="💰 Check your total coins")
    async def balance(self, ctx: commands.Context):
        # ১. কমান্ড প্রদানকারীর আইডি নেওয়া
        uid = str(ctx.author.id)
        
        # ২. 'inventory' কালেকশন থেকে ডাটা নেওয়া (Daily কমান্ডের সাথে মিল রেখে)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        
        # ৩. ব্যালেন্স সংগ্রহ করা (যেটি Database.update_balance আপডেট করে)
        balance = user_data.get("balance", 0) 
        
        # ৪. স্টাইলিশ এম্বেড ডিজাইন
        theme_color = get_theme_color(ctx.guild.id)
        embed = discord.Embed(
            color=theme_color
        )
        
        # OwO স্টাইলে বড় এবং স্পষ্টভাবে ব্যালেন্স প্রদর্শন
        embed.description = f"💰 **Total Balance:** `{balance:,}` coins"
        
        # ইউজার মেনশন না করে শুধু তার নাম ও ছবি ফুটারে দেখানো
        embed.set_footer(
            text=f"Requested by {ctx.author.name}", 
            icon_url=ctx.author.display_avatar.url
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(EconomySystem(bot))
    
