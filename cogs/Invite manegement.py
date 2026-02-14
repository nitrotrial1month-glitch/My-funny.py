import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button
import datetime
from utils import load_config, save_config, get_theme_color

# ================= 🎨 CUSTOMIZATION MODAL =================
class InviteMsgModal(Modal, title="🎨 Customize Invite Message"):
    msg_title = TextInput(label="Embed Title", placeholder="e.g. 📥 Welcome to the Server!", required=False)
    msg_desc = TextInput(label="Description", style=discord.TextStyle.paragraph, 
                         placeholder="Use: {member}, {inviter}, {invites}, {server}", required=True)
    msg_image = TextInput(label="GIF / Image URL", placeholder="https://link-to-your-gif.gif", required=False)
    msg_footer = TextInput(label="Footer Text", placeholder="e.g. Join time: {join_time}", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        guild_id = str(interaction.guild.id)
        
        # ডাটা সেভ করা
        config["invite_settings"][guild_id]["template"] = {
            "title": self.msg_title.value,
            "description": self.msg_desc.value,
            "image": self.msg_image.value,
            "footer": self.msg_footer.value
        }
        save_config(config)
        await interaction.response.send_message("✅ Invite template updated successfully!", ephemeral=True)

# ================= 🛡️ DASHBOARD VIEW =================
class InviteDashboard(View):
    @discord.ui.button(label="Edit Message", style=discord.ButtonStyle.primary, emoji="📝")
    async def edit_msg(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(InviteMsgModal())

    @discord.ui.button(label="Toggle System", style=discord.ButtonStyle.success, emoji="⚙️")
    async def toggle(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        guild_id = str(interaction.guild.id)
        current = config["invite_settings"][guild_id].get("enabled", False)
        config["invite_settings"][guild_id]["enabled"] = not current
        save_config(config)
        await interaction.response.send_message(f"✅ System is now **{'ON' if not current else 'OFF'}**", ephemeral=True)

# ================= 🚀 MAIN TRACKER COG =================
class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites = {}

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        config = load_config()
        settings = config.get("invite_settings", {}).get(str(guild.id), {})

        if not settings.get("enabled", False) or not settings.get("log_channel"):
            return

        # ইনভাইটার লজিক (আগের মতোই)
        inviter, total_invites = await self.get_inviter(member) 

        # কাস্টম এম্বেড তৈরি
        tpl = settings.get("template", {})
        join_time = datetime.datetime.now().strftime("%B %d, %Y %I:%M %p")
        
        # প্লেসহোল্ডার রিপ্লেস করা
        desc = tpl.get("description", "").format(
            member=member.mention,
            inviter=inviter.mention if inviter else "Unknown",
            invites=total_invites,
            server=guild.name
        )

        embed = discord.Embed(
            title=tpl.get("title", "New Member"),
            description=desc,
            color=get_theme_color(guild.id),
            timestamp=datetime.datetime.now()
        )
        if tpl.get("image"): embed.set_image(url=tpl.get("image"))
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=tpl.get("footer", "").format(join_time=join_time))

        log_channel = guild.get_channel(settings["log_channel"])
        if log_channel: await log_channel.send(embed=embed)

    @app_commands.command(name="invitesetup", description="🛠️ Open the Invite Customization Dashboard")
    @app_commands.checks.has_permissions(administrator=True)
    async def invitesetup(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📊 Invite Tracker Dashboard",
            description="Click the buttons below to customize your welcome logs, GIFs, and system status.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=InviteDashboard())

async def setup(bot):
    await bot.add_cog(InviteTracker(bot))
  
