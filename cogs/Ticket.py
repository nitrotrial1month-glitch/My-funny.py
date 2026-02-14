import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput, Select, RoleSelect, ChannelSelect
import datetime
from utils import load_config, save_config

# ================= 1. MODALS (এডিট করার ফর্ম) =================

# ১. টাইটেল ও ডেসক্রিপশন এডিট
class ContentModal(Modal, title="📝 Edit Text Content"):
    title_input = TextInput(label="Panel Title", placeholder="Funny Bot Support", required=True)
    desc_input = TextInput(label="Description", style=discord.TextStyle.paragraph, placeholder="Select a category below...", required=True)
    footer_input = TextInput(label="Footer Text", placeholder="Powered by Funny Bot", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        if "ticket_config" not in config: config["ticket_config"] = {}
        
        config["ticket_config"]["title"] = self.title_input.value
        config["ticket_config"]["description"] = self.desc_input.value
        config["ticket_config"]["footer"] = self.footer_input.value
        save_config(config)
        await interaction.response.send_message("✅ **Text Content Updated!**", ephemeral=True)

# ২. ছবি ও কালার এডিট
class VisualModal(Modal, title="🎨 Edit Visuals"):
    image_url = TextInput(label="Main GIF/Image URL", placeholder="https://...", required=False)
    thumb_url = TextInput(label="Thumbnail URL", placeholder="https://...", required=False)
    color_hex = TextInput(label="Embed Color (Hex)", placeholder="#00ff00", max_length=7, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        if "ticket_config" not in config: config["ticket_config"] = {}
        
        if self.image_url.value: config["ticket_config"]["image"] = self.image_url.value
        if self.thumb_url.value: config["ticket_config"]["thumbnail"] = self.thumb_url.value
        if self.color_hex.value: 
            try:
                # কালার ভ্যালিডেশন
                int(self.color_hex.value.replace("#", ""), 16)
                config["ticket_config"]["color"] = self.color_hex.value
            except:
                return await interaction.response.send_message("❌ Invalid Hex Color Code!", ephemeral=True)
                
        save_config(config)
        await interaction.response.send_message("✅ **Visuals Updated!**", ephemeral=True)

# ৩. নতুন ক্যাটাগরি এড করা
class CategoryModal(Modal, title="📂 Add New Category"):
    name = TextInput(label="Category Name", placeholder="e.g. Donation", required=True)
    emoji = TextInput(label="Emoji", placeholder="💰", max_length=2, required=True)
    desc = TextInput(label="Short Description", placeholder="For donations...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        if "ticket_config" not in config: config["ticket_config"] = {}
        if "categories" not in config["ticket_config"]: config["ticket_config"]["categories"] = []

        new_cat = {
            "label": self.name.value,
            "emoji": self.emoji.value,
            "description": self.desc.value,
            "value": self.name.value
        }
        
        config["ticket_config"]["categories"].append(new_cat)
        save_config(config)
        await interaction.response.send_message(f"✅ Added Category: **{self.name.value}**", ephemeral=True)

# ================= 2. TICKET SYSTEM LOGIC =================

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
        super().__init__(placeholder="👇 Select a Support Category...", min_values=1, max_values=1, custom_id="ticket_dropdown")

    async def callback(self, interaction: discord.Interaction):
        # ড্রপডাউন রিসেট করা
        self.view.stop()
        config = load_config()
        
        # প্যানেল রিফ্রেশ (যাতে ড্রপডাউন আটকে না থাকে)
        # লজিক: আমরা ভিউ আবার কল করবো না, শুধু ইন্টারঅ্যাকশন হ্যান্ডেল করবো
        
        category_name = self.values[0]
        await self.create_ticket(interaction, category_name)
        
        # মেসেজ রিসেট করার জন্য (Optional)
        # await interaction.message.edit(view=self.view) 

    async def create_ticket(self, interaction: discord.Interaction, category):
        guild = interaction.guild
        config = load_config()
        
        # 1. Ticket Count
        count = config.get("ticket_count", 0) + 1
        config["ticket_count"] = count
        save_config(config)

        # 2. Channel Name
        ch_name = f"ticket-{category.lower()}-{count:04d}"
        
        # 3. Permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # 4. Add Staff Roles
        staff_ids = config.get("ticket_config", {}).get("staff_roles", [])
        staff_mentions = []
        for role_id in staff_ids:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                staff_mentions.append(role.mention)

        # 5. Create Channel
        try:
            cat_id = config.get("ticket_config", {}).get("category_id")
            category_channel = guild.get_channel(cat_id) if cat_id else None
            
            channel = await guild.create_text_channel(name=ch_name, overwrites=overwrites, category=category_channel)
            
            # Embed inside Ticket
            embed = discord.Embed(
                title=f"🎫 {category} Ticket",
                description=f"Hello {interaction.user.mention}!\nWelcome to **{category}** support.\n\n{' '.join(staff_mentions)}\nPlease wait for our staff.",
                color=discord.Color.green()
            )
            
            # Close Button
            close_view = View()
            close_btn = Button(label="Close", style=discord.ButtonStyle.danger, emoji="🔒")
            
            async def close_callback(intr):
                await intr.response.send_message("🔒 Closing ticket...")
                import asyncio
                await asyncio.sleep(3)
                await intr.channel.delete()
                
            close_btn.callback = close_callback
            close_view.add_item(close_btn)

            await channel.send(content=f"{interaction.user.mention} {' '.join(staff_mentions)}", embed=embed, view=close_view)
            await interaction.response.send_message(f"✅ Ticket Created: {channel.mention}", ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

class TicketView(View):
    def __init__(self, categories):
        super().__init__(timeout=None)
        self.add_item(TicketSelect(categories))

# ================= 3. MASTER DASHBOARD =================

class DashboardView(View):
    def __init__(self):
        super().__init__(timeout=None)

    # Row 1: Content Editing
    @discord.ui.button(label="📝 Edit Text", style=discord.ButtonStyle.primary, row=0)
    async def edit_text(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ContentModal())

    @discord.ui.button(label="🎨 Edit Visuals", style=discord.ButtonStyle.secondary, row=0)
    async def edit_visuals(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(VisualModal())

    # Row 2: Management
    @discord.ui.button(label="📂 Add Category", style=discord.ButtonStyle.success, row=1)
    async def add_cat(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CategoryModal())
        
    @discord.ui.button(label="♻️ Reset Categories", style=discord.ButtonStyle.danger, row=1)
    async def reset_cat(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        if "ticket_config" in config:
            config["ticket_config"]["categories"] = [] # Clear list
            save_config(config)
        await interaction.response.send_message("🗑️ **All Categories Cleared!** Please add new ones or default will be used.", ephemeral=True)

    # Row 3: Setup
    @discord.ui.select(cls=RoleSelect, placeholder="🛡️ Add Staff Role", min_values=1, max_values=1, row=2)
    async def select_role(self, interaction: discord.Interaction, select: RoleSelect):
        config = load_config()
        if "ticket_config" not in config: config["ticket_config"] = {}
        if "staff_roles" not in config["ticket_config"]: config["ticket_config"]["staff_roles"] = []
        
        role_id = select.values[0].id
        if role_id not in config["ticket_config"]["staff_roles"]:
            config["ticket_config"]["staff_roles"].append(role_id)
            save_config(config)
            await interaction.response.send_message(f"✅ Added Staff Role: **{select.values[0].name}**", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Role already added.", ephemeral=True)

    @discord.ui.select(cls=ChannelSelect, channel_types=[discord.ChannelType.category], placeholder="📂 Set Ticket Channel Category", row=3)
    async def select_channel_cat(self, interaction: discord.Interaction, select: ChannelSelect):
        config = load_config()
        if "ticket_config" not in config: config["ticket_config"] = {}
        config["ticket_config"]["category_id"] = select.values[0].id
        save_config(config)
        await interaction.response.send_message(f"✅ Tickets will open in: **{select.values[0].name}**", ephemeral=True)

    # Row 4: SEND PANEL
    @discord.ui.button(label="🚀 SEND PANEL", style=discord.ButtonStyle.success, row=4)
    async def send_panel(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        tc = config.get("ticket_config", {})

        # --- DEFAULT FALLBACK LOGIC ---
        # যদি ইউজার কিছুই সেট না করে থাকে, তবে এই ডিফল্ট ভ্যালুগুলো ব্যবহার হবে
        title = tc.get("title", "🎫 Funny Bot Support")
        desc = tc.get("description", "Click the dropdown below to open a ticket.")
        footer = tc.get("footer", "Powered by Funny Bot")
        
        # Default Images
        image = tc.get("image", "https://media.tenor.com/7b2e6X2s-38AAAAC/discord-ticket.gif")
        thumb = tc.get("thumbnail", "https://cdn-icons-png.flaticon.com/512/4542/4542173.png")
        
        # Default Color (Blurple if not set)
        color_val = int(tc.get("color", "#5865F2").replace("#", ""), 16)

        # Default Categories
        categories = tc.get("categories", [])
        if not categories:
            categories = [
                {"label": "Claim", "emoji": "🎁", "description": "Claim rewards", "value": "Claim"},
                {"label": "Buy", "emoji": "🛒", "description": "Purchase items", "value": "Buy"},
                {"label": "Report", "emoji": "⚠️", "description": "Report issues", "value": "Report"}
            ]

        # Embed Generate
        embed = discord.Embed(title=title, description=desc, color=color_val)
        embed.set_image(url=image)
        embed.set_thumbnail(url=thumb)
        embed.set_footer(text=footer)

        await interaction.channel.send(embed=embed, view=TicketView(categories))
        await interaction.response.send_message("✅ **Ticket Panel Sent Successfully!**", ephemeral=True)

# ================= 4. MAIN COMMAND =================

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ticket_dashboard", description="🛠️ Open the Master Ticket Dashboard")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_dashboard(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎛️ Ticket Master Dashboard",
            description=(
                "Customize everything from here!\n"
                "• **Edit Text:** Change Title, Description.\n"
                "• **Edit Visuals:** Change GIF, Thumbnail, Color.\n"
                "• **Add Category:** Create your own buttons.\n"
                "• **Send Panel:** Finally send the panel to this channel."
            ),
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, view=DashboardView(), ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
            
