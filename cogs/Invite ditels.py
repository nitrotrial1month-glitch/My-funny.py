import discord
from discord.ext import commands
from discord import app_commands
import datetime
import math
from utils import load_config, save_config, get_theme_color

# ================= 🔘 বাটন ভিউ ক্লাস (Button View Class) =================
class InvitePaginationView(discord.ui.View):
    def __init__(self, data, title, member, guild_id):
        super().__init__(timeout=60) # ৬০ সেকেন্ড পর বাটন কাজ করা বন্ধ করবে
        self.data = data
        self.title = title
        self.member = member
        self.guild_id = guild_id
        self.current_page = 1
        self.items_per_page = 10
        self.total_pages = math.ceil(len(data) / self.items_per_page)

    # এম্বেড জেনারেট করার ফাংশন
    def create_embed(self):
        start = (self.current_page - 1) * self.items_per_page
        end = start + self.items_per_page
        current_data = self.data[start:end]

        embed = discord.Embed(
            title=self.title,
            color=get_theme_color(self.guild_id),
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=self.member.display_avatar.url)

        description = ""
        for i, entry in enumerate(current_data, start=start + 1):
            status_icon = "🔄" if entry['status'] == "Rejoined" else "🆕"
            description += (
                f"**{i}. {entry['name']}**\n"
                f"├─ ID: `{entry['id']}`\n"
                f"├─ Date: `{entry['date']}`\n"
                f"└─ Status: **{entry['status']}** {status_icon}\n\n"
            )
        
        embed.description = description
        embed.set_footer(text=f"Page {self.current_page} of {self.total_pages} • Total Invites: {len(self.data)}")
        return embed

    # বাটন আপডেট ফাংশন (প্রথম বা শেষ পেজে বাটন ডিজেবল করার জন্য)
    def update_buttons(self):
        self.prev_button.disabled = (self.current_page == 1)
        self.next_button.disabled = (self.current_page == self.total_pages)

    # ⬅️ আগের পেজ বাটন
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, emoji="⬅️", disabled=True)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    # ➡️ পরের পেজ বাটন
    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, emoji="➡️")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    # পারমিশন চেক (যে কমান্ড দিয়েছে শুধু সেই বাটন চাপতে পারবে)
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.member: # এখানে member হলো কমান্ডদাতা বা যার প্রোফাইল দেখা হচ্ছে না, বরং যে কমান্ড দিয়েছে
            await interaction.response.send_message("❌ This is not your menu!", ephemeral=True)
            return False
        return True


# ================= ⚙️ মেইন কোগ ক্লাস =================
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
            if "invite_history" not in config: config["invite_history"] = {}
            if gid not in config["invite_history"]: config["invite_history"][gid] = {}
            if inviter_id not in config["invite_history"][gid]: config["invite_history"][gid][inviter_id] = []

            # Rejoin Check & Limit
            history = config["invite_history"][gid][inviter_id]
            is_rejoin = any(entry['id'] == member.id for entry in history)
            status = "Rejoined" if is_rejoin else "New Join"

            entry_data = {
                "name": member.name,
                "id": member.id,
                "date": datetime.datetime.now().strftime("%d-%b-%Y %I:%M %p"),
                "status": status
            }
            
            config["invite_history"][gid][inviter_id].insert(0, entry_data)
            # ডাটাবেস বড় হওয়া ঠেকাতে এখানে লিমিট রাখতে পারেন (অপশনাল)
            save_config(config)

    # ================= 📜 বাটন সহ ইনভাইট লিস্ট কমান্ড =================
    @commands.hybrid_command(name="invitelist", description="📜 View full invite history with buttons")
    @app_commands.describe(member="User to check history")
    async def invitelist(self, ctx, member: discord.Member = None):
        target_member = member or ctx.author # যার ইনভাইট চেক করা হচ্ছে
        config = load_config()
        gid, uid = str(ctx.guild.id), str(target_member.id)
        
        history = config.get("invite_history", {}).get(gid, {}
                                                    
