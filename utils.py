import discord
from discord.ext import commands
import json
import os
import asyncio
from utils import load_config
from keep_alive import keep_alive  # ওয়েব সার্ভার ইমপোর্ট

# ================= 1. প্রিফিক্স সেটআপ =================
def get_prefix(bot, message):
    try:
        if os.path.exists('prefixes.json'):
            with open('prefixes.json', 'r') as f:
                prefixes = json.load(f)
            return prefixes.get(str(message.guild.id), "!")
    except:
        pass
    return "!"

# ================= 2. মেইন বট ক্লাস =================
class NovaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            help_command=None,   # ডিফল্ট হেল্প বন্ধ
            case_insensitive=True,
            strip_after_prefix=True
        )

    async def setup_hook(self):
        print("🔄 Loading Cogs...")
        # 'cogs' ফোল্ডারের সব ফাইল লোড করবে
        if os.path.exists('./cogs'):
            for filename in os.listdir('./cogs'):
                if filename.endswith('.py'):
                    try:
                        await self.load_extension(f'cogs.{filename[:-3]}')
                        print(f"  ✅ Loaded: {filename}")
                    except Exception as e:
                        print(f"  ❌ Failed {filename}: {e}")
        else:
            print("⚠️ 'cogs' folder not found!")

        print("🔄 Syncing Commands...")
        try:
            await self.tree.sync()
            print("  🛰️ Slash Commands Synced!")
        except Exception as e:
            print(f"  ⚠️ Sync Error: {e}")

# ================= 3. রানার =================
bot = NovaBot()

@bot.event
async def on_ready():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"✅ {bot.user.name} is Online on Render!")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/help | Nova World"))

# ================= 4. সার্ভার স্টার্ট =================
if __name__ == "__main__":
    # ১. ওয়েব সার্ভার চালু করা (Render এর জন্য জরুরি)
    keep_alive()
    
    # ২. বট রান করা
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ Error: DISCORD_TOKEN not found!")
  
