import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput, ChannelSelect
from easy_pil import Editor, load_image_async, Font
import os
from utils import load_config, save_config, get_theme_color

# ================= 1. MODALS (মেসেজ এবং ছবি এডিট) =================

class LeaveMessageModal(Modal, title="📝 Edit Goodbye Message"):
    msg = TextInput(
        label="New Message", 
        style=discord.TextStyle.paragraph, 
        placeholder="Goodbye {member}! We will miss you.", 
        default="Goodbye {member}! We hope to see you again soon.",
        required=True, 
        max_length=1000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        if "leave_settings" not in config: config["leave_settings"] = {}
        
        config["leave_settings"]["message"] = self.msg.value
        save_config(config)
        await interaction.response.send_message(f"✅ **Message Updated!**\nPreview:\n{self.msg.value}", ephemeral=True)

class LeaveBackgroundModal(Modal, title="🖼️ Set Background Image"):
    url = TextInput(
        label="Image URL (Link)", 
        placeholder="https://imgur.com/...", 
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        if "leave_settings" not in config: config["leave_settings"] = {}
        
        config["leave_settings"]["image_url"] = self.url.value
        save_config(config)
        await interaction.response.send_message(f"✅ **Background Image Updated!**", ephemeral=True)

# ================= 2. CHANNEL SELECT (ফিক্সড ভার্সন) =================

class LeaveChannelSelectMenu(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="📢 Select Leave Channel...",
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        config = load_config()
        if "leave_settings" not in config: config["leave_settings"] = {}
        
        channel = self.values[0]
        config["leave_settings"]["channel_id"] = channel.id
        config["leave_settings"]["enabled"] = True 
        save_config(config)
        
        await interaction.response.send_message(f"✅ Leave Channel set to {channel.mention} and System **ON**!", ephemeral=True)

class LeaveChannelView(View):
    def __init__(self):
        super().__init__()
        self.add_item(LeaveChannelSelectMenu())

# ================= 3. MAIN DASHBOARD (বাটন প্যানেল) =================

class LeaveDashboard(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Set Channel", style=discord.ButtonStyle.success, emoji="📢", row=0)
    async def set_channel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("👇 **Select the channel below:**", view=LeaveChannelView(), ephemeral=True)

    @discord.ui.button(label="Edit Message", style=discord.ButtonStyle.primary, emoji="📝", row=0)
    async def edit_message(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(LeaveMessageModal())

    @discord.ui.button(label="Background", style=discord.ButtonStyle.secondary, emoji="🖼️", row=0)
    async def set_background(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(LeaveBackgroundModal())

    @discord.ui.button(label="Test / Preview", style=discord.ButtonStyle.secondary, emoji="🧪", row=1)
    async def test_leave(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("⏳ Generating preview...", ephemeral=True)
        cog = interaction.client.get_cog("LeaveSystem")
        if cog:
            await cog.send_leave_card(interaction.user, interaction.channel, is_test=True)

    @discord.ui.button(label="ON / OFF", style=discord.ButtonStyle.danger, emoji="🔌", row=1)
    async def toggle_system(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        if "leave_settings" not in config: config["leave_settings"] = {}
        
        current = config["leave_settings"].get("enabled", False)
        new_state = not current
        config["leave_settings"]["enabled"] = new_state
        save_config(config)
        
        status = "🟢 Enabled" if new_state else "🔴 Disabled"
        await interaction.response.send_message(f"Leave System is now **{status}**", ephemeral=True)

# ================= 4. SYSTEM LOGIC (ইমেজ জেনারেটর) =================

class LeaveSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def generate_image(self, member, bg_url):
        # ডিফল্ট ব্যাকগ্রাউন্ড (একটু লালচে ভাব)
        if not bg_url: 
            bg_url = "https://img.freepik.com/free-vector/abstract-red-geometric-shapes-background_1035-17546.jpg"

        background = Editor(await load_image_async(bg_url)).resize((900, 400))
        profile_image = await load_image_async(member.display_avatar.url)
        
        profile = Editor(profile_image).resize((200, 200)).circle_image()
        poppins = Font.poppins(size=50, variant="bold")
        poppins_small = Font.poppins(size=30, variant="light")

        background.paste(profile, (350, 50))
        background.ellipse((350, 50), 200, 200, outline="white", stroke_width=5)

        # এখানে টেক্সট হবে GOODBYE
        background.text((450, 280), "GOODBYE", color="white", font=poppins, align="center")
        background.text((450, 340), f"{member.name}", color="#ffcccc", font=poppins_small, align="center")

        return discord.File(fp=background.image_bytes, filename="leave.jpg")

    async def send_leave_card(self, member, channel, is_test=False):
        config = load_config()
        ls = config.get("leave_settings", {})
        msg = ls.get("message", "Goodbye {member}! We will miss you.")
        msg = msg.format(member=member.mention, server=member.guild.name, count=member.guild.member_count)

        try:
            file = await self.generate_image(member, ls.get("image_url"))
            # লিভ মেসেজে সাধারণত লাল বা কমলা কালার ভালো লাগে
            color = discord.Color.red() 
            
            embed = discord.Embed(description=msg, color=color)
            embed.set_image(url="attachment://leave.jpg")
            embed.set_footer(text=f"Remaining Members: {member.guild.member_count}")

            if is_test:
                await channel.send(file=file, embed=embed)
            else:
                await channel.send(content=member.mention, file=file, embed=embed)
        except Exception as e:
            print(f"Leave Error: {e}")
            await channel.send(msg)

    # --- Listener: Member Remove (লিভ ইভেন্ট) ---
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        config = load_config()
        ls = config.get("leave_settings", {})
        
        if ls.get("enabled") and ls.get("channel_id"):
            channel = member.guild.get_channel(ls["channel_id"])
            if channel:
                await self.send_leave_card(member, channel)

    # --- Command: Setup Dashboard ---
    @app_commands.command(name="leave_setup", description="🛠️ Open Goodbye System Dashboard")
    @app_commands.checks.has_permissions(administrator=True)
    async def leave_setup(self, interaction: discord.Interaction):
        config = load_config()
        ls = config.get("leave_settings", {})
        status = "🟢 ON" if ls.get("enabled") else "🔴 OFF"
        ch = f"<#{ls.get('channel_id')}>" if ls.get('channel_id') else "Not Set"
        
        embed = discord.Embed(
            title="👋 Leave (Goodbye) Setup",
            description=f"Configure goodbye messages when users leave.\n\n• **Status:** {status}\n• **Channel:** {ch}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, view=LeaveDashboard())

async def setup(bot):
    await bot.add_cog(LeaveSystem(bot))
                           
