import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from typing import Union, Optional

class EmojiManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= 🎨 ADD EMOJI COMMAND =================
    @commands.hybrid_command(name="addemoji", description="🎨 Add a new emoji to the server")
    @app_commands.describe(source="The emoji, URL, or file to add", name="Optional name for the emoji")
    @commands.has_permissions(manage_emojis=True)
    async def addemoji(self, ctx, source: Union[discord.PartialEmoji, discord.Attachment, str], name: Optional[str] = None):
        """
        Usage:
        1. !addemoji <emoji> [name] (Steal from other server)
        2. !addemoji <url> [name] (Add from link)
        3. !addemoji (attach image) [name] (Upload file)
        """
        await ctx.defer() # প্রসেসিংয়ের সময় নেওয়ার জন্য

        image_url = None
        emoji_name = name

        try:
            # ১. যদি সোর্স হয় অন্য সার্ভারের ইমোজি (PartialEmoji)
            if isinstance(source, discord.PartialEmoji):
                image_url = source.url
                if not emoji_name:
                    emoji_name = source.name

            # ২. যদি সোর্স হয় ফাইল আপলোড (Attachment)
            elif isinstance(source, discord.Attachment):
                image_url = source.url
                if not emoji_name:
                    # ফাইলের নাম থেকে .png বা .jpg বাদ দিয়ে নাম নেওয়া হবে
                    emoji_name = source.filename.rsplit('.', 1)[0]

            # ৩. যদি সোর্স হয় কোনো লিংক (String URL)
            elif isinstance(source, str):
                image_url = source
                if not emoji_name:
                    emoji_name = "custom_emoji"

            # --- ইমেজ ডাউনলোড করা ---
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        return await ctx.send("❌ Failed to download image.")
                    image_data = await resp.read()

            # --- ইমোজি সার্ভারে ক্রিয়েট করা ---
            new_emoji = await ctx.guild.create_custom_emoji(name=emoji_name, image=image_data)

            # --- সাকসেস মেসেজ ---
            embed = discord.Embed(
                title="✅ Emoji Added!",
                description=f"Successfully added {new_emoji} as `:{new_emoji.name}:`",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=new_emoji.url)
            embed.set_footer(text=f"Added by {ctx.author.name}")
            await ctx.send(embed=embed)

        except discord.HTTPException as e:
            if "256 kb" in str(e).lower():
                await ctx.send("❌ Image is too big! Discord only allows emojis under 256KB.")
            elif "limit reached" in str(e).lower():
                await ctx.send("❌ This server has reached the emoji limit!")
            else:
                await ctx.send(f"❌ Error: {e}")
        except Exception as e:
            await ctx.send(f"❌ Something went wrong: {e}")

async def setup(bot):
    await bot.add_cog(EmojiManager(bot))
    
