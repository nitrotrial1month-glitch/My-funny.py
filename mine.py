import discord
from discord.ext import commands
from discord import app_commands
import os
from utils import load_config, save_config
from keep_alive import keep_alive 

def get_prefix(bot, message):
    if not message.guild: return "!"
    config = load_config()
    return config.get("prefixes", {}).get(str(message.guild.id), "!")

class FunnyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all() 
        super().__init__(command_prefix=get_prefix, intents=intents, help_command=None, case_insensitive=True)

    async def setup_hook(self):
        print("🔄 Loading Cogs...")
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f"  ✅ Loaded: {filename}")
                except Exception as e:
                    print(f"  ❌ Failed {filename}: {e}")
        # স্ল্যাশ কমান্ড অটো-সিঙ্ক
        await self.tree.sync()
        print("🛰️ Commands Synced!")

bot = FunnyBot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    await bot.change_presence(activity=discord.Game(name="/help | !help"))

if __name__ == "__main__":
    keep_alive() # আপটাইম বজায় রাখার জন্য
    token = os.getenv("DISCORD_TOKEN")
    if token: bot.run(token)
    else: print("❌ Error: DISCORD_TOKEN not found!")
        
