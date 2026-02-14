import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, RoleSelect
import os
from utils import load_config, save_config, get_theme_color

# ================= 1. ROLE SELECT MENU =================

class AutoRoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(
            placeholder="🛡️ Select a Role to give...",
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        role = self.values[0]
        
        # Check Role Hierarchy
        if role.position >= interaction.guild.me.top_role.position:
            await interaction.response.send_message(
                f"❌ **Error:** {role.mention} is higher than my role! Please move my role above this role in Server Settings.", 
                ephemeral=True
            )
            return

        config = load_config()
        if "autorole_settings" not in config: config["autorole_settings"] = {}
        
        config["autorole_settings"]["role_id"] = role.id
        config["autorole_settings"]["enabled"] = True
        save_config(config)
        
        await interaction.response.send_message(f"✅ Auto Role set to {role.mention} and System is now **ON**!", ephemeral=True)

class RoleView(View):
    def __init__(self):
        super().__init__()
        self.add_item(AutoRoleSelect())

# ================= 2. MAIN DASHBOARD =================

class AutoRoleDashboard(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Set Role", style=discord.ButtonStyle.success, emoji="🛡️", row=0)
    async def set_role(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("👇 **Select the role below:**", view=RoleView(), ephemeral=True)

    @discord.ui.button(label="ON / OFF", style=discord.ButtonStyle.danger, emoji="🔌", row=0)
    async def toggle_system(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        if "autorole_settings" not in config: config["autorole_settings"] = {}
        
        current = config["autorole_settings"].get("enabled", False)
        new_state = not current
        config["autorole_settings"]["enabled"] = new_state
        save_config(config)
        
        status = "🟢 Enabled" if new_state else "🔴 Disabled"
        await interaction.response.send_message(f"Auto Role System is now **{status}**", ephemeral=True)

    @discord.ui.button(label="Check Config", style=discord.ButtonStyle.secondary, emoji="👀", row=0)
    async def check_config(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        ars = config.get("autorole_settings", {})
        
        status = "🟢 ON" if ars.get("enabled") else "🔴 OFF"
        role_id = ars.get("role_id")
        role = interaction.guild.get_role(role_id) if role_id else None
        role_name = role.mention if role else "❌ Not Set"

        await interaction.response.send_message(
            f"📊 **Current Settings:**\n• **Status:** {status}\n• **Role:** {role_name}", 
            ephemeral=True
        )

# ================= 3. SYSTEM LOGIC =================

class AutoRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # 1. Load Config
        config = load_config()
        ars = config.get("autorole_settings", {})

        # 2. Check if enabled
        if not ars.get("enabled", False):
            return

        # 3. Check Role ID
        role_id = ars.get("role_id")
        if not role_id:
            return

        role = member.guild.get_role(role_id)
        if role:
            try:
                await member.add_roles(role)
                print(f"✅ Gave role {role.name} to {member.name}")
            except discord.Forbidden:
                print(f"❌ Error: I don't have permission to give {role.name}")
            except Exception as e:
                print(f"❌ AutoRole Error: {e}")

    # --- Setup Command ---
    @app_commands.command(name="autorole_setup", description="🛡️ Configure the Auto Role System")
    @app_commands.checks.has_permissions(administrator=True)
    async def autorole_setup(self, interaction: discord.Interaction):
        config = load_config()
        ars = config.get("autorole_settings", {})
        
        status = "🟢 ON" if ars.get("enabled") else "🔴 OFF"
        role_id = ars.get("role_id")
        role = interaction.guild.get_role(role_id) if role_id else None
        role_text = role.mention if role else "Not Set"
        
        embed = discord.Embed(
            title="🛡️ Auto Role Setup",
            description=f"Configure the role to be given automatically to new members.\n\n• **Status:** {status}\n• **Role:** {role_text}",
            color=get_theme_color(interaction.guild.id)
        )
        await interaction.response.send_message(embed=embed, view=AutoRoleDashboard())

async def setup(bot):
    await bot.add_cog(AutoRole(bot))
    
