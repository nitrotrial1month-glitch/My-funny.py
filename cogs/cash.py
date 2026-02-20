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
        
        # ২. ডাটাবেস থেকে ব্যালেন্স সংগ্রহ করা (Synced with inventory collection)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        
        # ব্যালেন্স না থাকলে ডিফল্ট ০
        balance = user_data.get("balance", 0) 
        
        # ৩. স্টাইলিশ এম্বেড তৈরি করা
        theme_color = get_theme_color(ctx.guild.id)
        embed = discord.Embed(
            color=theme_color
        )
        
        # OwO স্টাইলে ক্লিন এবং বড় করে ব্যালেন্স দেখানো
        embed.description = f"💰 **Total Balance:** `{balance:,}` coins"
        
        # এম্বেডটি ছোট এবং সুন্দর রাখার জন্য শুধু ফুটার ব্যবহার করা হয়েছে
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(EconomySystem(bot))
  
