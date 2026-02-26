import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from utils import load_config, save_config
from keep_alive import keep_alive 

# --- ১. স্মার্ট প্রেফিক্স লজিক (আপডেটেড) ---
def get_prefix(bot, message):
    # ডিফল্ট প্রেফিক্স
    default_prefix = "!"
    
    # শুরুতে শুধু ডিফল্ট প্রেফিক্সটি লিস্টে রাখা হলো
    # নোট: এখানে আর ম্যানুয়ালি স্পেস (default_prefix + " ") যোগ করার দরকার নেই
    prefixes = [default_prefix]
    
    # যদি মেসেজটি DM হয়, তবে শুধু ডিফল্টই কাজ করবে
    if not message.guild:
        return prefixes

    # কনফিগারেশন থেকে কাস্টম প্রেফিক্স চেক করা
    try:
        config = load_config()
        # আপনার কনফিগ ফাইল থেকে সার্ভারের আইডি দিয়ে প্রেফিক্স খোঁজা হচ্ছে
        custom_prefix = config.get("prefixes", {}).get(str(message.guild.id))
        
        # যদি কাস্টম প্রেফিক্স থাকে এবং সেটি ডিফল্ট (!) থেকে আলাদা হয়
        if custom_prefix and custom_prefix != default_prefix:
            prefixes.append(custom_prefix) # শুধু কাস্টম প্রেফিক্সটি অ্যাড করা হলো
    except:
        pass

    # এই ফাংশন এখন একটি ক্লিন লিস্ট রিটার্ন করবে। যেমন: ['!', '?']
    return prefixes

# --- ২. মেইন বট ক্লাস সেটআপ ---
class FunnyBot(commands.Bot):
    def __init__(self):
        # সব ইনটেন্টস অন করা জরুরি
        intents = discord.Intents.all() 
        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            help_command=None, 
            case_insensitive=True,
            strip_after_prefix=True # 🔥 ম্যাজিক লাইন: এটি অটোমেটিক স্পেস হ্যান্ডেল করবে
        )

    async def setup_hook(self):
        print("🔄 Loading Cogs...")
        if os.path.exists('./cogs'):
            for filename in os.listdir('./cogs'):
                if filename.endswith('.py'):
                    try:
                        await self.load_extension(f'cogs.{filename[:-3]}')
                        print(f"  ✅ Loaded Extension: {filename}")
                    except Exception as e:
                        print(f"  ❌ Failed to load {filename}: {e}")
        
        try:
            synced = await self.tree.sync()
            print(f"🛰️ Synced {len(synced)} slash commands globally!")
        except Exception as e:
            print(f"❌ Failed to sync commands: {e}")

# বট ইনস্ট্যান্স তৈরি
bot = FunnyBot()

# --- ৩. ইভেন্টস ---
@bot.event
async def on_ready():
    print(f"🚀 Logged in as {bot.user} (ID: {bot.user.id})")
    print("------ Ready to go! ------")
    await bot.change_presence(activity=discord.Game(name="/help | !help"))

# --- ৪. প্রেফিক্স চেঞ্জ কমান্ড ---
@bot.hybrid_command(name="set_prefix", description="⚙️ Add a custom prefix (Default '!' will ALWAYS work)")
@commands.has_permissions(administrator=True)
@app_commands.describe(new_prefix="Type the new prefix (e.g., ?)")
async def set_prefix(ctx, new_prefix: str):
    # ইউজার যদি ভুল করে স্পেস দেয়, তা সরিয়ে ক্লিন করা হচ্ছে
    clean_prefix = new_prefix.strip()
    
    config = load_config()
    if "prefixes" not in config:
        config["prefixes"] = {}
        
    config["prefixes"][str(ctx.guild.id)] = clean_prefix
    save_config(config)

    embed = discord.Embed(
        title="✅ Custom Prefix Set",
        description=f"Prefix updated to **`{clean_prefix}`**\n\n**Usage Examples:**\n✅ `{clean_prefix}help`\n✅ `{clean_prefix} help` (Space works automatically!)\n✅ `!help` (Default always active)",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

# --- ৫. রান ---
if __name__ == "__main__":
    keep_alive()
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ Error: 'DISCORD_TOKEN' not found!")
        
