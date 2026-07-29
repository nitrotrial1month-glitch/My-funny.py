import discord
from discord.ext import commands
from discord import app_commands, ui
from easy_pil import Editor, load_image_async, Font, Canvas
import os
from io import BytesIO

# utils থেকে আপনার কনফিগ ফাংশনগুলো (আগের মতোই রাখা হয়েছে)
from utils import load_config, save_config, get_theme_color

# ================= 0. SMART MEDIA ENGINE (নতুন ফাংশন) =================
# এই ফাংশনটি চেক করবে লিংকটি ভিডিও নাকি অ্যানিমেটেড GIF
def is_animated_media(url):
    if not url:
        return False
    val = url.lower()
    return any(ext in val for ext in ['.gif', '.mp4', '.mov', '.webm'])

# ================= 1. MODALS (প্রিমিয়াম লুক আপডেট) =================

class MessageModal(ui.Modal, title="✨ Custom Greeting Text"):
    msg = ui.TextInput(
        label="Enter your personalized message", 
        style=discord.TextStyle.paragraph, 
        placeholder="Welcome to the elite club, {member}!", 
        default="Welcome {member}! You are the #{count} member of {server}.",
        required=True, 
        max_length=1000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        guild_id = str(interaction.guild.id) 
        
        if guild_id not in config: config[guild_id] = {}
        if "welcome_settings" not in config[guild_id]: config[guild_id]["welcome_settings"] = {}
        
        config[guild_id]["welcome_settings"]["message"] = self.msg.value
        save_config(config)
        await interaction.response.send_message(f"🌟 **Greeting text updated perfectly!**\nPreview:\n{self.msg.value}", ephemeral=True)

class BackgroundModal(ui.Modal, title="🌌 Upload Visual Media"):
    url = ui.TextInput(
        label="Direct Link (.png, .jpg, .gif, .mp4)", 
        placeholder="https://example.com/media.gif", 
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not self.url.value.startswith("http"):
             return await interaction.response.send_message("⚠️ Error: Please provide a valid direct link.", ephemeral=True)

        config = load_config()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in config: config[guild_id] = {}
        if "welcome_settings" not in config[guild_id]: config[guild_id]["welcome_settings"] = {}
        
        config[guild_id]["welcome_settings"]["image_url"] = self.url.value
        save_config(config)
        
        # স্মার্ট রেসপন্স (ভিডিও নাকি ইমেজ তার ওপর ভিত্তি করে মেসেজ)
        if is_animated_media(self.url.value):
            msg = "🎬 **Animated Media Saved!**\n*(Since it's a Video/GIF, it will play directly without text overlays.)*"
        else:
            msg = "🖼️ **Static Image Saved!**\n*(The bot will elegantly draw the welcome text on this image.)*"
            
        await interaction.response.send_message(msg, ephemeral=True)

# ================= 2. CHANNEL SELECT (ডিজাইন আপডেট) =================

class ChannelSelectView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.select(
        placeholder="📍 Select Arrival Lounge...",
        cls=ui.ChannelSelect,
        channel_types=[discord.ChannelType.text, discord.ChannelType.news],
        min_values=1,
        max_values=1
    )
    async def select_channel(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        config = load_config()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in config: config[guild_id] = {}
        if "welcome_settings" not in config[guild_id]: config[guild_id]["welcome_settings"] = {}
        
        channel = select.values[0] 
        
        config[guild_id]["welcome_settings"]["channel_id"] = channel.id
        config[guild_id]["welcome_settings"]["enabled"] = True 
        save_config(config)
        
        await interaction.response.send_message(f"✅ VIP Arrivals will now be announced in {channel.mention}!", ephemeral=True)

# ================= 3. MAIN DASHBOARD (বাটন প্যানেল আপডেট) =================

class WelcomeDashboard(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Arrival Channel", style=discord.ButtonStyle.secondary, emoji="📍", row=0)
    async def set_channel(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("👇 **Where should we drop the welcome card?**", view=ChannelSelectView(), ephemeral=True)

    @ui.button(label="Greeting Text", style=discord.ButtonStyle.secondary, emoji="📝", row=0)
    async def edit_message(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(MessageModal())

    @ui.button(label="Visual Media", style=discord.ButtonStyle.secondary, emoji="🌌", row=0)
    async def set_background(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(BackgroundModal())

    @ui.button(label="Run Simulation", style=discord.ButtonStyle.success, emoji="🚀", row=1)
    async def test_welcome(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True) 
        
        cog = interaction.client.get_cog("WelcomeSystem")
        if cog:
            await cog.send_welcome_card(interaction.user, interaction.channel, is_test=True, interaction=interaction)
        else:
            await interaction.followup.send("⚠️ System Error: Cog not found!", ephemeral=True)

    @ui.button(label="Power Switch", style=discord.ButtonStyle.danger, emoji="⚡", row=1)
    async def toggle_system(self, interaction: discord.Interaction, button: ui.Button):
        config = load_config()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in config: config[guild_id] = {}
        if "welcome_settings" not in config[guild_id]: config[guild_id]["welcome_settings"] = {}
        
        current = config[guild_id]["welcome_settings"].get("enabled", False)
        new_state = not current
        config[guild_id]["welcome_settings"]["enabled"] = new_state
        save_config(config)
        
        status = "🟢 ONLINE & ACTIVE" if new_state else "🔴 OFFLINE"
        await interaction.response.send_message(f"System Status: **{status}**", ephemeral=True)

# ================= 4. SYSTEM LOGIC (স্মার্ট রেন্ডারার) =================

class WelcomeSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def generate_image(self, member, bg_url):
        # Premium Dark Abstract Background (সাদা লেখার জন্য পারফেক্ট)
        default_bg = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1000&auto=format&fit=crop"
        
        try:
            if bg_url:
                background = Editor(await load_image_async(bg_url)).resize((900, 400))
            else:
                background = Editor(await load_image_async(default_bg)).resize((900, 400))
        except:
            try:
                background = Editor(await load_image_async(default_bg)).resize((900, 400))
            except:
                # ফলব্যাক হিসেবে একটি ডার্ক সলিড ক্যানভাস
                background = Editor(Canvas((900, 400), color="#0b0e14"))

        # Profile Picture Setup
        try:
            raw_profile = await load_image_async(member.display_avatar.url)
            # নাইট্রো এভাটার ফ্রিজ করার জন্য RGBA কনভার্ট
            raw_profile = raw_profile.convert("RGBA") 
            profile = Editor(raw_profile).resize((200, 200)).circle_image()
            
            background.paste(profile, (350, 50))
            # গোল্ডেন রঙের প্রিমিয়াম বর্ডার 
            background.ellipse((350, 50), 200, 200, outline="#FFD700", stroke_width=6)
        except:
            pass 

        # Font Setup
        try:
            font_large = Font.poppins(size=55, variant="bold")
            font_small = Font.poppins(size=32, variant="light")
        except:
            font_large = Font.montserrat(size=55, variant="bold")
            font_small = Font.montserrat(size=32, variant="light")

        # Paste Texts (সাদা এবং গোল্ডেন থিম)
        background.text((450, 275), "WELCOME", color="white", font=font_large, align="center")
        background.text((450, 340), f"@{member.name}", color="#FFD700", font=font_small, align="center")

        return discord.File(fp=background.image_bytes, filename="premium_welcome.png")

    async def send_welcome_card(self, member, channel, is_test=False, interaction=None):
        config = load_config()
        guild_id = str(member.guild.id)
        
        ws = config.get(guild_id, {}).get("welcome_settings", {})
        
        raw_msg = ws.get("message", "Welcome {member} to {server}! You are member #{count}")
        msg_content = raw_msg.replace("{member}", member.mention)\
                             .replace("{server}", f"**{member.guild.name}**")\
                             .replace("{count}", str(member.guild.member_count))

        bg_url = ws.get("image_url")
        
        # আপনার utils এর থিম কালার ঠিক রাখা হয়েছে
        color = get_theme_color(member.guild.id)
        embed = discord.Embed(description=msg_content, color=color)
        embed.set_footer(text=f"User ID: {member.id} • #{member.guild.member_count}")

        file = None
        content_msg = member.mention

        # 🔥 SMART MEDIA LOGIC 🔥
        if is_animated_media(bg_url):
            # যদি লিংকটি ভিডিও বা GIF হয়, তবে ইমেজ জেনারেট না করে সরাসরি পাঠানো হবে।
            if ".gif" in bg_url.lower():
                embed.set_image(url=bg_url)
            else:
                # Video (mp4) এর ক্ষেত্রে মেসেজে দিলে ডিসকর্ড নিজে থেকে প্লে করবে।
                content_msg = f"{member.mention}\n{bg_url}"
        else:
            # নরমাল ইমেজের ক্ষেত্রে ওয়েলকাম কার্ড জেনারেট হবে।
            try:
                file = await self.generate_image(member, bg_url)
                embed.set_image(url="attachment://premium_welcome.png")
            except Exception as e:
                print(f"Image Gen Error: {e}")

        # মেসেজ পাঠানো (টেস্ট বা রিয়েল)
        if is_test and interaction:
            if file:
                await interaction.followup.send(content=content_msg, file=file, embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(content=content_msg, embed=embed, ephemeral=True)
        else:
            if file:
                await channel.send(content=content_msg, file=file, embed=embed)
            else:
                await channel.send(content=content_msg, embed=embed)

    # --- Listener ---
    @commands.Cog.listener()
    async def on_member_join(self, member):
        config = load_config()
        guild_id = str(member.guild.id)
        ws = config.get(guild_id, {}).get("welcome_settings", {})
        
        if not ws.get("enabled"): return
        
        channel_id = ws.get("channel_id")
        if not channel_id: return
        
        channel = member.guild.get_channel(channel_id)
        if channel:
            await self.send_welcome_card(member, channel)

    # --- Setup Command ---
    @app_commands.command(name="welcome_setup", description="🌟 Open the Premium Welcome System Dashboard")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_setup(self, interaction: discord.Interaction):
        config = load_config()
        guild_id = str(interaction.guild.id)
        ws = config.get(guild_id, {}).get("welcome_settings", {})
        
        status = "🟢 **ONLINE**" if ws.get("enabled") else "🔴 **OFFLINE**"
        ch_id = ws.get('channel_id')
        ch_mention = f"<#{ch_id}>" if ch_id else "`Not Set`"
        msg_preview = ws.get('message', 'Default')[:40] + "..."
        media_status = "🎬 Animated/Video" if is_animated_media(ws.get('image_url')) else "🖼️ Static Card"
        
        # প্রিমিয়াম এমবেড লুক
        embed = discord.Embed(
            title="🌟 Server Arrival Dashboard",
            description=(
                "Welcome to the premium configuration lounge.\n\n"
                "**📊 System Diagnostics:**\n"
                f"> ⚡ **Core Status:** {status}\n"
                f"> 📍 **Channel:** {ch_mention}\n"
                f"> 📝 **Message:** `{msg_preview}`\n"
                f"> 🌌 **Media Mode:** `{media_status}`"
            ),
            color=get_theme_color(interaction.guild.id)
        )
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        
        await interaction.response.send_message(embed=embed, view=WelcomeDashboard())

async def setup(bot):
    await bot.add_cog(WelcomeSystem(bot))
            
