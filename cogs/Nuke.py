import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from utils import get_theme_color

class NukeSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="nuke",
        description="💥 Delete and recreate the current channel to clear all messages"
    )
    @commands.has_permissions(administrator=True) # নিরাপত্তার জন্য শুধু অ্যাডমিনদের জন্য
    async def nuke(self, ctx: commands.Context):
        # সতর্কতা মেসেজ পাঠানো
        embed = discord.Embed(
            description="⚠️ **Are you sure?** This will delete every message in this channel forever.",
            color=discord.Color.orange()
        )
        msg = await ctx.send(embed=embed)
        
        # ৫ সেকেন্ড সময় দিবে ভাবার জন্য
        await asyncio.sleep(5)

        # চ্যানেলের তথ্য কপি করা
        channel_info = {
            "name": ctx.channel.name,
            "category": ctx.channel.category,
            "position": ctx.channel.position,
            "overwrites": ctx.channel.overwrites,
            "topic": ctx.channel.topic,
            "slowmode": ctx.channel.slowmode_delay,
            "nsfw": ctx.channel.is_nsfw()
        }

        # চ্যানেল ডিলিট করা
        await ctx.channel.delete(reason=f"Nuked by {ctx.author}")

        # নতুন চ্যানেল তৈরি করা
        new_channel = await ctx.guild.create_text_channel(
            name=channel_info["name"],
            category=channel_info["category"],
            position=channel_info["position"],
            overwrites=channel_info["overwrites"],
            topic=channel_info["topic"],
            slowmode_delay=channel_info["slowmode"],
            nsfw=channel_info["nsfw"]
        )

        # নতুন চ্যানেলে স্টাইলিশ এম্বেড পাঠানো
        nuke_embed = discord.Embed(
            title="💥 CHANNEL NUKED 💥",
            description=f"This channel has been successfully recreated by **{ctx.author.name}**.",
            color=get_theme_color(ctx.guild.id) # আপনার utils থেকে থিম কালার নিবে
        )
        # একটি নিউক্লিয়ার এক্সপ্লোশন GIF
        nuke_embed.set_image(url="https://media.tenor.com/gi9_7pS9_XIAAAAM/explosion-boom.gif")
        nuke_embed.set_footer(text="Wow Bot Security • All messages cleared")

        await new_channel.send(embed=nuke_embed)

    # পারমিশন এরর হ্যান্ডলিং
    @nuke.error
    async def nuke_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Only **Administrators** can use the Nuke command!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(NukeSystem(bot))
  
