import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput, Select
import json
import os
import datetime
from utils import load_config, save_config, get_theme_color

# ================= 0. CONFIG & ASSETS =================
# You can change these GIFs to your own links
TICKET_GIF = "https://media.tenor.com/7b2e6X2s-38AAAAC/discord-ticket.gif"
THUMBNAIL_URL = "https://cdn-icons-png.flaticon.com/512/4542/4542173.png"

# ================= 1. MODALS (For Editing Ticket Live) =================
class EditTicketModal(Modal, title="⚙️ Admin Dashboard"):
    new_title = TextInput(label="New Title", placeholder="Ticket Support", required=False)
    new_desc = TextInput(label="New Description", style=discord.TextStyle.paragraph, placeholder="How can we help?", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        # Get current embed
        embed = interaction.message.embeds[0]
        
        if self.new_title.value: embed.title = self.new_title.value
        if self.new_desc.value: embed.description = self.new_desc.value
        
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message("✅ **Ticket Updated Successfully!**", ephemeral=True)

# ================= 2. DASHBOARD VIEW (Inside Ticket) =================
class TicketDashboardView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✏️ Edit Embed", style=discord.ButtonStyle.secondary, emoji="📝")
    async def edit_embed(self, interaction: discord.Interaction, button: Button):
        # Check permissions
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("❌ Admin Only!", ephemeral=True)
        await interaction.response.send_modal(EditTicketModal())

    @discord.ui.button(label="👤 Add Member", style=discord.ButtonStyle.primary, emoji="➕")
    async def add_member(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("👇 **Mention the user to add:**", ephemeral=True)
        
        def check(m): return m.author == interaction.user and m.channel == interaction.channel
        try:
            msg = await interaction.client.wait_for('message', check=check, timeout=30)
            if msg.mentions:
                user = msg.mentions[0]
                await interaction.channel.set_permissions(user, read_messages=True, send_messages=True)
                await interaction.followup.send(f"✅ Added {user.mention} to the ticket.")
            else:
                await interaction.followup.send("❌ No user mentioned.")
        except:
            pass

# ================= 3. TICKET CONTROLS (Close/Claim) =================
class TicketControls(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(description=f"🔒 Ticket closed by {interaction.user.mention}. Deleting in 5s...", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
        import asyncio
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="✋ Claim", style=discord.ButtonStyle.success, custom_id="claim_ticket")
    async def claim_ticket(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(description=f"✅ Ticket claimed by {interaction.user.mention}!", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
        # Disable button
        button.disabled = True
        button.label = f"Claimed by {interaction.user.name}"
        await interaction.message.edit(view=self)

    @discord.ui.button(label="⚙️ Dashboard", style=discord.ButtonStyle.secondary, emoji="🛠️", custom_id="dash_ticket")
    async def dashboard(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("❌ Staff Only!", ephemeral=True)
        
        await interaction.response.send_message(
            "⚙️ **Admin Control Panel**\nUse this to edit the ticket message or add members.", 
            view=TicketDashboardView(), 
            ephemeral=True
        )

# ================= 4. LAUNCHER (Main Panel) =================
class TicketLauncher(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def create_ticket(self, interaction: discord.Interaction, category_name: str, emoji: str):
        config = load_config()
        t_settings = config.get("ticket_settings", {})
        
        # 1. Ticket Number Logic
        count = t_settings.get("count", 0) + 1
        t_settings["count"] = count
        config["ticket_settings"] = t_settings
        save_config(config)

        # 2. Channel Name
        ch_name = f"{emoji}-{category_name.lower()}-{count:04d}"
        guild = interaction.guild
        
        # 3. Permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Add Staff Roles (Multi-Role Support)
        staff_roles = t_settings.get("support_roles", [])
        staff_mentions = []
        for role_id in staff_roles:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                staff_mentions.append(role.mention)

        # 4. Create Channel
        try:
            category = discord.utils.get(guild.categories, id=t_settings.get("category_id"))
            channel = await guild.create_text_channel(name=ch_name, overwrites=overwrites, category=category)
            
            # 5. Welcome Embed
            welcome_embed = discord.Embed(
                title=f"{emoji} {category_name} Ticket Support",
                description=(
                    f"Hello {interaction.user.mention}!\n"
                    f"Thank you for contacting support regarding **{category_name}**.\n\n"
                    f"**Staff:** {' '.join(staff_mentions) if staff_mentions else 'Please wait for staff.'}\n"
                    f"Please describe your issue below."
                ),
                color=get_theme_color(guild.id),
                timestamp=datetime.datetime.now()
            )
            welcome_embed.set_thumbnail(url=interaction.user.display_avatar.url)
            welcome_embed.set_image(url=TICKET_GIF)
            
            msg = await channel.send(
                content=f"{interaction.user.mention} {' '.join(staff_mentions)}", 
                embed=welcome_embed, 
                view=TicketControls()
            )
            await msg.pin()

            await interaction.response.send_message(f"✅ Ticket Created: {channel.mention}", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error creating ticket: {e}", ephemeral=True)

    # --- Buttons ---
    @discord.ui.button(label="Claim / Support", style=discord.ButtonStyle.blurple, emoji="🎫", custom_id="cat_claim")
    async def claim_btn(self, interaction: discord.Interaction, button: Button):
        await self.create_ticket(interaction, "Claim", "🎫")

    @discord.ui.button(label="Buy / Purchase", style=discord.ButtonStyle.success, emoji="🛒", custom_id="cat_buy")
    async def buy_btn(self, interaction: discord.Interaction, button: Button):
        await self.create_ticket(interaction, "Buy", "🛒")

    @discord.ui.button(label="Report Issue", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="cat_report")
    async def report_btn(self, interaction: discord.Interaction, button: Button):
        await self.create_ticket(interaction, "Report", "⚠️")

# ================= 5. MAIN COG =================
class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_ticket", description="🎫 Setup the Premium Ticket Panel")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_ticket(self, interaction: discord.Interaction, channel: discord.TextChannel):
        embed = discord.Embed(
            title="🎫 **Funny Bot Support Center**",
            description=(
                "Please select a category below to open a ticket.\n"
                "Our staff will be with you shortly.\n\n"
                "🔹 **Claim** - Redeem rewards or roles\n"
                "🔹 **Buy** - Purchase premium or items\n"
                "🔹 **Report** - Report bugs or users"
            ),
            color=discord.Color.from_rgb(47, 49, 54) # Dark Theme
        )
        embed.set_image(url=TICKET_GIF)
        embed.set_thumbnail(url=THUMBNAIL_URL)
        embed.set_footer(text="Powered by Funny Bot System")

        await channel.send(embed=embed, view=TicketLauncher())
        await interaction.response.send_message(f"✅ Ticket Panel sent to {channel.mention}!", ephemeral=True)

    @app_commands.command(name="ticket_role_add", description="➕ Add a Support Role (Staff)")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_role(self, interaction: discord.Interaction, role: discord.Role):
        config = load_config()
        if "ticket_settings" not in config: config["ticket_settings"] = {"support_roles": [], "count": 0}
        
        # Add role ID to list if not exists
        current_roles = config["ticket_settings"].get("support_roles", [])
        if role.id not in current_roles:
            current_roles.append(role.id)
            config["ticket_settings"]["support_roles"] = current_roles
            save_config(config)
            await interaction.response.send_message(f"✅ Added {role.mention} to Support Staff.", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ {role.mention} is already a Support Role.", ephemeral=True)

    @app_commands.command(name="ticket_category_set", description="📂 Set the Category where tickets open")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_category(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        config = load_config()
        if "ticket_settings" not in config: config["ticket_settings"] = {}
        
        config["ticket_settings"]["category_id"] = category.id
        save_config(config)
        await interaction.response.send_message(f"✅ Tickets will now open in **{category.name}**", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
