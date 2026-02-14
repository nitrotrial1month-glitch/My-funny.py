import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button
import datetime
from utils import load_config, save_config, get_theme_color

# ================= 🎨 CUSTOMIZATION MODAL =================
class InviteMsgModal(Modal, title="🎨 Customize Invite Message"):
    msg_title = TextInput(label="Embed Title", placeholder="e.g. 📥 New Member Joined!", required=False)
    msg_desc = TextInput(
        label="Description (Placeholders allowed)", 
        style=discord.TextStyle.paragraph, 
        placeholder="Use: {member}, {inviter}, {invites}, {server}", 
        required=True
    )
    msg_image = TextInput(label="GIF / Banner Image URL", placeholder="https://link.to-your-gif.gif", required=False)
    msg_footer = TextInput(label="Footer Text", placeholder="e.g. Join time: {join_time}", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        guild_id = str(interaction.guild.id)
        if guild_id not in config["invite_settings"]: config["invite_settings"][guild_id] = {}
        
        config["invite_settings"][guild_id]["template"] = {
            "title": self.msg_title.value,
            "description": self.msg_desc.value,
            "image": self.msg_image.value,
            "footer": self.msg_footer.value
        }
        save_config(config)
        await interaction.response.send_message("✅ Invite message template updated!", ephemeral=True)

# ================= 🛡️ DASHBOARD VIEW =================
class InviteDashboard(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Edit Message", style=discord.ButtonStyle.primary, emoji="📝")
    async def edit_msg(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(InviteMsgModal())

    @discord.ui.button(label="Toggle System", style=discord.ButtonStyle.success, emoji="⚙️")
    async def toggle(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        guild_id = str(interaction.guild.id)
        settings = config["invite_settings"].get(guild_id, {})
        current = settings.get("enabled", False)
        settings["enabled"] = not current
        config["invite_settings"][guild_id] = settings
        save_config(config)
        status = "ON 🟢" if not current else "OFF 🔴"
        await interaction.response.send_message(f"✅ Invite System is now **{status}**", ephemeral=True)

# ================= 🚀 MAIN INVITE TRACKER COG =================
class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites = {}

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            try:
                self.invites[guild.id] = await guild.invites()
            except: pass

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        config = load_config()
        settings = config.get("invite_settings", {}).get(str(guild.id), {})
        if not settings.get("enabled", False) or not settings.get("log_channel"): return

        # ইনভাইটার খোঁজা
        invites_before = self.invites.get(guild.id)
        invites_after = await guild.invites()
        self.invites[guild.id] = invites_after
        inviter = None
        if invites_before:
            for i in invites_before:
                for a in invites_after:
                    if i.code == a.code and a.uses > i.uses:
                        inviter = i.inviter
                        break

        # ডাটা সেভ
        invite_data = config.get("invite_data", {}).get(str(guild.id), {})
        total_invites = 0
        if inviter:
            inviter_id = str(inviter.id)
            if inviter_id not in invite_data: invite_data[inviter_id] = {"count": 0}
            invite_data[inviter_id]["count"] += 1
            total_invites = invite_data[inviter_id]["count"]
            milestones = settings.get("milestones", {})
            if str(total_invites) in milestones:
                role = guild.get_role(int(milestones[str(total_invites)]))
                if role: await inviter.add_roles(role)
        config["invite_data"][str(guild.id)] = invite_data
        save_config(config)

        # লগ পাঠানো
        log_channel = guild.get_channel(settings["log_channel"])
        if log_channel:
            tpl = settings.get("template", {})
            jt = datetime.datetime.now().strftime("%B %d, %Y %I:%M %p")
            description = tpl.get("description", "{member} joined").format(
                member=member.mention, inviter=inviter.mention if inviter else "Unknown",
                invites=total_invites, server=guild.name
            )
            embed = discord.Embed(title=tpl.get("title", "Member Joined"), description=description, color=get_theme_color(guild.id), timestamp=datetime.datetime.now())
            if tpl.get("image"): embed.set_image(url=tpl.get("image"))
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=tpl.get("footer", "Join time: {join_time}").format(join_time=jt))
            await log_channel.send(embed=embed)

    # --- COMMANDS ---
    @commands.hybrid_command(name="invitesetup", description="🛠️ Interactive Invite Dashboard")
    @commands.has_permissions(administrator=True)
    async def invitesetup(self, ctx):
        embed = discord.Embed(title="📊 Invite Tracker Setup", description="Toggle the system or edit your custom message using the buttons.", color=discord.Color.blue())
        await ctx.send(embed=embed, view=InviteDashboard())

    @commands.hybrid_command(name="invitelog", description="📢 Set the channel for invite logs")
    @commands.has_permissions(administrator=True)
    async def invitelog(self, ctx, channel: discord.TextChannel):
        config = load_config()
        config["invite_settings"][str(ctx.guild.id)]["log_channel"] = channel.id
        save_config(config)
        await ctx.send(f"✅ Logs set to {channel.mention}")

    @commands.hybrid_command(name="inviterole", description="🏆 Add a reward role for invites")
    @commands.has_permissions(administrator=True)
    async def inviterole(self, ctx, role: discord.Role, count: int):
        config = load_config()
        if "milestones" not in config["invite_settings"][str(ctx.guild.id)]: config["invite_settings"][str(ctx.guild.id)]["milestones"] = {}
        config["invite_settings"][str(ctx.guild.id)]["milestones"][str(count)] = role.id
        save_config(config)
        await ctx.send(f"✅ {role.mention} will be given at **{count}** invites.")

    @commands.hybrid_command(name="inviteremove", description="🗑️ Reset invite data")
    @commands.has_permissions(administrator=True)
    async def inviteremove(self, ctx, member: discord.Member = None):
        config = load_config()
        if member:
            if str(ctx.guild.id) in config["invite_data"] and str(member.id) in config["invite_data"][str(ctx.guild.id)]:
                del config["invite_data"][str(ctx.guild.id)][str(member.id)]
                save_config(config)
                await ctx.send(f"✅ Data reset for {member.mention}")
        else:
            config["invite_data"][str(ctx.guild.id)] = {}
            save_config(config)
            await ctx.send("✅ All invite data reset.")

async def setup(bot):
    await bot.add_cog(InviteTracker(bot))
    
