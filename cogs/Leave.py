import discord
from discord.ext import commands
from discord import app_commands, ui
from easy_pil import Editor, load_image_async, Font
import os
from io import BytesIO

# utils থেকে কনফিগ ফাংশন
from utils import load_config, save_config

# ================= 1. MODALS (মেসেজ এবং ছবি এডিট) =================

class LeaveMessageModal(ui.Modal, title="📝 Edit Goodbye Message"):
    msg = ui.TextInput(
        label="New Message", 
        style=discord.TextStyle.paragraph, 
        placeholder="Goodbye {member}! We will miss you.", 
        default="Goodbye {member}! We hope to see you again soon. You were member #{count}",
        required=True, 
        max_length=1000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        if "leave_settings" not in config: config["leave_settings"] = {}
        
        config["leave_settings"]["message"] = self.msg.value
        save_config(config)
        await interaction.response.send_message(f"✅ **Goodbye Message Updated!**\nPreview:\n{self.msg.value}", ephemeral=True)

class LeaveBackgroundModal(ui.Modal, title="🖼️ Set Background Image"):
    url = ui.TextInput(
        label="Image URL (Link)", 
        placeholder="https://imgur.com/...", 
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # URL ভ্যালিডেশন
        if not self.url.value.startswith("http"):
             return await interaction.response.send_message("❌ Invalid URL! Please provide a direct image link.", ephemeral=True)

        config = load_config()
        if "leave_settings" not in config: config["leave_settings"] = {}
        
        config["leave_settings"]["image_url"] = self.url.value
        save_config(config)
        await interaction.response.send_message(f"✅ **Background Image Updated!**", ephemeral=True)

# ================= 2. CHANNEL SELECT (ফিক্সড ভার্সন) =================

class LeaveChannelSelectView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.select(
        placeholder="📢 Select Leave Channel...",
        cls=ui.ChannelSelect,
        channel_types=[discord.ChannelType.text, discord.ChannelType.news],
        min_values=1,
        max_values=1
    )
    async def select_channel(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        config = load_config()
        if "leave_settings" not in config: config["leave_settings"] = {}
        
        channel = select.values[0] # সিলেক্ট করা চ্যানেল
        
        config["leave_settings"]["channel_id"] = channel.id
        config["leave_settings"]["enabled"] = True 
        save_config(config)
        
        await interaction.response.send_message(f"✅ Leave Channel set to {channel.mention} and System **ON**!", ephemeral=True)

# ================= 3. MAIN DASHBOARD (বাটন প্যানেল) =================

class LeaveDashboard(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Set Channel", style=discord.ButtonStyle.success, emoji="📢", row=0)
    async def set_channel(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("👇 **Select the channel below:**", view=LeaveChannelSelectView(), ephemeral=True)

    @ui.button(label="Edit Message", style=discord.ButtonStyle.primary, emoji="📝", row=0)
    async def edit_message(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(LeaveMessageModal())

    @ui.button(label="Background", style=discord.ButtonStyle.secondary, emoji="🖼️", row=0)
    async def set_background(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(LeaveBackgroundModal())

    @ui.button(label="Test / Preview", style=discord.ButtonStyle.secondary, emoji="🧪", row=1)
    async def test_leave(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        cog = interaction.client.get_cog("LeaveSystem")
        if cog:
            # টেস্ট মোড
            await cog.send_leave_card(interaction.user, interaction.channel, is_test=True, interaction=interaction)
        else:
            await interaction.followup.send("❌ Error: Cog not found!", ephemeral=True)

    @ui.button(label="ON / OFF", style=discord.ButtonStyle.danger, emoji="🔌", row=1)
    async def toggle_system(self, interaction: discord.Interaction, button: ui.Button):
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
        # ডিফল্ট ব্যাকগ্রাউন্ড (Red/Goodbye Theme)
        default_bg = "https://img.freepik.com/free-vector/abstract-red-geometric-shapes-background_1035-17546.jpg"
        
        if not bg_url:
            bg_url = default_bg

        try:
            background = Editor(await load_image_async(bg_url)).resize((900, 400))
        except:
            # কাস্টম লিংক কাজ না করলে ডিফল্ট
            background = Editor(await load_image_async(default_bg)).resize((900, 400))

        # প্রোফাইল পিকচার
        try:
            profile_image = await load_image_async(member.display_avatar.url)
            profile = Editor(profile_image).resize((200, 200)).circle_image()
            
            background.paste(profile, (350, 50))
            background.ellipse((350, 50), 200, 200, outline="white", stroke_width=5)
        except:
            pass 

        # ফন্ট লোড
        try:
            font_large = Font.poppins(size=50, variant="bold")
            font_small = Font.poppins(size=30, variant="light")
        except:
            font_large = Font.montserrat(size=50, variant="bold")
            font_small = Font.montserrat(size=30, variant="light")

        # টেক্সট (Goodbye)
        background.text((450, 280), "GOODBYE", color="white", font=font_large, align="center")
        background.text((450, 340), f"{member.name}", color="#ffcccc", font=font_small, align="center")

        return discord.File(fp=background.image_bytes, filename="leave.jpg")

    async def send_leave_card(self, member, channel, is_test=False, interaction=None):
        config = load_config()
        ls = config.get("leave_settings", {})
        
        # মেসেজ ফরম্যাটিং
        raw_msg = ls.get("message", "Goodbye {member}! We will miss you.")
        msg_content = raw_msg.replace("{member}", member.mention)\
                             .replace("{server}", member.guild.name)\
                             .replace("{count}", str(member.guild.member_count))

        # ইমেজ জেনারেট
        try:
            file = await self.generate_image(member, ls.get("image_url"))
        except Exception as e:
            print(f"Leave Image Error: {e}")
            file = None

        # এমবেড (Red Color for Leave)
        embed = discord.Embed(description=msg_content, color=discord.Color.red())
        
        if file:
            embed.set_image(url="attachment://leave.jpg")
        
        embed.set_footer(text=f"Remaining Members: {member.guild.member_count}")

        # পাঠানো (টেস্ট বা রিয়েল)
        if is_test and interaction:
            if file:
                await interaction.followup.send(file=file, embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            if file:
                await channel.send(content=member.mention, file=file, embed=embed)
            else:
                await channel.send(content=member.mention, embed=embed)

    # --- Listener: Member Remove ---
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        config = load_config()
        ls = config.get("leave_settings", {})
        
        # ১. সিস্টেম অন আছে কিনা
        if not ls.get("enabled"): return
        
        # ২. চ্যানেল সেট আছে কিনা
        channel_id = ls.get("channel_id")
        if not channel_id: return
        
        channel = member.guild.get_channel(channel_id)
        if channel:
            await self.send_leave_card(member, channel)

    # --- Setup Command ---
    @app_commands.command(name="leave_setup", description="🛠️ Open Goodbye System Dashboard")
    @app_commands.checks.has_permissions(administrator=True)
    async def leave_setup(self, interaction: discord.Interaction):
        config = load_config()
        ls = config.get("leave_settings", {})
        
        status = "🟢 ON" if ls.get("enabled") else "🔴 OFF"
        ch_id = ls.get('channel_id')
        ch_mention = f"<#{ch_id}>" if ch_id else "Not Set"
        
        embed = discord.Embed(
            title="👋 Goodbye System Setup",
            description=f"Configure goodbye messages.\n\n"
                        f"• **Status:** {status}\n"
                        f"• **Channel:** {ch_mention}\n"
                        f"• **Message:** {ls.get('message', 'Default')[:50]}...",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, view=LeaveDashboard())

async def setup(bot):
    await bot.add_cog(LeaveSystem(bot))
        
