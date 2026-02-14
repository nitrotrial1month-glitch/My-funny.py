import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
from utils import load_config, save_config
from keep_alive import keep_alive 

# --- ১. ডাইনামিক প্রেফিক্স লজিক ---
def get_prefix(bot, message):
    if not message.guild:
        return "!" # ডিফল্ট প্রেফিক্স
    
    config = load_config()
    prefixes = config.get("prefixes", {})
    return prefixes.get(str(message.guild.id), "!") # না থাকলে ডিফল্ট "!"

# --- ২. মেইন বট ক্লাস ---
class FunnyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True
        )

    async def setup_hook(self):
        print("🔄 Loading Cogs...")
        if os.path.exists('./cogs'):
            for filename in os.listdir('./cogs'):
                if filename.endswith('.py'):
                    try:
                        await self.load_extension(f'cogs.{filename[:-3]}')
                        print(f"  ✅ Loaded: {filename}")
                    except Exception as e:
                        print(f"  ❌ Failed {filename}: {e}")

        # কমান্ড সিঙ্ক করা (স্ল্যাশ কমান্ডের জন্য)
        await self.tree.sync()
        print("🛰️ Commands Synced!")

bot = FunnyBot()

# --- ৩. হাইব্রিড প্রেফিক্স সেট কমান্ড ---
@bot.hybrid_command(name="set_prefix", description="⚙️ Set a custom prefix for this server")
@commands.has_permissions(administrator=True)
@app_commands.describe(new_prefix="The new prefix (e.g. $, #, .)")
async def set_prefix(ctx, new_prefix: str):
    config = load_config()
    config["prefixes"][str(ctx.guild.id)] = new_prefix
    save_config(config)

    embed = discord.Embed(
        title="✅ Prefix Updated",
        description=f"Prefix for **{ctx.guild.name}** is now `{new_prefix}`",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    await bot.change_presence(activity=discord.Game(name="/help | !help"))

# --- ৪. রানার ---
if __name__ == "__main__":
    keep_alive() # ওয়েব সার্ভার চালু
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ Error: DISCORD_TOKEN not found!")
        
