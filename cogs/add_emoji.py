import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import re
from typing import Optional

class EmojiManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="add_emoji", 
        description="✨ Add a new emoji to the server"
    )
    @app_commands.describe(
        emoji="Paste an emoji, URL, or ID",
        name="The name for the emoji (Optional)"
    )
    @app_commands.checks.has_permissions(manage_expressions=True)
    async def add_emoji(
        self, 
        interaction: discord.Interaction, 
        emoji: str, 
        name: Optional[str] = None
    ):
        await interaction.response.defer()
        
        image_url = ""
        display_name = name

        # ১. ইমোজি ফরম্যাট থেকে আইডি বের করা (যেমন: <:name:123456789>)
        custom_emoji_regex = re.compile(r"<a?:[a-zA-Z0-9_]+:([0-9]+)>")
        match = custom_emoji_regex.match(emoji)

        if match:
            emoji_id = match.group(1)
            is_animated = emoji.startswith("<a:")
            ext = "gif" if is_animated else "png"
            image_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}"
        elif emoji.isdigit(): # শুধু আইডি দিলে
            image_url = f"https://cdn.discordapp.com/emojis/{emoji}.png"
        else: # সরাসরি লিঙ্ক দিলে
            image_url = emoji

        # ২. নাম সেট করা (যদি ইউজার না দেয়)
        if not display_name:
            try:
                # ইউআরএল থেকে নাম বের করা
                temp_name = image_url.split('/')[-1].split('?')[0].rsplit('.', 1)[0]
                display_name = temp_name if len(temp_name) > 1 else "emoji"
            except:
                display_name = "emoji"

        # নাম ক্লিন করা (ডিসকর্ড স্ট্যান্ডার্ড)
        final_name = re.sub(r'[^a-zA-Z0-9_]', '', display_name)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        return await interaction.followup.send("❌ **Error:** Could not download the image. Make sure the link/emoji is valid.")
                    
                    image_bytes = await response.read()

                    # ৩. ইমোজি তৈরি করা
                    new_emoji = await interaction.guild.create_custom_emoji(
                        name=final_name, 
                        image=image_bytes, 
                        reason=f"Added by {interaction.user}"
                    )
                    
                    embed = discord.Embed(
                        description=f"✅ **Emoji Added Successfully!**\n\n**Name:** `{new_emoji.name}`\n**Preview:** {new_emoji}",
                        color=0x2b2d31
                    )
                    embed.set_thumbnail(url=new_emoji.url)
                    
                    await interaction.followup.send(embed=embed)

        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ **Discord Error:** {e.text}")
        except Exception as e:
            await interaction.followup.send(f"❌ **An error occurred:** Please provide a valid Image URL or Emoji.")

async def setup(bot):
    await bot.add_cog(EmojiManager(bot))
    
