import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button
import datetime
from utils import get_theme_color

# ================= 1. ANNOUNCEMENT MODAL (ফর্ম) =================
class AnnounceModal(Modal):
    def __init__(self, ping_role=None):
        super().__init__(title="📢 Create Announcement")
        self.ping_role = ping_role

    # ইনপুট ফিল্ডগুলো
    a_title = TextInput(
        label="Headline / Title", 
        placeholder="Enter announcement title...", 
        required=True, 
        max_length=256
    )
    a_desc = TextInput(
        label="Message Content", 
        style=discord.TextStyle.paragraph, 
        placeholder="Write your detailed message here...", 
        required=True, 
        max_length=4000
    )
    a_image = TextInput(
        label="Image URL (Optional)", 
        placeholder="https://example.com/image.png", 
        required=False
    )
    a_footer = TextInput(
        label="Footer Text (Optional)", 
        placeholder="Custom footer text...", 
        required=False,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        # এম্বেড তৈরি করা
        color = get_theme_color(interaction.guild.id)
        
        embed = discord.Embed(
            title=f"📢  {self.a_title.value}",
            description=self.a_desc.value,
            color=color,
            timestamp=datetime.datetime.now()
        )

        # ছবি সেট করা (যদি দেয়)
        if self.a_image.value:
            embed.set_image(url=self.a_image.value)
        
        # ফুটার এবং অথর সেট করা
        footer_text = self.a_footer.value if self.a_footer.value else f"Announcement by {interaction.user.name}"
        embed.set_footer(text=footer_text, icon_url=interaction.client.user.display_avatar.url)
        embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

        # রোল মেনশন লজিক
        content = self.ping_role.mention if self.ping_role else None

        # মেসেজ পাঠানো
        await interaction.response.send_message("✅ Announcement sent!", ephemeral=True)
        await interaction.channel.send(content=content, embed=embed)

# ================= 2. VIEW FOR PREFIX COMMAND (বাটন সিস্টেম) =================
class AnnouncementLauncher(View):
    def __init__(self, role=None):
        super().__init__(timeout=60)
        self.role = role

    @discord.ui.button(label="Click to Create Announcement", style=discord.ButtonStyle.primary, emoji="📝")
    async def launch(self, interaction: discord.Interaction, button: Button):
        # বাটন ক্লিক করলে মোডাল ওপেন হবে
        await interaction.response.send_modal(AnnounceModal(self.role))
        # বাটনটি ডিজেবল করে দেওয়া হবে
        self.stop()
        await interaction.message.delete() # আগের বাটন মেসেজ ডিলিট

# ================= 3. MAIN COG CLASS =================
class Announcement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Hybrid Command: Announce ---
    @commands.hybrid_command(name="announce", description="📢 Create a stylish announcement.")
    @app_commands.describe(role="Select a role to ping (Optional)")
    @commands.has_permissions(manage_messages=True)
    async def announce(self, ctx: commands.Context, role: discord.Role = None):
        """
        Slash usage: /announce [role] -> Opens Form directly
        Prefix usage: !announce [role] -> Sends Button -> Opens Form
        """
        
        # যদি স্ল্যাশ কমান্ড হয়
        if ctx.interaction:
            await ctx.interaction.response.send_modal(AnnounceModal(role))
        
        # যদি প্রেফিক্স কমান্ড হয় (!announce)
        else:
            embed = discord.Embed(
                description="👇 **Click the button below to write your announcement.**",
                color=get_theme_color(ctx.guild.id)
            )
            await ctx.send(embed=embed, view=AnnouncementLauncher(role))

    # --- Simple Say Command (Optional) ---
    @commands.hybrid_command(name="say", description="🗣️ Bot repeats what you say (Simple embed).")
    @commands.has_permissions(manage_messages=True)
    async def say(self, ctx: commands.Context, *, message: str):
        
        embed = discord.Embed(
            description=message,
            color=get_theme_color(ctx.guild.id)
        )
        embed.set_footer(text=f"Sent by {ctx.author.name}")
        
        # অরিজিনাল মেসেজ ডিলিট (শুধু প্রেফিক্সের জন্য)
        try:
            if not ctx.interaction:
                await ctx.message.delete()
        except:
            pass

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Announcement(bot))
    
