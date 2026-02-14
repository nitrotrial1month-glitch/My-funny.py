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
    # সার্ভারে কাস্টম প্রেফিক্স না থাকলে "!" ব্যবহার করবে
    return prefixes.get(str(message.guild.id), "!")

# --- ২. মেইন বট ক্লাস ---
class FunnyBot(commands.Bot):
    def __init__(self):
        # ইনভাইট এবং মেম্বার ট্র্যাকিংয়ের জন্য সব ইনটেন্টস অন রাখা হয়েছে
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

        # স্ল্যাশ কমান্ড সিঙ্ক করা
        await self.tree.sync()
        print("🛰️ Commands Synced!")

bot = FunnyBot()

# --- ৩. হাইব্রিড প্রেফিক্স সেট কমান্ড ---
@bot.hybrid_command(name="set_prefix", description="⚙️ Set a custom prefix for this server")
@commands.has_permissions(administrator=True)
@app_commands.describe(new_prefix="The new prefix (e.g. $, #, .)")
async def set_prefix(ctx, new_prefix: str):
    config = load_config()
    if "prefixes" not in config:
        config["prefixes"] = {}
        
    config["prefixes"][str(ctx.guild.id)] = new_prefix
    save_config(config)

    embed = discord.Embed(
        title="✅ Prefix Updated",
        description=f"Prefix for **{ctx.guild.name}** is now `{new_prefix}`",
        color=discord.Color.green(),
        timestamp=ctx.message.created_at
    )
    embed.set_footer(text=f"Funny Bot Configuration", icon_url=bot.user.display_avatar.url)
    await ctx.send(embed=embed)

# --- ৪. ইভেন্টস ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    # বটের স্ট্যাটাস আপডেট (আপনার দেওয়া প্রেফিক্স অনুযায়ী)
    await bot.change_presence(
        activity=discord.Game(name="/help | !help")
    )

# --- ৫. গ্লোবাল এরর হ্যান্ডলিং ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command!", delete_after=5)
    elif isinstance(error, commands.CommandNotFound):
        pass 

# --- ৬. রানার ---
if __name__ == "__main__":
    keep_alive() # রেন্ডার/আপটাইম বজায় রাখার জন্য
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ Error: DISCORD_TOKEN not found!")
        
