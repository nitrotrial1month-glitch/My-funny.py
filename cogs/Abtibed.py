import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
from utils import load_config, save_config, get_theme_color

# ================= 1. DASHBOARD VIEW =================

class AutoModDashboard(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="ON / OFF", style=discord.ButtonStyle.success, emoji="🛡️")
    async def toggle_mod(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        if "automod_settings" not in config: 
            config["automod_settings"] = {"enabled": False, "bad_words": []}
        
        current_state = config["automod_settings"].get("enabled", False)
        new_state = not current_state
        config["automod_settings"]["enabled"] = new_state
        save_config(config)

        status = "🟢 Enabled" if new_state else "🔴 Disabled"
        await interaction.response.send_message(f"Auto-Mod is now **{status}**", ephemeral=True)

    @discord.ui.button(label="Show Blocked Words", style=discord.ButtonStyle.secondary, emoji="📋")
    async def show_words(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        words = config.get("automod_settings", {}).get("bad_words", [])
        
        if not words:
            return await interaction.response.send_message("The blocked words list is currently empty.", ephemeral=True)
        
        word_list = ", ".join([f"`{w}`" for w in words])
        await interaction.response.send_message(f"**Blocked Words:**\n{word_list}", ephemeral=True)

# ================= 2. AUTO-MOD LOGIC =================

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return # Ignore bots and DMs

        config = load_config()
        settings = config.get("automod_settings", {})

        if not settings.get("enabled", False):
            return # System is OFF

        # Admins bypass the filter
        if message.author.guild_permissions.manage_messages:
            return

        bad_words = settings.get("bad_words", [])
        content = message.content.lower()

        # Check for bad words
        if any(word in content for word in bad_words):
            try:
                await message.delete() # Delete bad message
                warn_embed = discord.Embed(
                    description=f"🚫 {message.author.mention}, your message contained a blacklisted word and was removed.",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=warn_embed, delete_after=5)
            except discord.Forbidden:
                print("Bot lacks permission to delete messages.")

    # ================= 3. COMMANDS =================

    @app_commands.command(name="automod_setup", description="🛠️ Setup the Bad Words Filter Dashboard")
    @app_commands.checks.has_permissions(administrator=True)
    async def automod_setup(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛡️ Auto-Mod Protection",
            description=(
                "Protect your server from bad language and toxicity.\n\n"
                "**Features:**\n"
                "• Automatic Message Deletion\n"
                "• Customizable Word List\n"
                "• Admin Bypass Enabled"
            ),
            color=get_theme_color(interaction.guild.id)
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1162/1162951.png")
        await interaction.response.send_message(embed=embed, view=AutoModDashboard())

    @app_commands.command(name="automod_add", description="➕ Add a word to the blacklist")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def add_word(self, interaction: discord.Interaction, word: str):
        config = load_config()
        if "automod_settings" not in config:
            config["automod_settings"] = {"enabled": False, "bad_words": []}
        
        word = word.lower()
        if word not in config["automod_settings"]["bad_words"]:
            config["automod_settings"]["bad_words"].append(word)
            save_config(config)
            await interaction.response.send_message(f"✅ Added `{word}` to the blacklist.", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ `{word}` is already in the list.", ephemeral=True)

    @app_commands.command(name="automod_remove", description="➖ Remove a word from the blacklist")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def remove_word(self, interaction: discord.Interaction, word: str):
        config = load_config()
        word = word.lower()
        
        if "automod_settings" in config and word in config["automod_settings"]["bad_words"]:
            config["automod_settings"]["bad_words"].remove(word)
            save_config(config)
            await interaction.response.send_message(f"✅ Removed `{word}` from the blacklist.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ `{word}` was not found in the list.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
              
