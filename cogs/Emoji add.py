import discord
from discord.ext import commands
from discord import app_commands
import aiohttp

class EmojiManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="add_emoji", 
        description="🖼️ সার্ভারে নতুন ইমোজি যোগ করুন"
    )
    @commands.has_permissions(manage_expressions=True)
    @app_commands.describe(
        name="ইমোজির নাম কি হবে?",
        url="ইমোজির ইমেজ লিঙ্ক (অথবা ইমেজটি এখানে আপলোড করুন)"
    )
    async def add_emoji(self, ctx, name: str, url: str = None):
        # যদি ইউজার ফাইল আপলোড করে, তবে সেই লিঙ্ক নেওয়া হবে
        if ctx.message.attachments:
            url = ctx.message.attachments[0].url
        
        if not url:
            return await ctx.send("❌ দয়া করে একটি ইমেজের লিঙ্ক দিন অথবা ইমেজ আপলোড করুন।", ephemeral=True)

        await ctx.defer() # প্রসেসিং এর জন্য সময় নেওয়া

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return await ctx.send("❌ ইমেজটি ডাউনলোড করা সম্ভব হয়নি। সঠিক লিঙ্ক দিন।")
                    
                    image_data = await response.read()
                    
                    # ইমোজি তৈরি করা
                    new_emoji = await ctx.guild.create_custom_emoji(name=name, image=image_data)
                    
                    embed = discord.Embed(
                        title="✅ Emoji Added!",
                        description=f"সফলভাবে **{new_emoji.name}** ইমোজিটি অ্যাড করা হয়েছে।",
                        color=discord.Color.green()
                    )
                    embed.set_thumbnail(url=new_emoji.url)
                    await ctx.send(embed=embed)

        except discord.Forbidden:
            await ctx.send("❌ আমার 'Manage Expressions' পারমিশন নেই।")
        except discord.HTTPException as e:
            await ctx.send(f"❌ ভুল হয়েছে: সম্ভবত ইমেজের সাইজ অনেক বড় বা ফাইল ফরম্যাট সঠিক নয়।")
        except Exception as e:
            await ctx.send(f"❌ একটি এরর হয়েছে: {str(e)}")

async def setup(bot):
    await bot.add_cog(EmojiManager(bot))
    
