import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import re
from typing import Union, Optional

class EmojiManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="add_emoji", 
        description="✨ Add a high-quality emoji to your server"
    )
    @commands.has_permissions(manage_expressions=True)
    @app_commands.describe(
        emoji="Upload an image file or paste an Emoji URL/ID",
        name="The name for the emoji (Optional)"
    )
    async def add_emoji(
        self, 
        ctx, 
        emoji: Union[discord.Attachment, str], 
        name: Optional[str] = None
    ):
        await ctx.defer()
        
        image_url = ""
        display_name = name

        # ১. ইনপুট চেক (ফাইল না কি লিঙ্ক)
        if isinstance(emoji, discord.Attachment):
            image_url = emoji.url
            if not display_name:
                # ফাইল নেম থেকে নাম নেওয়া
                display_name = emoji.filename.rsplit('.', 1)[0]
        else:
            # যদি শুধু আইডি দেয়
            if emoji.isdigit():
                image_url = f"https://cdn.discordapp.com/emojis/{emoji}.png"
            else:
                image_url = emoji

        # ২. নাম ক্লিনিং (স্পেস বা স্পেশাল ক্যারেক্টার বাদ দেওয়া)
        if not display_name:
            try:
                temp_name = image_url.split('/')[-1].split('?')[0].rsplit('.', 1)[0]
                display_name = temp_name if len(temp_name) > 1 else "custom_emoji"
            except:
                display_name = "custom_emoji"

        final_name = re.sub(r'[^a-zA-Z0-9_]', '', display_name)
        if len(final_name) < 2:
            final_name = f"emoji_{ctx.author.id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        return await ctx.send("❌ **Error:** Unable to fetch image. Please check the link.")
                    
                    image_bytes = await response.read()

                    # ইমোজি তৈরি করা
                    new_emoji = await ctx.guild.create_custom_emoji(
                        name=final_name, 
                        image=image_bytes, 
                        reason=f"Added by {ctx.author}"
                    )
                    
                    # স্টাইলিশ ইমবেড
                    embed = discord.Embed(
                        title="<:success:1234567890> New Emoji Created!", 
                        color=0x2F3136
                    )
                    embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
                    embed.add_field(name="📌 Name", value=f"`{new_emoji.name}`", inline=True)
                    embed.add_field(name="🆔 ID", value=f"`{new_emoji.id}`", inline=True)
                    embed.add_field(name="✨ Preview", value=f"{new_emoji}", inline=True)
                    embed.set_image(url=new_emoji.url)
                    embed.set_footer(text=f"By {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
                    
                    await ctx.send(embed=embed)

        except discord.Forbidden:
            await ctx.send("❌ **Error:** I don't have 'Manage Expressions' permission.")
        except Exception as e:
            await ctx.send(f"❌ **Error:** {str(e)}")

async def setup(bot):
    await bot.add_cog(EmojiManager(bot))
    
