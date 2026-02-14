import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput
import datetime
from utils import get_theme_color

# ================= 1. ANNOUNCEMENT MODAL (স্ল্যাশ কমান্ডের জন্য ফর্ম) =================
class AnnounceModal(Modal, title="📢 Create Stylish Announcement"):
    a_title = TextInput(label="Announcement Title", placeholder="Enter the headline here...", required=True)
    a_desc = TextInput(label="Message Content", style=discord.TextStyle.paragraph, placeholder="Write your detailed message...", required=True)
    a_image = TextInput(label="Large Image URL (Optional)", placeholder="https://image-link.com/photo.png", required=False)
    a_thumb = TextInput(label="Small Thumbnail URL (Optional)", placeholder="https://icon-link.com/icon.png", required=False)

    def __init__(self, ping_role=None):
        super().__init__()
        self.ping_role = ping_role

    async def on_submit(self, interaction: discord.Interaction):
        # এম্বেড ডিজাইন
        embed = discord.Embed(
            title=f"📢 {self.a_title.value}",
            description=self.a_desc.value,
            color=get_theme_color(interaction.guild.id), # আপনার utils থেকে থিম কালার
            timestamp=datetime.datetime.now()
        )

        if self.a_image.value:
            embed.set_image(url=self.a_image.value)
        if self.a_thumb.value:
            embed.set_thumbnail(url=self.a_thumb.value)

        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text="Funny Bot Announcement System", icon_url=interaction.client.user.display_avatar.url)

        # পিং লজিক
        content = self.ping_role.mention if self.ping_role else None

        await interaction.channel.send(content=content, embed=embed)
        await interaction.response.send_message("✅ Announcement sent successfully!", ephemeral=True)

# ================= 2. MAIN COG CLASS =================
class Announcement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="announce", description="📢 Send a professional announcement using a stylish form")
    @app_commands.describe(mention="Select a role to ping (Optional)")
    @app_commands.checks.has_permissions(administrator=True)
    async def announce(self, interaction: discord.Interaction, mention: discord.Role = None):
        """Slash Command: Opens a form for the announcement"""
        await interaction.response.send_modal(AnnounceModal(ping_role=mention))

    # হাইব্রিড সাপোর্ট: প্রেফিক্স কমান্ডের জন্য
    @commands.command(name="say", description="Send a simple announcement via prefix")
    @commands.has_permissions(manage_messages=True)
    async def say(self, ctx, *, message: str):
        """Prefix Command: Simple text announcement"""
        embed = discord.Embed(
            description=message,
            color=get_theme_color(ctx.guild.id),
            timestamp=datetime.datetime.now()
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text="Funny Bot Quick Announce")
        
        await ctx.message.delete()
        await ctx.send(embed=embed)

    # এরর হ্যান্ডলিং
    @announce.error
    async def announce_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ Only Admins/Managers can use this command!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Announcement(bot))
  
