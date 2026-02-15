import discord
from discord.ext import commands
from discord import app_commands
import datetime
import math
from utils import load_config, save_config, get_theme_color

# ================= 🔘 পেজ বাটন ক্লাস (Pagination View) =================
class InvitePaginationView(discord.ui.View):
    def __init__(self, data, title, author, member_checked, guild_id):
        super().__init__(timeout=60)
        self.data = data
        self.title = title
        self.author = author
        self.member_checked = member_checked
        self.guild_id = guild_id
        self.current_page = 1
        self.items_per_page = 10
        self.total_pages = math.ceil(len(data) / self.items_per_page)

    def create_embed(self):
        start = (self.current_page - 1) * self.items_per_page
        end = start + self.items_per_page
        current_data = self.data[start:end]

        embed = discord.Embed(
            title=self.title,
            color=get_theme_color(self.guild_id),
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=self.member_checked.display_avatar.url)

        description = ""
        for i, entry in enumerate(current_data, start=start + 1):
            status_icon = "🔄" if entry.get('status') == "Rejoined" else "🆕"
            date_str = entry.get('date', 'Unknown Date')
            
            description += (
                f"**{i}. {entry['name']}**\n"
                f"├─ ID: `{entry['id']}`\n"
                f"├─ Date: `{date_str}`\n"
                f"└─ Status: **{entry.get('status', 'New Join')}** {status_icon}\n\n"
            )
        
        embed.description = description or "❌ No invites found."
        embed.set_footer(text=f"Page {self.current_page} of {self.total_pages} • Total: {len(self.data)}")
        return embed

    def update_buttons(self):
        self.prev_button.disabled = (self.current_page == 1)
        self.next_button.disabled = (self.current_page == self.total_pages)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, emoji="⬅️")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, emoji="➡️")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("❌ This menu is not for you!", ephemeral=True)
            return False
        return True

# ================= ⚙️ মেইন লজিক ক্লাস =================
class InviteDetails(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites = {}

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            try: self.invites[guild.id] = await guild.invites()
            except: pass

    # ================= 📝 ডাটা সেভ লজিক =================
    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        config = load_config()
        inviter = None

        if member.bot:
            try:
                async for entry in guild.audit_logs(action=discord.AuditLogAction.bot_add, limit=5):
                    if entry.target.id == member.id:
                        inviter = entry.user
                        break
            except: pass
        else:
            invites_before = self.invites.get(guild.id)
            invites_after = await guild.invites()
            self.invites[guild.id] = invites_after
            if invites_before:
                for i in invites_before:
                    for a in invites_after:
                        if i.code == a.code and a.uses > i.uses:
                            inviter = i.inviter
                            break
        
        if inviter:
            gid, inviter_id = str(guild.id), str(inviter.id)
            
            # কনফিগারেশন চেক
            if "invite_history" not in config: config["invite_history"] = {}
            if gid not in config["invite_history"]: config["invite_history"][gid] = {}
            if inviter_id not in config["invite_history"][gid]: config["invite_history"][gid][inviter_id] = []

            # Rejoin চেক
            history = config["invite_history"][gid][inviter_id]
            is_rejoin = any(entry['id'] == member.id for entry in history)
            status = "Rejoined" if is_rejoin else "New Join"

            entry_data = {
                "name": member.name,
                "id": member.id,
                "date": datetime.datetime.now().strftime("%d-%b-%Y %I:%M %p"),
                "status": status,
                "invited_by_id": inviter_id
            }
            
            config["invite_history"][gid][inviter_id].insert(0, entry_data)
            
            # Who invited me ডাটা সেভ
            if "who_invited" not in config: config["who_invited"] = {}
            if gid not in config["who_invited"]: config["who_invited"][gid] = {}
            
            config["who_invited"][gid][str(member.id)] = {
                "inviter_id": inviter_id,
                "inviter_name": inviter.name,
                "date": entry_data["date"]
            }

            save_config(config)

    # ================= 📜 ১. INVITED কমান্ড (Short forms added) =================
    @commands.hybrid_command(
        name="invited", 
        aliases=["invites", "list", "il"], # শর্ট ফর্ম: !invites, !list, !il
        description="📜 See the list of people invited by a user."
    )
    @app_commands.describe(member="User to check invites for")
    async def invited(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        config = load_config()
        gid, uid = str(ctx.guild.id), str(target.id)
        
        history = config.get("invite_history", {}).get(gid, {}).get(uid, [])

        if not history:
            await ctx.send(embed=discord.Embed(
                description=f"❌ **{target.name}** has not invited anyone yet.", 
                color=discord.Color.red()
            ))
            return

        view = InvitePaginationView(
            data=history, 
            title=f"📜 Invited by: {target.name}", 
            author=ctx.author,
            member_checked=target,
            guild_id=ctx.guild.id
        )
        view.update_buttons()
        await ctx.send(embed=view.create_embed(), view=view)

    # ================= 🕵️ ২. INVITER কমান্ড (Short forms added) =================
    @commands.hybrid_command(
        name="inviter", 
        aliases=["who", "check", "wh"], # শর্ট ফর্ম: !who, !check, !wh
        description="🕵️ Check who invited a specific member."
    )
    @app_commands.describe(member="User to check invite source for")
    async def inviter(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        config = load_config()
        gid, target_id = str(ctx.guild.id), str(target.id)

        invite_info = config.get("who_invited", {}).get(gid, {}).get(target_id)

        embed = discord.Embed(title=f"Invite Source Info", color=get_theme_color(ctx.guild.id))
        embed.set_thumbnail(url=target.display_avatar.url)

        if invite_info:
            inviter_id = invite_info.get("inviter_id")
            inviter_name = invite_info.get("inviter_name", "Unknown")
            date = invite_info.get("date", "Unknown")
            
            inviter_member = ctx.guild.get_member(int(inviter_id))
            inviter_mention = inviter_member.mention if inviter_member else f"@{inviter_name}"

            embed.description = (
                f"👤 **Member:** {target.mention}\n"
                f"📨 **Invited By:** {inviter_mention} (`{inviter_id}`)\n"
                f"📅 **Date:** `{date}`"
            )
        else:
            embed.description = (
                f"👤 **Member:** {target.mention}\n"
                f"❓ **Invited By:** Unknown / Old Member\n"
                f"⚠️ *Tracking started recently.*"
            )

        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(InviteDetails(bot))
            
