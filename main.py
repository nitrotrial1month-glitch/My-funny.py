import discord
from discord.ext import commands
from discord import app_commands
import os
from utils import load_config, save_config
from database import Database
from keep_alive import keep_alive  

# --- 1. Smart Prefix Logic ---
def get_prefix(bot, message):
    # Set default prefix to 'Nova'
    default_prefix = "Nova"
    prefixes = [default_prefix]
    
    # If the message is in a DM, only the default prefix works
    if not message.guild:
        return prefixes

    # Check for custom prefix in configuration
    try:
        config = load_config()
        custom_prefix = config.get("prefixes", {}).get(str(message.guild.id))
        
        # Add custom prefix if it exists and is different from default
        if custom_prefix and custom_prefix != default_prefix:
            prefixes.append(custom_prefix)
    except:
        pass

    return prefixes

# --- 2. Main Bot Class Setup ---
class FunnyBot(commands.Bot):
    def __init__(self):
        # Intents.all() allows the bot to monitor role updates (Server Members Intent)
        intents = discord.Intents.all() 
        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            help_command=None, 
            case_insensitive=True,
            strip_after_prefix=True
        )
        
        # IMPORTANT: Replace this ID with your actual Discord "Seller" Role ID
        self.SELLER_ROLE_ID = 123456789012345678 

    async def setup_hook(self):
        print("Loading Cogs...")
        if os.path.exists('./cogs'):
            for filename in os.listdir('./cogs'):
                if filename.endswith('.py'):
                    try:
                        await self.load_extension(f'cogs.{filename[:-3]}')
                        print(f"  Loaded Extension: {filename}")
                    except Exception as e:
                        print(f"  Failed to load {filename}: {e}")
        
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} slash commands globally!")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

    # --- Role Syncing Logic (E-commerce) ---
    async def on_member_update(self, before, after):
        """Triggers automatically when a member's role changes"""
        if before.roles != after.roles:
            seller_role_before = discord.utils.get(before.roles, id=self.SELLER_ROLE_ID)
            seller_role_after = discord.utils.get(after.roles, id=self.SELLER_ROLE_ID)

            # If Seller role was ADDED
            if not seller_role_before and seller_role_after:
                print(f"Granting website seller access to: {after.name}")
                Database.set_seller_access(after.id, after.name, True)
                try:
                    await after.send("Congratulations! You now have Seller access on the website.")
                except discord.Forbidden:
                    pass

            # If Seller role was REMOVED
            elif seller_role_before and not seller_role_after:
                print(f"Revoking website seller access from: {after.name}")
                Database.set_seller_access(after.id, after.name, False)

# Create bot instance
bot = FunnyBot()

# --- 3. Events ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------ Ready to go! ------")
    await bot.change_presence(activity=discord.Game(name="/help | Nova help"))

# --- 4. Prefix Change Command ---
@bot.hybrid_command(name="set_prefix", description="Add a custom prefix (Default 'Nova' will ALWAYS work)")
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
        title="Custom Prefix Set",
        description=(
            f"Prefix updated to **`{clean_prefix}`**\n\n"
            f"**Usage Examples:**\n"
            f"`{clean_prefix}help`\n"
            f"`{clean_prefix} help` (Space works automatically!)\n"
            f"`Nova help` (Default 'Nova' is always active)"
        ),
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

# --- 5. Run Bot and Web Server ---
if __name__ == "__main__":
    # 1. Start the web server (keep_alive)
    keep_alive()
    
    # 2. Start the Discord bot
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("Error: 'DISCORD_TOKEN' not found!")
        
