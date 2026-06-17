import discord
from discord.ext import commands
from discord import app_commands
import os
from utils import load_config, save_config
from database import Database
from keep_alive import keep_alive  

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

class FunnyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all() 
        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            help_command=None, 
            case_insensitive=True,
            strip_after_prefix=True
        )
        
        # ⚠️ আপনার আসল ডিসকর্ড রোলের আইডিগুলো এখানে বসিয়ে নেবেন
        self.SELLER_ROLE_ID = 123456789012345678 
        self.OWNER_ROLE_ID = 987654321098765432 # <-- ওনার রোলের আইডি এখানে দিন

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
        if before.roles != after.roles:
            is_seller = any(role.id == self.SELLER_ROLE_ID for role in after.roles)
            is_owner = any(role.id == self.OWNER_ROLE_ID for role in after.roles)

            # ডাটাবেসে একসাথে Seller এবং Owner স্ট্যাটাস সেভ করে দেওয়া হলো
            Database.update_website_roles(after.id, after.name, is_seller, is_owner)
            
            seller_role_before = discord.utils.get(before.roles, id=self.SELLER_ROLE_ID)
            seller_role_after = discord.utils.get(after.roles, id=self.SELLER_ROLE_ID)
            owner_role_before = discord.utils.get(before.roles, id=self.OWNER_ROLE_ID)
            owner_role_after = discord.utils.get(after.roles, id=self.OWNER_ROLE_ID)

            if not seller_role_before and seller_role_after:
                print(f"Granting website seller access to: {after.name}")
                try:
                    await after.send("Congratulations! You now have Seller access on the website.")
                except discord.Forbidden:
                    pass

            if not owner_role_before and owner_role_after:
                print(f"Granting website OWNER access to: {after.name}")
                try:
                    await after.send("Congratulations! You now have Owner access on the website.")
                except discord.Forbidden:
                    pass

bot = FunnyBot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------ Ready to go! ------")
    await bot.change_presence(activity=discord.Game(name="/help | Nova help"))

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

if __name__ == "__main__":
    keep_alive()
    
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("Error: 'DISCORD_TOKEN' not found!")
                    
