import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select, ChannelSelect, RoleSelect
import datetime
import re
from utils import load_config, save_config, get_theme_color

# ================= 1. WHITELIST MENUS (মাল্টিপল চ্যানেল/রোল সাপোর্ট) =================

class WhitelistChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="📢 Select Channels to Whitelist...",
            channel_types=[discord.ChannelType.text, discord.ChannelType.news, discord.ChannelType.voice],
            min_values=1,
            max_values=5 # একসাথে ৫টি চ্যানেল সিলেক্ট করা যাবে
        )

    async def callback(self, interaction: discord.Interaction):
        config = load_config()
        if "antilink_settings" not in config: config["antilink_settings"] = {}
        
        # বর্তমান লিস্ট নেওয়া
        current_list = config["antilink_settings"].get("whitelist_channels", [])
        
        # নতুন চ্যানেলগুলো যোগ করা (ডুপ্লিকেট এড়ানো)
        new_channels = [c.id for c in self.values]
        updated_list = list(set(current_list + new_channels))
        
        config["antilink_settings"]["whitelist_channels"] = updated_list
        save_config(config)
        
        await interaction.response.send_message(f"✅ Added **{len(new_channels)}** channels to whitelist!", ephemeral=True)

class WhitelistRoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(
            placeholder="🛡️ Select Roles to Whitelist...",
            min_values=1,
            max_values=5
        )

    async def callback(self, interaction: discord.Interaction):
        config = load_config()
        if "antilink_settings" not in config: config["antilink_settings"] = {}
        
        current_list = config["antilink_settings"].get("whitelist_roles", [])
        
        new_roles = [r.id for r in self.values]
        updated_list = list(set(current_list + new_roles))
        
        config["antilink_settings"]["whitelist_roles"] = updated_list
        save_config(config)
        
        await interaction.response.send_message(f"✅ Added **{len(new_roles)}** roles to whitelist!", ephemeral=True)

class WhitelistView(View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(WhitelistChannelSelect())
        self.add_item(WhitelistRoleSelect())

# ================= 2. DASHBOARD (কন্ট্রোল প্যানেল) =================

class AntiLinkDashboard(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Toggle ON/OFF", style=discord.ButtonStyle.success, emoji="🛡️", row=0)
    async def toggle_system(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        if "antilink_settings" not in config: config["antilink_settings"] = {}
        
        current = config["antilink_settings"].get("enabled", False)
        new_state = not current
        config["antilink_settings"]["enabled"] = new_state
        save_config(config)
        
        status = "🟢 Enabled" if new_state else "🔴 Disabled"
        btn_style = discord.ButtonStyle.success if new_state else discord.ButtonStyle.danger
        button.style = btn_style
        
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"Anti-Link System is now **{status}**", ephemeral=True)

    @discord.ui.button(label="Whitelist Menu", style=discord.ButtonStyle.primary, emoji="🔓", row=0)
    async def whitelist_menu(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("👇 **Select Channels or Roles to Whitelist:**", view=WhitelistView(), ephemeral=True)

    @discord.ui.button(label="Set Punishment", style=discord.ButtonStyle.danger, emoji="⚖️", row=0)
    async def set_punishment(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        if "antilink_settings" not in config: config["antilink_settings"] = {}
        
        # Cycle: None -> Timeout -> Kick -> Ban
        modes = ["None", "Timeout", "Kick", "Ban"]
        current = config["antilink_settings"].get("punishment", "None")
        
        try: next_idx = (modes.index(current) + 1) % len(modes)
        except: next_idx = 0
            
        new_mode = modes[next_idx]
        config["antilink_settings"]["punishment"] = new_mode
        save_config(config)
        
        await interaction.response.send_message(f"⚖️ Punishment Mode updated to: **{new_mode}**", ephemeral=True)

    @discord.ui.button(label="Reset Whitelist", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def reset_config(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        if "antilink_settings" in config:
            config["antilink_settings"]["whitelist_channels"] = []
            config["antilink_settings"]["whitelist_roles"] = []
            save_config(config)
            await interaction.response.send_message("✅ Whitelist has been reset!", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ No settings found to reset.", ephemeral=True)

    @discord.ui.button(label="Check Config", style=discord.ButtonStyle.gray, emoji="👀", row=1)
    async def check_config(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        als = config.get("antilink_settings", {})
        
        status = "🟢 ON" if als.get("enabled") else "🔴 OFF"
        mode = als.get("punishment", "None")
        
        wc = len(als.get('whitelist_channels', []))
        wr = len(als.get('whitelist_roles', []))

        embed = discord.Embed(title="🛡️ Anti-Link Settings", color=get_theme_color(interaction.guild.id))
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Punishment", value=f"`{mode}`", inline=True)
        embed.add_field(name="Whitelisted Channels", value=f"{wc} Channels", inline=True)
        embed.add_field(name="Whitelisted Roles", value=f"{wr} Roles", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ================= 3. SYSTEM LOGIC =================

class AntiLink(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return 
        
        # 1. Config Load
        config = load_config()
        als = config.get("antilink_settings", {})
        
        if not als.get("enabled", False): return

        # 2. Admin Bypass
        if message.author.guild_permissions.administrator or message.author.guild_permissions.manage_messages:
            return

        # 3. Whitelist Check (Channel & Role)
        if message.channel.id in als.get("whitelist_channels", []): return
        
        user_roles = [r.id for r in message.author.roles]
        whitelist_roles = als.get("whitelist_roles", [])
        # যদি ইউজারের কোনো রোল হোয়াইটলিস্টে থাকে
        if any(role in whitelist_roles for role in user_roles): return

        # 4. Link Detection (Regex for accuracy)
        # http/https/www/discord.gg ডিটেক্ট করবে
        link_regex = r"(https?://|www\.|discord\.(gg|io|me|li)|discordapp\.com/invite)"
        if re.search(link_regex, message.content.lower()):
            try:
                await message.delete()
                
                # Warning
                warn = await message.channel.send(f"🚫 {message.author.mention}, **Links are not allowed!**")
                
                # Punishment
                mode = als.get("punishment", "None")
                reason = "Anti-Link Auto Punishment"
                
                if mode == "Timeout":
                    # 1 Minute Mute
                    await message.author.timeout(datetime.timedelta(minutes=1), reason=reason)
                elif mode == "Kick":
                    await message.author.kick(reason=reason)
                elif mode == "Ban":
                    await message.author.ban(reason=reason, delete_message_days=0)

                # Delete warning after 5s
                import asyncio
                await asyncio.sleep(5)
                await warn.delete()

            except discord.Forbidden:
                print(f"Missing permissions to punish {message.author}")
            except Exception as e:
                print(f"AntiLink Error: {e}")

    # --- Hybrid Command: Setup ---
    @commands.hybrid_command(name="antilink_setup", description="🛡️ Open Advanced Anti-Link Dashboard")
    @commands.has_permissions(administrator=True)
    async def antilink_setup(self, ctx: commands.Context):
        embed = discord.Embed(
            title="🛡️ Advanced Anti-Link System",
            description=(
                "Protect your server from spam links.\n\n"
                "• **Multiple Whitelists:** Add many channels/roles.\n"
                "• **Punishments:** Timeout, Kick, or Ban.\n"
                "• **Smart Detection:** Blocks hidden links."
            ),
            color=get_theme_color(ctx.guild.id)
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2092/2092663.png")
        
        await ctx.send(embed=embed, view=AntiLinkDashboard())

async def setup(bot):
    await bot.add_cog(AntiLink(bot))
                    
