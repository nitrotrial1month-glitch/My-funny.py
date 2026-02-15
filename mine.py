import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from utils import load_config, save_config
from keep_alive import keep_alive 

# --- ১. ডাইনামিক প্রেফিক্স লজিক ---
def get_prefix(bot, message):
    # যদি মেসেজটি ডাইরেক্ট মেসেজ (DM) হয়, তবে ডিফল্ট '!' ব্যবহার করবে
    if not message.guild:
        return "!"
    
    config = load_config()
    # কনফিগারেশন থেকে সার্ভারের প্রেফিক্স খুঁজবে, না পেলে '!' দিবে
    return config.get("prefixes", {}).get(str(message.guild.id), "!")

# --- ২. মেইন বট ক্লাস সেটআপ ---
class FunnyBot(commands.Bot):
    def __init__(self):
        # সব ইনটেন্টস অন করা হয়েছে (ইনভাইট ট্র্যাকিং ও অডিট লগের জন্য জরুরি)
        intents = discord.Intents.all() 
        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            help_command=None, # ডিফল্ট হেল্প কমান্ড বন্ধ রাখা হয়েছে
            case_insensitive=True
        )

    async def setup_hook(self):
        print("🔄 Loading Cogs...")
        # cogs ফোল্ডার থেকে সব এক্সটেনশন লোড করবে
        if os.path.exists('./cogs'):
            for filename in os.listdir('./cogs'):
                if filename.endswith('.py'):
                    try:
                        await self.load_extension(f'cogs.{filename[:-3]}')
                        print(f"  ✅ Loaded Extension: {filename}")
                    except Exception as e:
                        print(f"  ❌ Failed to load {filename}: {e}")
        
        # স্লাশ কমান্ডগুলো ডিসকর্ডের সাথে সিঙ্ক করবে
        try:
            synced = await self.tree.sync()
            print(f"🛰️ Synced {len(synced)} slash commands globally!")
        except Exception as e:
            print(f"❌ Failed to sync commands: {e}")

# বট ইনস্ট্যান্স তৈরি
bot = FunnyBot()

# --- ৩. ইভেন্টস (Events) ---
@bot.event
async def on_ready():
    print(f"🚀 Logged in as {bot.user} (ID: {bot.user.id})")
    print("------ Ready to go! ------")
    # বটের স্ট্যাটাস সেট করা
    await bot.change_presence(activity=discord.Game(name="/help | !help"))

# --- ৪. প্রেফিক্স চেঞ্জ কমান্ড (Set Prefix) ---
@bot.hybrid_command(name="set_prefix", description="⚙️ Change the bot prefix for this server")
@commands.has_permissions(administrator=True)
@app_commands.describe(new_prefix="Type the new prefix (e.g., !, $, #)")
async def set_prefix(ctx, new_prefix: str):
    config = load_config()
    
    # কনফিগ ফাইলে prefixes সেকশন না থাকলে তৈরি করবে
    if "prefixes" not in config:
        config["prefixes"] = {}
        
    # নতুন প্রেফিক্স সেভ করা
    config["prefixes"][str(ctx.guild.id)] = new_prefix
    save_config(config)

    # কনফার্মেশন মেসেজ
    embed = discord.Embed(
        title="✅ Prefix Updated",
        description=f"Prefix for **{ctx.guild.name}** has been set to `{new_prefix}`",
        color=discord.Color.green()
    )
    embed.set_footer(text="Funny Bot Settings", icon_url=bot.user.display_avatar.url)
    await ctx.send(embed=embed)

# --- ৫. বট রান করা (Run Bot) ---
if __name__ == "__main__":
    keep_alive() # ওয়েব সার্ভার চালু রাখা (Render এর জন্য)
    
    # এনভায়রনমেন্ট ভেরিয়েবল থেকে টোকেন নেওয়া
    token = os.getenv("DISCORD_TOKEN")
    
    if token:
        bot.run(token)
    else:
        print("❌ Error: 'DISCORD_TOKEN' not found in environment variables!")
        
