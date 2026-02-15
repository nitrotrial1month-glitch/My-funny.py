import discord
from discord.ext import commands
from discord import app_commands
import datetime
import math
from utils import load_config, save_config, get_theme_color

# ================= 🔘 বাটন ক্লাস (Pagination View) =================
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

# ================= ⚙️ মেইন ইনভাইট ট্র্যাকার ক্লাস =================
class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites = {}

    @commands.Cog.listener()
    async def on_ready(self):
        """বট চালু হলে ইনভাইট ক্যাশ করবে"""
        for guild in self.bot.guilds:
            try: self.invites[guild.id] = await guild.invites()
            except: pass

    # ================= 📥 জয়েন ট্র্যাকিং (সব লজিক একসাথে) =================
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
            
            if "invite_data" not in config: config["invite_data"] = {}
            if gid not in config["invite_data"]: config["invite_data"][gid] = {}
            if inviter_id not in config["invite_data"][gid]: 
                config["invite_data"][gid][inviter_id] = {"regular": 0, "fake": 0, "leave": 0, "bonus": 0, "bots": 0}

            if "invite_history" not in config: config["invite_history"] = {}
            if gid not in config["invite_history"]: config["invite_history"][gid] = {}
            if inviter_id not in config["invite_history"][gid]: config["invite_history"][gid][inviter_id] = []
            
            if "who_invited" not in config: config["who_invited"] = {}
            if gid not in config["who_invited"]: config["who_invited"][gid] = {}

            # --- সংখ্যা আপডেট ---
            if member.bot:
                config["invite_data"][gid][inviter_id]["bots"] += 1
            elif (datetime.datetime.now(datetime.timezone.utc) - member.created_at).days < 1:
                config["invite_data"][gid][inviter_id]["fake"] += 1
            else:
                config["invite_data"][gid][inviter_id]["regular"] += 1

            # --- ডিটেইলস আপডেট ---
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

            # --- সোর্স আপডেট ---
            config["who_invited"][gid][str(member.id)] = {
                "inviter_id": inviter_id,
                "inviter_name": inviter.name,
                "date": entry_data["date"]
            }

            save_config(config)

    # ================= 📊 ১. INVITE =================
    @commands.hybrid_command(name="invite", aliases=["i", "inv"], description="📊 View invite stats")
    @app_commands.describe(member="User to check")
    async def invite(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        config = load_config()
        data = config.get("invite_data", {}).get(str(ctx.guild.id), {}).get(str(member.id), {
            "regular": 0, "fake": 0, "leave": 0, "bonus": 0, "bots": 0
        })

        reg, fake, leave, bonus, bots = data.values()
        total = max(0, (reg + bonus) - (fake + leave))

        embed = discord.Embed(title=f"", color=get_theme_color(ctx.guild.id))
        embed.set_author(name=f"{member.name}", icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        
        embed.description = (
            f"<:Star:1472268505238863945> **Total Invites:** `{total}`\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<:dot:1472268394391670855> **Join:** `{reg}`\n"
            f"<:dot:1472268394391670855> **Leave:** `{leave}`\n"
            f"<:dot:1472268394391670855> **Fake:** `{fake}`\n"
            f"<:dot:1472268394391670855> **Bonus:** `{bonus}`\n"
            f"<:dot:1472268394391670855> **Bots:** `{bots}`"
        )
        embed.set_footer(text="Funny Bot Security", icon_url=self.bot.user.display_avatar.url)
        await ctx.send(embed=embed)

    # ================= 📜 ২. INVITED (LIST) =================
    @commands.hybrid_command(name="invited", aliases=["invites", "list", "il"], description="📜 See invited list")
    @app_commands.describe(member="User to check")
    async def invited(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        config = load_config()
        gid, uid = str(ctx.guild.id), str(target.id)
        
        history = config.get("invite_history", {}).get(gid, {}).get(uid, [])

        if not history:
            await ctx.send(embed=discord.Embed(description=f"❌ **{target.name}** has not invited anyone yet.", color=discord.Color.red()))
            return

        view = InvitePaginationView(data=history, title=f"📜 Invited by: {target.name}", author=ctx.author, member_checked=target, guild_id=ctx.guild.id)
        view.update_buttons()
        await ctx.send(embed=view.create_embed(), view=view)

    # ================= 🕵️ ৩. INVITER (SOURCE) =================
    @commands.hybrid_command(name="inviter", aliases=["who", "check"], description="🕵️ Check inviter")
    @app_commands.describe(member="User to check")
    async def inviter(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        config = load_config()
        info = config.get("who_invited", {}).get(str(ctx.guild.id), {}).get(str(target.id))
        embed = discord.Embed(title="Invite Source", color=get_theme_color(ctx.guild.id))
        embed.set_thumbnail(url=target.display_avatar.url)

        if info:
            embed.description = f"👤 **Member:** {target.mention}\n📨 **Invited By:** <@{info.get('inviter_id')}> (`{info.get('inviter_id')}`)\n📅 **Date:** `{info.get('date')}`"
        else:
            embed.description = f"👤 **Member:** {target.mention}\n❓ **Invited By:** Unknown\n⚠️ *Tracking started recently.*"

        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ================= 🎁 ৪. ADD INVITE =================
    @commands.hybrid_command(name="addinvite")
    @commands.has_permissions(administrator=True)
    async def addinvite(self, ctx, member: discord.Member, amount: int):
        config = load_config()
        gid, uid = str(ctx.guild.id), str(member.id)
        if gid not in config.setdefault("invite_data", {}): config["invite_data"][gid] = {}
        config["invite_data"][gid].setdefault(uid, {"regular": 0, "fake": 0, "leave": 0, "bonus": 0, "bots": 0})["bonus"] += amount
        save_config(config)
        
        embed = discord.Embed(description=f"<:Star:1472268505238863945> Added **{amount}** bonus invites to {member.mention}", color=discord.Color.green())
        embed.set_author(name=f"Action by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ================= 🗑️ ৫. REMOVE INVITE (Bonus only) =================
    @commands.hybrid_command(name="removeinvite")
    @commands.has_permissions(administrator=True)
    async def removeinvite(self, ctx, member: discord.Member, amount: int):
        config = load_config()
        gid, uid = str(ctx.guild.id), str(member.id)
        if gid in config.get("invite_data", {}) and uid in config["invite_data"][gid]:
            config["invite_data"][gid][uid]["bonus"] -= amount
            save_config(config)
            embed = discord.Embed(description=f"<:dot:1472268394391670855> Removed **{amount}** bonus invites from {member.mention}", color=discord.Color.orange())
            embed.set_author(name=f"Action by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ User has no data.")

    # ================= 🧹 ৬. CLEAR INVITE (New: User Reset) =================
    @commands.hybrid_command(name="clearinvite", aliases=["resetinvite", "ci"], description="⚠️ Clear ALL data for a user")
    @commands.has_permissions(administrator=True)
    async def clearinvite(self, ctx, member: discord.Member):
        config = load_config()
        gid, uid = str(ctx.guild.id), str(member.id)
        deleted = False
        
        # কাউন্ট ডিলিট
        if gid in config.get("invite_data", {}) and uid in config["invite_data"][gid]:
            del config["invite_data"][gid][uid]
            deleted = True
            
        # হিস্ট্রি ডিলিট
        if gid in config.get("invite_history", {}) and uid in config["invite_history"][gid]:
            del config["invite_history"][gid][uid]
            deleted = True
            
        if deleted:
            save_config(config)
            embed = discord.Embed(description=f"<:dot:1472268394391670855> **Success:** All invite data for {member.mention} has been wiped!", color=discord.Color.red())
            embed.set_author(name=f"Action by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send(embed=discord.Embed(description="❌ This user already has 0 invites.", color=discord.Color.red()))

    # ================= ⚠️ ৭. RESET ALL (Server Reset) =================
    @commands.hybrid_command(name="resetallinvite")
    @commands.has_permissions(administrator=True)
    async def resetallinvite(self, ctx):
        config = load_config()
        gid = str(ctx.guild.id)
        
        # সব ডাটা ক্লিয়ার
        if gid in config.get("invite_data", {}): config["invite_data"][gid] = {}
        if gid in config.get("invite_history", {}): config["invite_history"][gid] = {}
        if gid in config.get("who_invited", {}): config["who_invited"][gid] = {}
            
        save_config(config)
        embed = discord.Embed(description="<:dot:1472268394391670855> All invite counts and history for this server have been reset!", color=discord.Color.red())
        embed.set_author(name=f"Action by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(InviteTracker(bot))
            
