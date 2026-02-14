import discord
from discord.ext import commands
from discord import app_commands
import datetime
from utils import get_theme_color

class ChannelControl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= 🔒 LOCK COMMAND =================
    @commands.hybrid_command(
        name="lock",
        description="🔒 Lock the current channel for everyone or a specific role"
    )
    @commands.has_permissions(manage_channels=True)
    @app_commands.describe(role="The role you want to lock (Default: @everyone)")
    async def lock(self, ctx: commands.Context, role: discord.Role = None):
        # যদি রোল মেনশন না থাকে, তবে @everyone সিলেক্ট হবে
        target_role = role or ctx.guild.default_role
        
        # পারমিশন আপডেট (মেসেজ পাঠানো বন্ধ)
        await ctx.channel.set_permissions(target_role, send_messages=False)

        # স্টাইলিশ এম্বেড ডিজাইন
        embed = discord.Embed(
            title="🔒 Channel Locked!",
            description=f"This channel has been locked for {target_role.mention}.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        embed.add_field(name="🛡️ Authorized by", value=ctx.author.mention, inline=True)
        embed.add_field(name="📍 Channel", value=ctx.channel.mention, inline=True)
        
        # লক আইকন GIF
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3064/3064197.png")
        embed.set_footer(text="Funny Bot Security System", icon_url=self.bot.user.display_avatar.url)

        await ctx.send(embed=embed)

    # ================= 🔓 UNLOCK COMMAND =================
    @commands.hybrid_command(
        name="unlock",
        description="🔓 Unlock the current channel for everyone or a specific role"
    )
    @commands.has_permissions(manage_channels=True)
    @app_commands.describe(role="The role you want to unlock (Default: @everyone)")
    async def unlock(self, ctx: commands.Context, role: discord.Role = None):
        target_role = role or ctx.guild.default_role
        
        # পারমিশন আপডেট (মেসেজ পাঠানো চালু)
        await ctx.channel.set_permissions(target_role, send_messages=True)

        # স্টাইলিশ এম্বেড ডিজাইন
        embed = discord.Embed(
            title="🔓 Channel Unlocked!",
            description=f"This channel is now open for {target_role.mention}. Everyone can chat now!",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        embed.add_field(name="🛡️ Authorized by", value=ctx.author.mention, inline=True)
        embed.add_field(name="📍 Channel", value=ctx.channel.mention, inline=True)
        
        # আনলক আইকন GIF
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3064/3064155.png")
        embed.set_footer(text="Funny Bot Security System", icon_url=self.bot.user.display_avatar.url)

        await ctx.send(embed=embed)

    # এরর হ্যান্ডলিং (পারমিশন না থাকলে)
    @lock.error
    @unlock.error
    async def channel_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need **Manage Channels** permission to use this command!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ChannelControl(bot))
  
