import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import re
from datetime import timedelta
from utils import load_config, save_config, get_theme_color

# ================= 1. DASHBOARD VIEW (বাটন প্যানেল) =================

class AutoModDashboard(View):
    def __init__(self):
        super().__init__(timeout=None)

    # --- Button 1: Bad Words Toggle (ON/OFF) ---
    @discord.ui.button(label="Bad Words Filter", style=discord.ButtonStyle.primary, emoji="🤬", row=0)
    async def toggle_words(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        if "automod_settings" not in config: config["automod_settings"] = {}
        
        current = config["automod_settings"].get("filter_words", False)
        new_state = not current
        config["automod_settings"]["filter_words"] = new_state
        save_config(config)

        status = "🟢 Enabled" if new_state else "🔴 Disabled"
        await interaction.response.send_message(f"**Bad Word Filter** is now **{status}**", ephemeral=True)

    # --- Button 2: Show List (তালিকা দেখা) ---
    @discord.ui.button(label="Show Blocked Words", style=discord.ButtonStyle.secondary, emoji="📋", row=0)
    async def show_words(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        words = config.get("automod_settings", {}).get("bad_words", [])
        
        if not words:
            return await interaction.response.send_message("The blocked words list is empty.", ephemeral=True)
        
        # লিস্ট সুন্দর করে দেখানো
        word_list = ", ".join([f"`{w}`" for w in words])
        await interaction.response.send_message(f"🚫 **Blocked Words:**\n{word_list}", ephemeral=True)

# ================= 2. AUTO-MOD LOGIC (লজিক) =================

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_settings(self):
        config = load_config()
        if "automod_settings" not in config:
            return {"filter_words": False, "bad_words": []}
        return config["automod_settings"]

    # --- Listener: মেসেজ চেক করা ---
    @commands.Cog.listener()
    async def on_message(self, message):
        # ১. বট এবং ডিএম ইগনোর করা
        if message.author.bot or not message.guild:
            return

        # ২. এডমিন বা যাদের পারমিশন আছে তাদের চেক করবে না
        if message.author.guild_permissions.manage_messages or message.author.guild_permissions.administrator:
            return

        settings = self.get_settings()
        
        # যদি ফিল্টার অফ থাকে, তাহলে চেক করার দরকার নেই
        if not settings.get("filter_words", False):
            return

        content = message.content.lower()
        bad_words = settings.get("bad_words", [])
        
        for word in bad_words:
            # Regex: শুধু আলাদা শব্দ হিসেবে থাকলেই ধরবে (যেমন: "class" এ "ass" ধরবে না)
            if re.search(r'\b' + re.escape(word) + r'\b', content):
                try:
                    await message.delete()
                    
                    # ওয়ার্নিং মেসেজ
                    embed = discord.Embed(
                        description=f"🚫 {message.author.mention}, don't use bad language!",
                        color=discord.Color.red()
                    )
                    await message.channel.send(embed=embed, delete_after=5)

                    # ১ মিনিটের টাইমআউট (Timeout)
                    try:
                        await message.author.timeout(timedelta(minutes=1), reason="Bad Language Violation")
                    except:
                        pass # বটের পারমিশন না থাকলে ইগনোর করবে

                except discord.Forbidden:
                    print("❌ Missing Permissions to delete/timeout.")
                break # একটা খারাপ শব্দ পেলেই লুপ থামবে

    # ================= 3. HYBRID COMMANDS (কমান্ড) =================

    # কমান্ড: !antibad অথবা /antibad
    @commands.hybrid_command(name="antibad", description="🛠️ Open Bad Word Filter Dashboard")
    @commands.has_permissions(administrator=True)
    async def antibad(self, ctx: commands.Context):
        settings = self.get_settings()
        status = "🟢 ON" if settings.get('filter_words') else "🔴 OFF"
        
        embed = discord.Embed(
            title="🛡️ Bad Word Protection",
            description=f"**Status:** {status}\n\nClick the buttons below to control the filter.",
            color=get_theme_color(ctx.guild.id)
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1162/1162951.png")
        
        await ctx.send(embed=embed, view=AutoModDashboard())

    # কমান্ড: !block_word [word]
    @commands.hybrid_command(name="block_word", description="➕ Add a word to blocklist")
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(word="The word you want to block")
    async def block_word(self, ctx: commands.Context, word: str):
        config = load_config()
        if "automod_settings" not in config: config["automod_settings"] = {}
        if "bad_words" not in config["automod_settings"]: config["automod_settings"]["bad_words"] = []
        
        word = word.lower().strip()
        
        if word not in config["automod_settings"]["bad_words"]:
            config["automod_settings"]["bad_words"].append(word)
            save_config(config)
            await ctx.send(f"✅ Added `{word}` to blocklist.", ephemeral=True)
        else:
            await ctx.send(f"⚠️ `{word}` is already blocked.", ephemeral=True)

    # কমান্ড: !unblock_word [word]
    @commands.hybrid_command(name="unblock_word", description="➖ Remove a word from blocklist")
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(word="The word you want to unblock")
    async def unblock_word(self, ctx: commands.Context, word: str):
        config = load_config()
        word = word.lower().strip()
        
        try:
            config["automod_settings"]["bad_words"].remove(word)
            save_config(config)
            await ctx.send(f"✅ Removed `{word}` from blocklist.", ephemeral=True)
        except (ValueError, KeyError):
            await ctx.send(f"❌ `{word}` was not found in the list.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
            
