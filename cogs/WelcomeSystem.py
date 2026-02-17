import discord
from discord.ext import commands
from discord import app_commands, ui
from easy_pil import Editor, load_image_async, Font
import os
from io import BytesIO

# utils থেকে আপনার কনফিগ ফাংশনগুলো
from utils import load_config, save_config, get_theme_color

# ================= 1. MODALS (মেসেজ এবং ছবি এডিট) =================

class MessageModal(ui.Modal, title="📝 Edit Welcome Message"):
    msg = ui.TextInput(
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

class BackgroundModal(ui.Modal, title="🖼️ Set Background Image"):
    url = ui.TextInput(
        label="Image URL (Link)", 
        placeholder="https://imgur.com/...", 
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # URL ভ্যালিডেশন (বেসিক)
        if not self.url.value.startswith("http"):
             return await interaction.response.send_message("❌ Invalid URL! Please provide a direct image link.", ephemeral=True)

        config = load_config()
        if "welcome_settings" not in config: config["welcome_settings"] = {}
        
        config["welcome_settings"]["image_url"] = self.url.value
        save_config(config)
        await interaction.response.send_message(f"✅ **Background Image Updated!**", ephemeral=True)

# ================= 2. CHANNEL SELECT (ফিক্সড ভার্সন) =================

class ChannelSelectView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.select(
        placeholder="📢 Select a Channel...",
        cls=ui.ChannelSelect,
        channel_types=[discord.ChannelType.text, discord.ChannelType.news],
        min_values=1,
        max_values=1
    )
    async def select_channel(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        config = load_config()
        if "welcome_settings" not in config: config["welcome_settings"] = {}
        
        channel = select.values[0] # সিলেক্ট করা চ্যানেল অবজেক্ট
        
        config["welcome_settings"]["channel_id"] = channel.id
        config["welcome_settings"]["enabled"] = True 
        save_config(config)
        
        await interaction.response.send_message(f"✅ Welcome Channel set to {channel.mention} and System **ON**!", ephemeral=True)

# ================= 3. MAIN DASHBOARD (বাটন প্যানেল) =================

class WelcomeDashboard(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Set Channel", style=discord.ButtonStyle.success, emoji="📢", row=0)
    async def set_channel(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("👇 **Select the channel below:**", view=ChannelSelectView(), ephemeral=True)

    @ui.button(label="Edit Message", style=discord.ButtonStyle.primary, emoji="📝", row=0)
    async def edit_message(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(MessageModal())

    @ui.button(label="Background", style=discord.ButtonStyle.secondary, emoji="🖼️", row=0)
    async def set_background(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(BackgroundModal())

    @ui.button(label="Test / Preview", style=discord.ButtonStyle.secondary, emoji="🧪", row=1)
    async def test_welcome(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True) # টাইমআউট এড়াতে
        
        cog = interaction.client.get_cog("WelcomeSystem")
        if cog:
            # টেস্ট মোডে কল করা হচ্ছে
            await cog.send_welcome_card(interaction.user, interaction.channel, is_test=True, interaction=interaction)
        else:
            await interaction.followup.send("❌ System Error: Cog not found!", ephemeral=True)

    @ui.button(label="ON / OFF", style=discord.ButtonStyle.danger, emoji="🔌", row=1)
    async def toggle_system(self, interaction: discord.Interaction, button: ui.Button):
        config = load_config()
        if "welcome_settings" not in config: config["welcome_settings"] = {}
        
        current = config["welcome_settings"].get("enabled", False)
        new_state = not current
        config["welcome_settings"]["enabled"] = new_state
        save_config(config)
        
        status = "🟢 Enabled" if new_state else "🔴 Disabled"
        await interaction.response.send_message(f"System is now **{status}**", ephemeral=True)

# ================= 4. SYSTEM LOGIC (ইমেজ জেনারেটর) =================

class WelcomeSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def generate_image(self, member, bg_url):
        # ডিফল্ট ব্যাকগ্রাউন্ড যদি ইউজার কিছু সেট না করে
        default_bg = "https://img.freepik.com/free-vector/abstract-blue-geometric-shapes-background_1035-17545.jpg"
        
        if not bg_url:
            bg_url = default_bg

        try:
            background = Editor(await load_image_async(bg_url)).resize((900, 400))
        except:
            # যদি লিংক কাজ না করে, ডিফল্ট লোড হবে
            background = Editor(await load_image_async(default_bg)).resize((900, 400))

        # প্রোফাইল পিকচার
        try:
            profile_image = await load_image_async(member.display_avatar.url)
            profile = Editor(profile_image).resize((200, 200)).circle_image()
            
            # ব্যাকগ্রাউন্ডে পেস্ট করা
            background.paste(profile, (350, 50))
            background.ellipse((350, 50), 200, 200, outline="white", stroke_width=5)
        except:
            pass # প্রোফাইল লোড না হলে স্কিপ করবে

        # ফন্ট লোড (ডিফল্ট বা কাস্টম)
        # easy_pil এর ডিফল্ট ফন্ট ব্যবহার করা হচ্ছে নিরাপদ থাকার জন্য
        try:
            font_large = Font.poppins(size=50, variant="bold")
            font_small = Font.poppins(size=30, variant="light")
        except:
            font_large = Font.montserrat(size=50, variant="bold")
            font_small = Font.montserrat(size=30, variant="light")

        # টেক্সট বসানো
        background.text((450, 280), "WELCOME", color="white", font=font_large, align="center")
        background.text((450, 340), f"{member.name}", color="#00ffcc", font=font_small, align="center")

        # বাইট-এ কনভার্ট করে রিটার্ন
        return discord.File(fp=background.image_bytes, filename="welcome.jpg")

    async def send_welcome_card(self, member, channel, is_test=False, interaction=None):
        config = load_config()
        ws = config.get("welcome_settings", {})
        
        # মেসেজ ফরম্যাটিং
        raw_msg = ws.get("message", "Welcome {member} to {server}!")
        msg_content = raw_msg.replace("{member}", member.mention)\
                             .replace("{server}", member.guild.name)\
                             .replace("{count}", str(member.guild.member_count))

        # ইমেজ জেনারেট
        try:
            file = await self.generate_image(member, ws.get("image_url"))
        except Exception as e:
            print(f"Image Gen Error: {e}")
            file = None

        # এমবেড তৈরি
        color = get_theme_color(member.guild.id)
        embed = discord.Embed(description=msg_content, color=color)
        
        if file:
            embed.set_image(url="attachment://welcome.jpg")
        
        embed.set_footer(text=f"Member #{member.guild.member_count}")

        # পাঠানো (টেস্ট বা রিয়েল)
        if is_test and interaction:
            # প্রিভিউ (Ephemeral)
            if file:
                await interaction.followup.send(file=file, embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            # রিয়েল চ্যানেল
            if file:
                await channel.send(content=member.mention, file=file, embed=embed)
            else:
                await channel.send(content=member.mention, embed=embed)

    # --- Listener ---
    @commands.Cog.listener()
    async def on_member_join(self, member):
        config = load_config()
        ws = config.get("welcome_settings", {})
        
        # ১. ফিচার অন আছে কিনা চেক
        if not ws.get("enabled"): return
        
        # ২. চ্যানেল আইডি ভ্যালিড কিনা চেক
        channel_id = ws.get("channel_id")
        if not channel_id: return
        
        channel = member.guild.get_channel(channel_id)
        if channel:
            await self.send_welcome_card(member, channel)

    # --- Setup Command ---
    @app_commands.command(name="welcome_setup", description="🛠️ Open Welcome System Dashboard")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_setup(self, interaction: discord.Interaction):
        config = load_config()
        ws = config.get("welcome_settings", {})
        
        status = "🟢 ON" if ws.get("enabled") else "🔴 OFF"
        ch_id = ws.get('channel_id')
        ch_mention = f"<#{ch_id}>" if ch_id else "Not Set"
        
        embed = discord.Embed(
            title="👋 Welcome System Setup",
            description=f"Configure your server's welcome messages and images.\n\n"
                        f"• **Status:** {status}\n"
                        f"• **Channel:** {ch_mention}\n"
                        f"• **Message:** {ws.get('message', 'Default')[:50]}...",
            color=get_theme_color(interaction.guild.id)
        )
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        await interaction.response.send_message(embed=embed, view=WelcomeDashboard())

async def setup(bot):
    await bot.add_cog(WelcomeSystem(bot))
    
