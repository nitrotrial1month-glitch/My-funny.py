import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select, ChannelSelect, RoleSelect
import datetime
from utils import load_config, save_config, get_theme_color

# ================= 1. WHITELIST MENUS (কাদের লিঙ্ক ডিলিট হবে না) =================

class WhitelistChannelSelect(ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="📢 Select Channel to Whitelist...",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        config = load_config()
        if "antilink_settings" not in config: config["antilink_settings"] = {}
        
        # Save Channel ID
        channel_id = self.values[0].id
        config["antilink_settings"]["whitelist_channel"] = channel_id
        save_config(config)
        
        await interaction.response.send_message(f"✅ **{self.values[0].mention}** is now whitelisted! Links allowed here.", ephemeral=True)

class WhitelistRoleSelect(RoleSelect):
    def __init__(self):
        super().__init__(
            placeholder="🛡️ Select Role to Whitelist...",
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        config = load_config()
        if "antilink_settings" not in config: config["antilink_settings"] = {}
        
        # Save Role ID
        role_id = self.values[0].id
        config["antilink_settings"]["whitelist_role"] = role_id
        save_config(config)
        
        await interaction.response.send_message(f"✅ Users with **{self.values[0].mention}** can now send links!", ephemeral=True)

class WhitelistView(View):
    def __init__(self):
        super().__init__()
        self.add_item(WhitelistChannelSelect())
        self.add_item(WhitelistRoleSelect())

# ================= 2. DASHBOARD (মেইন কন্ট্রোল প্যানেল) =================

class AntiLinkDashboard(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="ON / OFF", style=discord.ButtonStyle.success, emoji="🛡️", row=0)
    async def toggle_system(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        if "antilink_settings" not in config: config["antilink_settings"] = {}
        
        current = config["antilink_settings"].get("enabled", False)
        new_state = not current
        config["antilink_settings"]["enabled"] = new_state
        save_config(config)
        
        status = "🟢 Enabled" if new_state else "🔴 Disabled"
        style = discord.ButtonStyle.success if new_state else discord.ButtonStyle.danger
        button.style = style
        
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"Anti-Link System is now **{status}**", ephemeral=True)

    @discord.ui.button(label="Whitelist Settings", style=discord.ButtonStyle.primary, emoji="🔓", row=0)
    async def whitelist_menu(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("👇 **Select Channel or Role to Whitelist:**", view=WhitelistView(), ephemeral=True)

    @discord.ui.button(label="Punishment Mode", style=discord.ButtonStyle.danger, emoji="⚖️", row=0)
    async def set_punishment(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        if "antilink_settings" not in config: config["antilink_settings"] = {}
        
        # Cycle through modes: None -> Timeout -> Kick
        modes = ["None", "Timeout", "Kick"]
        current_mode = config["antilink_settings"].get("punishment", "None")
        
        try:
            next_index = (modes.index(current_mode) + 1) % len(modes)
        except:
            next_index = 0
            
        new_mode = modes[next_index]
        config["antilink_settings"]["punishment"] = new_mode
        save_config(config)
        
        await interaction.response.send_message(f"⚖️ Punishment Mode set to: **{new_mode}**", ephemeral=True)

    @discord.ui.button(label="Check Config", style=discord.ButtonStyle.secondary, emoji="👀", row=1)
    async def check_config(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        als = config.get("antilink_settings", {})
        
        status = "🟢 ON" if als.get("enabled") else "🔴 OFF"
        mode = als.get("punishment", "None")
        
        w_chan = f"<#{als['whitelist_channel']}>" if als.get('whitelist_channel') else "None"
        w_role = f"<@&{als['whitelist_role']}>" if als.get('whitelist_role') else "None"

        embed = discord.Embed(title="🛡️ Anti-Link Configuration", color=get_theme_color(interaction.guild.id))
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Punishment", value=f"`{mode}`", inline=True)
        embed.add_field(name="Whitelisted Channel", value=w_chan, inline=False)
        embed.add_field(name="Whitelisted Role", value=w_role, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ================= 3. SYSTEM LOGIC (লিঙ্ক ডিটেকশন) =================

class AntiLink(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return # বট ইগনোর করবে
        if not message.guild: return
        
        # 1. Load Config
        config = load_config()
        als = config.get("antilink_settings", {})
        
        if not als.get("enabled", False): return

        # 2. Check Admin/Permissions (Admins Bypass)
        if message.author.guild_permissions.administrator or message.author.guild_permissions.manage_messages:
            return

        # 3. Check Whitelists
        if als.get("whitelist_channel") == message.channel.id: return
        if als.get("whitelist_role") in [r.id for r in message.author.roles]: return

        # 4. Link Detection Logic
        links = ["http://", "https://", "www.", "discord.gg", ".com", ".net", ".xyz"]
        content = message.content.lower()
        
        if any(link in content for link in links):
            try:
                # ডিলিট করা
                await message.delete()
                
                # ওয়ার্নিং মেসেজ
                warn_msg = await message.channel.send(
                    f"🚫 {message.author.mention}, **Links are not allowed here!**"
                )
                
                # শাস্তি (Punishment)
                punishment = als.get("punishment", "None")
                
                if punishment == "Timeout":
                    # 1 মিনিটের জন্য টাইমআউট
                    duration = datetime.timedelta(minutes=1)
                    await message.author.timeout(duration, reason="Anti-Link Violation")
                    await message.channel.send(f"🔇 {message.author.mention} has been timed out for 1 minute.", delete_after=5)
                
                elif punishment == "Kick":
                    await message.author.kick(reason="Anti-Link Violation")
                    await message.channel.send(f"👢 {message.author.mention} has been kicked.", delete_after=5)

                # 5 সেকেন্ড পর ওয়ার্নিং ডিলিট
                import asyncio
                await asyncio.sleep(5)
                await warn_msg.delete()

            except discord.Forbidden:
                pass # বটের পাওয়ার না থাকলে এরর ইগনোর করবে
            except Exception as e:
                print(f"AntiLink Error: {e}")

    # --- Setup Command ---
    @app_commands.command(name="antilink_setup", description="🛡️ Open Premium Anti-Link Dashboard")
    @app_commands.checks.has_permissions(administrator=True)
    async def antilink_setup(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛡️ Anti-Link System",
            description="Protect your server from spam links. Use the dashboard below to configure settings.",
            color=get_theme_color(interaction.guild.id)
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2092/2092663.png") # Shield Icon
        
        await interaction.response.send_message(embed=embed, view=AntiLinkDashboard())

async def setup(bot):
    await bot.add_cog(AntiLink(bot))
      
