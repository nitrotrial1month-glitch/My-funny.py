import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import re
from typing import Optional

class EmojiManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="add_emoji", 
        description="✨ Add a new emoji to this server"
    )
    @app_commands.describe(
        emoji="Upload an image file or paste a direct image URL",
        name="The name for the emoji (Optional)"
    )
    @app_commands.checks.has_permissions(manage_expressions=True)
    async def add_emoji(
        self, 
        interaction: discord.Interaction, 
        emoji: str, 
        name: Optional[str] = None
    ):
        await interaction.response.defer() # প্রসেসিংয়ের জন্য সময় নেওয়া
        
        image_url = emoji
        display_name = name

        # ১. নাম ঠিক করা (যদি ইউজার না দেয়)
        if not display_name:
            # ইউআরএল থেকে নাম বের করার চেষ্টা
            try:
                temp_name = image_url.split('/')[-1].split('?')[0].rsplit('.', 1)[0]
                display_name = temp_name if len(temp_name) > 1 else "emoji"
            except:
                display_name = "emoji"

        # ২. ডিসকর্ড স্ট্যান্ডার্ড অনুযায়ী নাম ক্লিন করা
        final_name = re.sub(r'[^a-zA-Z0-9_]', '', display_name)
        if len(final_name) < 2:
            final_name = f"emoji_{interaction.user.id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        return await interaction.followup.send("❌ **Error:** Failed to download the image. Make sure the link is valid.")
                    
                    image_bytes = await response.read()

                    # ৩. ইমোজি তৈরি করা
                    new_emoji = await interaction.guild.create_custom_emoji(
                        name=final_name, 
                        image=image_bytes, 
                        reason=f"Added by {interaction.user}"
                    )
                    
                    # স্টাইলিশ সাকসেস ইমবেড
                    embed = discord.Embed(
                        description=f"✅ **Emoji Added Successfully!**\n\n**Name:** `{new_emoji.name}`\n**Preview:** {new_emoji}",
                        color=0x2b2d31
                    )
                    embed.set_thumbnail(url=new_emoji.url)
                    embed.set_footer(text=f"Requested by {interaction.user.display_name}")
                    
                    await interaction.followup.send(embed=embed)

        except discord.Forbidden:
            await interaction.followup.send("❌ **Permission Denied:** I need 'Manage Expressions' permission.")
        except Exception as e:
            await interaction.followup.send(f"❌ **An error occurred:** `{str(e)}`")

async def setup(bot):
    await bot.add_cog(EmojiManager(bot))
    
