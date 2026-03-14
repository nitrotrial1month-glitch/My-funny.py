import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from dotenv import load_dotenv # .env লোড করার জন্য এটি যোগ করা হয়েছে
from utils import load_config, save_config
# from keep_alive import keep_alive # AWS-এ keep_alive দরকার নেই, তাই কমেন্ট করে দিলাম

# --- ০. এনভায়রনমেন্ট ভেরিয়েবল লোড করা ---
load_dotenv() 

# --- ১. Smart Prefix Logic ---
def get_prefix(bot, message):
    default_prefix = "Nova"
    prefixes = [default_prefix]
    
    if not message.guild:
        return prefixes

    try:
        config = load_config()
        custom_prefix = config.get("prefixes", {}).get(str(message.guild.id))
        if custom_prefix and custom_prefix != default_prefix:
            prefixes.append(custom_prefix)
    except:
        pass

    return prefixes

# --- ২. Main Bot Class Setup ---
class FunnyBot(commands.Bot):
    def __init__(self):
        # AWS-এ কাজ করার জন্য Intents সব ON রাখা ভালো
        intents = discord.Intents.all() 
        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            help_command=None, 
            case_insensitive=True,
            strip_after_prefix=True
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
            print("🛰️ Syncing commands, please wait...")
            synced = await self.tree.sync()
            print(f"🛰️ Synced {len(synced)} slash commands globally!")
        except Exception as e:
            print(f"❌ Failed to sync commands: {e}")

bot = FunnyBot()

# --- ৩. Events ---
@bot.event
async def on_ready():
    print(f"🚀 Logged in as {bot.user} (ID: {bot.user.id})")
    print("------ Ready to go! ------")
    await bot.change_presence(activity=discord.Game(name="/help | Nova help"))

# --- ৪. Prefix Change Command ---
@bot.hybrid_command(name="set_prefix", description="⚙️ Add a custom prefix")
@commands.has_permissions(administrator=True)
@app_commands.describe(new_prefix="Type the new prefix (e.g., ?)")
async def set_prefix(ctx, new_prefix: str):
    clean_prefix = new_prefix.strip()
    
    config = load_config()
    if "prefixes" not in config:
        config["prefixes"] = {}
        
    config["prefixes"][str(ctx.guild.id)] = clean_prefix
    save_config(config)

    embed = discord.Embed(
        title="✅ Custom Prefix Set",
        description=(
            f"Prefix updated to **`{clean_prefix}`**\n\n"
            f"**Usage Examples:**\n"
            f"✅ `{clean_prefix}help`\n"
            f"✅ `Nova help` (Always works)"
        ),
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

# --- ৫. Run ---
if __name__ == "__main__":
    # keep_alive() # AWS ২৪ ঘণ্টা চলে, তাই এটি আর প্রয়োজন নেই
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ Error: 'DISCORD_TOKEN' not found in .env file!")
        
