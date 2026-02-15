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
        emoji="Upload image or paste Emoji ID/URL",
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

        # 1. Logic for Emoji Input (File or String)
        if isinstance(emoji, discord.Attachment):
            image_url = emoji.url
            if not display_name:
                display_name = emoji.filename.rsplit('.', 1)[0]
        else:
            if emoji.isdigit(): # If user provides just an ID
                image_url = f"https://cdn.discordapp.com/emojis/{emoji}.png"
            else:
                image_url = emoji

        # 2. Extract name from URL if name is still None
        if not display_name:
            try:
                temp_name = image_url.split('/')[-1].split('?')[0].rsplit('.', 1)[0]
                display_name = temp_name if len(temp_name) > 1 else "custom_emoji"
            except:
                display_name = "custom_emoji"

        # 3. Sanitize name (Discord requirements)
        final_name = re.sub(r'[^a-zA-Z0-9_]', '', display_name)
        if len(final_name) < 2:
            final_name = f"emoji_{ctx.author.discriminator if ctx.author.discriminator != '0' else ctx.author.id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        return await ctx.send("❌ **Error:** Unable to fetch image from the provided source.")
                    
                    image_bytes = await response.read()

                    # Create Emoji
                    new_emoji = await ctx.guild.create_custom_emoji(
                        name=final_name, 
                        image=image_bytes, 
                        reason=f"Added by {ctx.author}"
                    )
                    
                    # --- STYLISH EMBED MESSAGE ---
                    embed = discord.Embed(
                        title="<:success:1234567890> New Emoji Created!", 
                        color=0x2F3136 # Sleek Dark Grey
                    )
                    embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
                    embed.add_field(name="📌 Name", value=f"`{new_emoji.name}`", inline=True)
                    embed.add_field(name="🆔 ID", value=f"`{new_emoji.id}`", inline=True)
                    embed.add_field(name="✨ Preview", value=f"{new_emoji}", inline=True)
                    
                    embed.set_image(url=new_emoji.url)
                    embed.set_footer(
                        text=f"Requested by {ctx.author.display_name}", 
                        icon_url=ctx.author.display_avatar.url
                    )
                    
                    await ctx.send(embed=embed)

        except discord.Forbidden:
            await ctx.send("❌ **Permission Denied:** I need `Manage Expressions` permission.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ **Discord Error:** {e.text}")
        except Exception as e:
            await ctx.send(f"❌ **Error:** {str(e)}")

async def setup(bot):
    await bot.add_cog(EmojiManager(bot))
    
