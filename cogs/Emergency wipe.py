import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from utils import get_theme_color

class EmergencyWipe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="server_wipe",
        description="🚨 EMERGENCY: Delete all channels and reset the server (Owner Only)"
    )
    async def server_wipe(self, ctx: commands.Context):
        # সর্বোচ্চ নিরাপত্তা: শুধুমাত্র সার্ভার মালিক এটি রান করতে পারবেন
        if ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("❌ **Security Alert:** Only the Server Owner can use this emergency command!", ephemeral=True)

        # কনফার্মেশন প্রম্পট
        embed = discord.Embed(
            title="⚠️ CRITICAL WARNING",
            description=(
                "You are about to **WIPE** this entire server.\n"
                "All channels, messages, and categories will be deleted forever.\n\n"
                "To confirm, type: `CONFIRM WIPE` within 15 seconds."
            ),
            color=discord.Color.dark_red()
        )
        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content == "CONFIRM WIPE"

        try:
            await self.bot.wait_for('message', check=check, timeout=15.0)
        except asyncio.TimeoutError:
            return await ctx.send("⌛ Wipe cancelled due to timeout.")

        # --- সার্ভার ক্লিনিং শুরু ---
        await ctx.send("🚀 Starting Emergency Wipe... Please wait.")
        
        # সব চ্যানেল ডিলিট করা
        for channel in ctx.guild.channels:
            try:
                await channel.delete(reason="Emergency Server Wipe")
            except:
                continue

        # একটি নতুন ইমারজেন্সি চ্যানেল তৈরি করা
        new_channel = await ctx.guild.create_text_channel(name="🚨-emergency-reset")
        
        # স্টাইলিশ রিসেট এম্বেড
        wipe_embed = discord.Embed(
            title="🛡️ SERVER WIPED & RESET",
            description="The server has been completely wiped for security reasons.",
            color=get_theme_color(ctx.guild.id), # আপনার utils থেকে থিম কালার
            timestamp=ctx.message.created_at
        )
        wipe_embed.add_field(name="Initiated By", value=f"{ctx.author.mention}", inline=False)
        wipe_embed.set_image(url="https://media.tenor.com/On7tT96Fe_kAAAAM/vampire-diaries-alaric-saltzman.gif")
        wipe_embed.set_footer(text="Wow Security System • Fresh Start")

        await new_channel.send(embed=wipe_embed)

async def setup(bot):
    await bot.add_cog(EmergencyWipe(bot))
      
