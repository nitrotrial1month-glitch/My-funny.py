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

# ================= 2. মেইন বট ক্লাস (Funny Bot) =================
class FunnyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            help_command=None,   # ❌ অটো হেল্প সিস্টেম অফ করা হয়েছে
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
bot = FunnyBot()

@bot.event
async def on_ready():
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print(f"""
    ╔══════════════════════════════════════════════╗
    ║            🤡 FUNNY BOT ONLINE 🤡            ║
    ╠══════════════════════════════════════════════╣
    ║ 🤖 Bot Name   : {bot.user.name}             
    ║ 🆔 Bot ID     : {bot.user.id}               
    ║ 📡 Status     : Auto Help OFF               
    ║ 🌍 Hosting    : Render Ready                
    ╚══════════════════════════════════════════════╝
    """)
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing, 
            name="with Jokes | /help"
        ),
        status=discord.Status.online
    )

@bot.event
async def on_message(message):
    if message.author.bot: return
    await bot.process_commands(message)

# ================= 4. সার্ভার স্টার্ট =================
if __name__ == "__main__":
    # ১. ওয়েব সার্ভার চালু করা (Render এর জন্য জরুরি)
    keep_alive()
    
    # ২. বট রান করা (Environment Variable থেকে টোকেন নিবে)
    token = os.getenv("DISCORD_TOKEN")
    
    if token:
        try:
            bot.run(token)
        except Exception as e:
            print(f"❌ Login Error: {e}")
    else:
        print("❌ Error: DISCORD_TOKEN not found!")
