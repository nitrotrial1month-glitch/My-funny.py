
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput, Select
from easy_pil import Editor, load_image_async, Font
import os
from utils import load_config, save_config, get_theme_color

# ================= 1. MODALS (ইনপুট বক্স) =================

class MessageModal(Modal, title="📝 Edit Welcome Message"):
    msg = TextInput(
        label="New Message", 
        style=discord.TextStyle.paragraph, 
        placeholder="Welcome {member} to {server}!", 
        default="Welcome {member} to {server}! You are member #{count}",
        required=True, 
        max_length=1000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        if "welcome_settings" not in config: config["welcome_settings"] = {}
        
        config["welcome_settings"]["message"] = self.msg.value
        save_config(config)
        await interaction.response.send_message(f"✅ **Message Updated!**\nPreview:\n{self.msg.value}", ephemeral=True)

class BackgroundModal(Modal, title="🖼️ Set Background Image"):
    url = TextInput(
        label="Image URL (Link)", 
        placeholder="https://imgur.com/...", 
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        if "welcome_settings" not in config: config["welcome_settings"] = {}
        
        config["welcome_settings"]["image_url"] = self.url.value
        save_config(config)
        await interaction.response.send_message(f"✅ **Background Image Updated!**", ephemeral=True)

# ================= 2. CHANNEL SELECT (চ্যানেল বাছাই) =================

class ChannelSelect(Select):
    def __init__(self):
        super().__init__(placeholder="📢 Select a Channel...", channel_types=[discord.ChannelType.text])
    
    async def callback(self, interaction: discord.Interaction):
        config = load_config()
        if "welcome_settings" not in config: config["welcome_settings"] = {}
        
        channel = self.values[0]
        config["welcome_settings"]["channel_id"] = channel.id
        config["welcome_settings"]["enabled"] = True # অটোমেটিক অন হবে
        save_config(config)
        
        await interaction.response.send_message(f"✅ Welcome Channel set to {channel.mention} and System **ON**!", ephemeral=True)

class ChannelView(View):
    def __init__(self):
        super().__init__()
        self.add_item(ChannelSelect())

# ================= 3. MAIN DASHBOARD (মেইন প্যানেল) =================

class WelcomeDashboard(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Set Channel", style=discord.ButtonStyle.success, emoji="📢", row=0)
    async def set_channel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("👇 **Select the channel below:**", view=ChannelView(), ephemeral=True)

    @discord.ui.button(label="Edit Message", style=discord.ButtonStyle.primary, emoji="📝", row=0)
    async def edit_message(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(MessageModal())

    @discord.ui.button(label="Background", style=discord.ButtonStyle.secondary, emoji="🖼️", row=0)
    async def set_background(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BackgroundModal())

    @discord.ui.button(label="Test / Preview", style=discord.ButtonStyle.secondary, emoji="🧪", row=1)
    async def test_welcome(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("⏳ Generating preview...", ephemeral=True)
        # Cog থেকে ফাংশন কল করা
        cog = interaction.client.get_cog("WelcomeSystem")
        if cog:
            await cog.send_welcome_card(interaction.user, interaction.channel, is_test=True)

    @discord.ui.button(label="ON / OFF", style=discord.ButtonStyle.danger, emoji="🔌", row=1)
    async def toggle_system(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        if "welcome_settings" not in config: config["welcome_settings"] = {}
        
        current = config["welcome_settings"].get("enabled", False)
        new_state = not current
        config["welcome_settings"]["enabled"] = new_state
        save_config(config)
        
        status = "🟢 Enabled" if new_state else "🔴 Disabled"
        await interaction.response.send_message(f"System is now **{status}**", ephemeral=True)

# ================= 4. SYSTEM LOGIC (মেইন লজিক) =================

class WelcomeSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def generate_image(self, member, bg_url):
        # ডিফল্ট ব্যাকগ্রাউন্ড যদি সেট না থাকে
        if not bg_url: 
            bg_url = "https://img.freepik.com/free-vector/abstract-blue-geometric-shapes-background_1035-17545.jpg"

        background = Editor(await load_image_async(bg_url)).resize((900, 400))
        profile_image = await load_image_async(member.display_avatar.url)
        
        # প্রোফাইল ছবি গোল করা
        profile = Editor(profile_image).resize((200, 200)).circle_image()
        
        # ফন্ট সেটআপ
        poppins = Font.poppins(size=50, variant="bold")
        poppins_small = Font.poppins(size=30, variant="light")

        # ড্রয়িং
        background.paste(profile, (350, 50))
        background.ellipse((350, 50), 200, 200, outline="white", stroke_width=5)

        background.text((450, 280), "WELCOME", color="white", font=poppins, align="center")
        background.text((450, 340), f"{member.name}", color="#00ffcc", font=poppins_small, align="center")

        return discord.File(fp=background.image_bytes, filename="welcome.jpg")

    async def send_welcome_card(self, member, channel, is_test=False):
        config = load_config()
        ws = config.get("welcome_settings", {})

        # মেসেজ ফরম্যাট করা
        msg = ws.get("message", "Welcome {member} to {server}!")
        msg = msg.format(
            member=member.mention, 
            server=member.guild.name, 
            count=member.guild.member_count,
            username=member.name
        )

        try:
            file = await self.generate_image(member, ws.get("image_url"))
            
            # এম্বেড কালার
            color = get_theme_color(member.guild.id)
            embed = discord.Embed(description=msg, color=color)
            embed.set_image(url="attachment://welcome.jpg")
            embed.set_footer(text=f"Member #{member.guild.member_count}")

            if is_test:
                await channel.send(file=file, embed=embed)
            else:
                await channel.send(content=member.mention, file=file, embed=embed)
        except Exception as e:
            print(f"Welcome Error: {e}")
            await channel.send(msg)

    # --- Listener: Member Join ---
    @commands.Cog.listener()
    async def on_member_join(self, member):
        config = load_config()
        ws = config.get("welcome_settings", {})

        if not ws.get("enabled", False): return
        
        channel_id = ws.get("channel_id")
        if not channel_id: return
        
        channel = member.guild.get_channel(channel_id)
        if channel:
            await self.send_welcome_card(member, channel)

    # --- Command: Setup Dashboard ---
    @app_commands.command(name="welcome_setup", description="🛠️ Open Welcome System Dashboard")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_setup(self, interaction: discord.Interaction):
        config = load_config()
        ws = config.get("welcome_settings", {})
        
        status = "🟢 ON" if ws.get("enabled") else "🔴 OFF"
        ch_id = ws.get("channel_id")
        ch_name = f"<#{ch_id}>" if ch_id else "Not Set"
        
        embed = discord.Embed(
            title="👋 Welcome System Dashboard",
            description=(
                f"Use the buttons below to configure the system.\n\n"
                f"**Current Settings:**\n"
                f"• **Status:** {status}\n"
                f"• **Channel:** {ch_name}\n"
                f"• **Message:** `{ws.get('message', 'Default')}`"
            ),
            color=get_theme_color(interaction.guild.id)
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, view=WelcomeDashboard())

async def setup(bot):
    await bot.add_cog(WelcomeSystem(bot))
  
