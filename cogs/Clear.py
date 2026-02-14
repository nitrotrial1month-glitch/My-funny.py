import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import datetime
from utils import get_theme_color

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="clear",
        description="🗑️ Bulk delete messages from the current channel (Limit: 500)"
    )
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(amount="The number of messages to delete (Max: 500)")
    async def clear(self, ctx: commands.Context, amount: int):
        # লিমিট চেক
        if amount > 500:
            return await ctx.send("❌ **Error:** You cannot clear more than 500 messages at once!", ephemeral=True)
        
        if amount < 1:
            return await ctx.send("❌ **Error:** Please provide a number between 1 and 500.", ephemeral=True)

        await ctx.defer(ephemeral=True)

        try:
            # মেসেজ ডিলিট করা
            deleted = await ctx.channel.purge(limit=amount if ctx.interaction else amount + 1)
            count = len(deleted)
            
            # --- STYLISH EMBED DESIGN ---
            embed = discord.Embed(
                title="🗑️ Messages Purged!",
                description=f"Successfully cleaned up the conversation in {ctx.channel.mention}.",
                color=get_theme_color(ctx.guild.id), # আপনার utils থেকে থিম কালার নিবে
                timestamp=datetime.datetime.now()
            )
            
            # মেটা ডাটা ফিল্ডস
            embed.add_field(name="📊 Amount", value=f"`{count}` messages", inline=True)
            embed.add_field(name="🛡️ Staff", value=ctx.author.mention, inline=True)
            
            # স্টাইলিশ থাম্বনেইল (ঝাঁড়ুর GIF)
            embed.set_thumbnail(url="https://cdn.pixabay.com/animation/2022/10/27/11/45/11-45-46-340_512.gif")
            
            embed.set_footer(
                text=f"Funny Bot Moderation System", 
                icon_url=self.bot.user.display_avatar.url
            )
            
            # মেসেজটি ৫ সেকেন্ড পর ডিলিট হবে
            msg = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await msg.delete()

        except discord.Forbidden:
            await ctx.send("❌ **Error:** I don't have permission to manage messages!", ephemeral=True)
        except Exception as e:
            await ctx.send(f"❌ **An error occurred:** {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
