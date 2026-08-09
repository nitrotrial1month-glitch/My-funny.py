import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput, Select, RoleSelect, ChannelSelect
import datetime
from utils import load_config, save_config

# ================= 1. MODALS (এডিটিং ফর্ম) =================

class ContentModal(Modal, title="📝 Edit Panel Text"):
    title_input = TextInput(label="Title", placeholder="Funny Bot Support", required=True)
    desc_input = TextInput(label="Description", style=discord.TextStyle.paragraph, placeholder="Select a category...", required=True)
    footer_input = TextInput(label="Footer", placeholder="Powered by Funny Bot", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in config: config[guild_id] = {}
        if "ticket_config" not in config[guild_id]: config[guild_id]["ticket_config"] = {}
        
        config[guild_id]["ticket_config"]["title"] = self.title_input.value
        config[guild_id]["ticket_config"]["description"] = self.desc_input.value
        config[guild_id]["ticket_config"]["footer"] = self.footer_input.value
        save_config(config)
        await interaction.response.send_message("✅ **Text Updated!** Use `/ticket_set` to see changes.", ephemeral=True)

class VisualModal(Modal, title="🎨 Edit Visuals"):
    image_url = TextInput(label="Main GIF/Image URL", placeholder="https://...", required=False)
    thumb_url = TextInput(label="Thumbnail URL", placeholder="https://...", required=False)
    color_hex = TextInput(label="Color (Hex)", placeholder="#00ff00", max_length=7, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in config: config[guild_id] = {}
        if "ticket_config" not in config[guild_id]: config[guild_id]["ticket_config"] = {}
        
        if self.image_url.value: config[guild_id]["ticket_config"]["image"] = self.image_url.value
        if self.thumb_url.value: config[guild_id]["ticket_config"]["thumbnail"] = self.thumb_url.value
        if self.color_hex.value: config[guild_id]["ticket_config"]["color"] = self.color_hex.value
        save_config(config)
        await interaction.response.send_message("✅ **Visuals Updated!** Use `/ticket_set` to see changes.", ephemeral=True)

class CategoryModal(Modal, title="📂 Add New Category"):
    name = TextInput(label="Name", placeholder="Donation", required=True)
    emoji = TextInput(label="Emoji", placeholder="💰", max_length=2, required=True)
    desc = TextInput(label="Description", placeholder="For donations...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in config: config[guild_id] = {}
        if "ticket_config" not in config[guild_id]: config[guild_id]["ticket_config"] = {}
        if "categories" not in config[guild_id]["ticket_config"]: config[guild_id]["ticket_config"]["categories"] = []

        new_cat = {"label": self.name.value, "emoji": self.emoji.value, "description": self.desc.value, "value": self.name.value}
        config[guild_id]["ticket_config"]["categories"].append(new_cat)
        save_config(config)
        await interaction.response.send_message(f"✅ Added Category: **{self.name.value}**", ephemeral=True)

# ================= 2. TICKET LOGIC (Dropdown & Channel) =================

class TicketSelect(Select):
    def __init__(self, categories):
        options = []
        for cat in categories:
            options.append(discord.SelectOption(
                label=cat["label"], 
                emoji=cat["emoji"], 
                description=cat["description"], 
                value=cat["value"]
            ))
        
        # ⚠️ ফিক্স: এখানে options=options যোগ করা হয়েছে
        super().__init__(
            placeholder="👇 Select Support Category...", 
            min_values=1, 
            max_values=1, 
            options=options, 
            custom_id="ticket_dropdown"
        )

    async def callback(self, interaction: discord.Interaction):
        # ড্রপডাউন রিসেট করার দরকার নেই, শুধু টিকিট ক্রিয়েট করবে
        await self.create_ticket(interaction, self.values[0])

    async def create_ticket(self, interaction: discord.Interaction, category_name):
        guild = interaction.guild
        guild_id = str(guild.id)
        config = load_config()
        
        if guild_id not in config: config[guild_id] = {}
        
        # Ticket Count Logic
        count = config[guild_id].get("ticket_count", 0) + 1
        config[guild_id]["ticket_count"] = count
        save_config(config)

        # Channel Name & Perms
        ch_name = f"ticket-{category_name.lower()}-{count:04d}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Add Staff Roles
        staff_ids = config[guild_id].get("ticket_config", {}).get("staff_roles", [])
        staff_mentions = []
        for role_id in staff_ids:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                staff_mentions.append(role.mention)

        try:
            # Category Check
            cat_id = config[guild_id].get("ticket_config", {}).get("category_id")
            category_channel = guild.get_channel(cat_id) if cat_id else None
            
            channel = await guild.create_text_channel(name=ch_name, overwrites=overwrites, category=category_channel)
            
            # Ticket Inner Embed
            embed = discord.Embed(
                title=f"🎫 {category_name} Support",
                description=f"Hello {interaction.user.mention}!\nWelcome to **{category_name}** ticket.\n\n**Staff:** {' '.join(staff_mentions)}\nPlease describe your issue.",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            
            # Close Button Logic
            async def close_callback(intr):
                await intr.response.send_message("🔒 Closing in 5 seconds...")
                import asyncio
                await asyncio.sleep(5)
                await intr.channel.delete()

            close_btn = Button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
            close_btn.callback = close_callback
            view = View()
            view.add_item(close_btn)

            await channel.send(content=f"{interaction.user.mention} {' '.join(staff_mentions)}", embed=embed, view=view)
            await interaction.response.send_message(f"✅ Ticket Created: {channel.mention}", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

class TicketView(View):
    def __init__(self, categories):
        super().__init__(timeout=None)
        self.add_item(TicketSelect(categories))

# ================= 3. DASHBOARD VIEW (Admin) =================

class DashboardView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Edit Text", style=discord.ButtonStyle.primary, row=0)
    async def edit_text(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ContentModal())

    @discord.ui.button(label="🎨 Edit Visuals", style=discord.ButtonStyle.secondary, row=0)
    async def edit_visuals(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(VisualModal())

    @discord.ui.button(label="📂 Add Category", style=discord.ButtonStyle.success, row=1)
    async def add_cat(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CategoryModal())

    @discord.ui.button(label="♻️ Reset Defaults", style=discord.ButtonStyle.danger, row=1)
    async def reset_config(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        guild_id = str(interaction.guild.id)
        if guild_id not in config: config[guild_id] = {}
        
        config[guild_id]["ticket_config"] = {} # Full Reset
        save_config(config)
        await interaction.response.send_message("🗑️ **Config Reset!** Now using Default Normal Panel.", ephemeral=True)

    @discord.ui.select(cls=RoleSelect, placeholder="🛡️ Add Staff Role", min_values=1, max_values=1, row=2)
    async def select_role(self, interaction: discord.Interaction, select: RoleSelect):
        config = load_config()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in config: config[guild_id] = {}
        if "ticket_config" not in config[guild_id]: config[guild_id]["ticket_config"] = {"staff_roles": []}
        if "staff_roles" not in config[guild_id]["ticket_config"]: config[guild_id]["ticket_config"]["staff_roles"] = []
        
        config[guild_id]["ticket_config"]["staff_roles"].append(select.values[0].id)
        save_config(config)
        await interaction.response.send_message(f"✅ Added Staff: **{select.values[0].name}**", ephemeral=True)

    @discord.ui.select(cls=ChannelSelect, channel_types=[discord.ChannelType.category], placeholder="📂 Set Category Channel", row=3)
    async def select_channel_cat(self, interaction: discord.Interaction, select: ChannelSelect):
        config = load_config()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in config: config[guild_id] = {}
        if "ticket_config" not in config[guild_id]: config[guild_id]["ticket_config"] = {}
        
        config[guild_id]["ticket_config"]["category_id"] = select.values[0].id
        save_config(config)
        await interaction.response.send_message(f"✅ Tickets will open in: **{select.values[0].name}**", ephemeral=True)

# ================= 4. COMMANDS =================

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # COMMAND 1: DASHBOARD
    @app_commands.command(name="ticket_dashboard", description="🛠️ Configure Ticket System (Edit, Add Categories)")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_dashboard(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎛️ Ticket Master Dashboard",
            description="Use the buttons below to customize your ticket panel.\nOnce done, use `/ticket_set` to launch it.",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, view=DashboardView(), ephemeral=True)

    # COMMAND 2: SET PANEL
    @app_commands.command(name="ticket_set", description="🚀 Launch the Ticket Panel in a channel")
    @app_commands.describe(channel="Where to send the panel? (Default: Current Channel)")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_set(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        target_channel = channel or interaction.channel
        config = load_config()
        guild_id = str(interaction.guild.id)
        
        # 서버 아이ডি (guild.id) ভিত্তিক কনফিগ রিড
        tc = config.get(guild_id, {}).get("ticket_config", {})

        # --- FALLBACK TO DEFAULT (যদি কনফিগ না থাকে) ---
        title = tc.get("title", "🎫 Funny Bot Support")
        desc = tc.get("description", "Click below to open a ticket.")
        footer = tc.get("footer", "Powered by Funny Bot")
        image = tc.get("image", "https://media.tenor.com/7b2e6X2s-38AAAAC/discord-ticket.gif")
        thumb = tc.get("thumbnail", "https://cdn-icons-png.flaticon.com/512/4542/4542173.png")
        color = int(tc.get("color", "#5865F2").replace("#", ""), 16)

        categories = tc.get("categories", [])
        
        # ⚠️ ফিক্স: যদি ক্যাটাগরি না থাকে, তবে ডিফল্ট ক্যাটাগরি সেট হবে
        if not categories:
            categories = [
                {"label": "Help", "emoji": "❓", "description": "General Help", "value": "Help"},
                {"label": "Report", "emoji": "⚠️", "description": "Report an issue", "value": "Report"}
            ]

        # Embed Generation
        embed = discord.Embed(title=title, description=desc, color=color)
        embed.set_image(url=image)
        embed.set_thumbnail(url=thumb)
        embed.set_footer(text=footer)

        try:
            # ⚠️ ফিক্স: এখন ক্যাটাগরি লিস্ট সঠিকভাবে ভিউতে যাচ্ছে
            await target_channel.send(embed=embed, view=TicketView(categories))
            await interaction.response.send_message(f"✅ Ticket Panel sent to {target_channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to send panel: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
        
