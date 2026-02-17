import discord
from discord.ext import commands
from discord import app_commands
import datetime
import math
from utils import get_theme_color
from database import Database  # 👇 ডাটাবেস ইমপোর্ট

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
        self.invites = {} # Cache for tracking differences

    @commands.Cog.listener()
    async def on_ready(self):
        """বট চালু হলে ইনভাইট ক্যাশ করবে"""
        for guild in self.bot.guilds:
            try: self.invites[guild.id] = await guild.invites()
            except: pass

    # ================= 📥 জয়েন ট্র্যাকিং (ডাটাবেস লজিক) =================
    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        inviter = None

        # ১. ইনভাইটার খোঁজা
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
        
        # ২. ডাটাবেসে সেভ করা
        if inviter:
            col = Database.get_collection("invites")
            gid, inviter_id = str(guild.id), str(inviter.id)

            # --- টাইপ নির্ধারণ ---
            inc_field = "regular"
            if member.bot:
                inc_field = "bots"
            elif (datetime.datetime.now(datetime.timezone.utc) - member.created_at).days < 1:
                inc_field = "fake"
            
            # --- হিস্ট্রি ডাটা তৈরি ---
            entry_data = {
                "name": member.name,
                "id": member.id,
                "date": datetime.datetime.now().strftime("%d-%b-%Y %I:%M %p"),
                "status": "New Join" # আপাতত সিম্পল রাখা হলো
            }

            # --- ৩. ইনভাইটার আপডেট (Update Inviter Stats) ---
            col.update_one(
                {"guild_id": gid, "user_id": inviter_id},
                {
                    "$inc": {inc_field: 1}, # সংখ্যা বাড়ানো
                    "$push": {
                        "history": {
                            "$each": [entry_data],
                            "$position": 0 # লিস্টের শুরুতে যোগ হবে
                        }
                    },
                    "$setOnInsert": {"bonus": 0, "leave": 0} # ডিফল্ট ভ্যালু
                },
                upsert=True
            )

            # --- ৪. জয়েন করা মেম্বার আপডেট (Who Invited whom) ---
            col.update_one(
                {"guild_id": gid, "user_id": str(member.id)},
                {
                    "$set": {
                        "invited_by": inviter_id,
                        "invited_by_name": inviter.name,
                        "join_date": entry_data["date"]
                    }
                },
                upsert=True
            )

    # ================= 📊 ১. INVITE STATS =================
    @commands.hybrid_command(name="invite", aliases=["i"], description="📊 View invite stats")
    @app_commands.describe(member="User to check")
    async def invite(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        col = Database.get_collection("invites")
        
        # ডাটাবেস থেকে ডাটা আনা
        data = col.find_one({"guild_id": str(ctx.guild.id), "user_id": str(member.id)})
        
        if not data:
            data = {} # ডাটা না থাকলে সব ০

        reg = data.get("regular", 0)
        fake = data.get("fake", 0)
        leave = data.get("leave", 0)
        bonus = data.get("bonus", 0)
        bots = data.get("bots", 0)

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

    # ================= 📜 ২. INVITED LIST =================
    @commands.hybrid_command(name="invited", aliases=["invites", "list", "il"], description="📜 See invited list")
    @app_commands.describe(member="User to check")
    async def invited(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        col = Database.get_collection("invites")
        
        data = col.find_one({"guild_id": str(ctx.guild.id), "user_id": str(target.id)})
        history = data.get("history", []) if data else []

        if not history:
            await ctx.send(embed=discord.Embed(description=f"❌ **{target.name}** has not invited anyone yet.", color=discord.Color.red()))
            return

        view = InvitePaginationView(data=history, title=f"📜 Invited by: {target.name}", author=ctx.author, member_checked=target, guild_id=ctx.guild.id)
        view.update_buttons()
        await ctx.send(embed=view.create_embed(), view=view)

    # ================= 🕵️ ৩. INVITER (CHECK SOURCE) =================
    @commands.hybrid_command(name="inviter", aliases=["who", "check"], description="🕵️ Check inviter")
    @app_commands.describe(member="User to check")
    async def inviter(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        col = Database.get_collection("invites")
        
        data = col.find_one({"guild_id": str(ctx.guild.id), "user_id": str(target.id)})
        
        embed = discord.Embed(title="Invite Source", color=get_theme_color(ctx.guild.id))
        embed.set_thumbnail(url=target.display_avatar.url)

        if data and "invited_by" in data:
            inviter_id = data.get("invited_by")
            date = data.get("join_date", "Unknown")
            embed.description = f"👤 **Member:** {target.mention}\n📨 **Invited By:** <@{inviter_id}> (`{inviter_id}`)\n📅 **Date:** `{date}`"
        else:
            embed.description = f"👤 **Member:** {target.mention}\n❓ **Invited By:** Unknown\n⚠️ *Tracking started recently.*"

        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ================= 🎁 ৪. ADD INVITE (BONUS) =================
    @commands.hybrid_command(name="addinvite")
    @commands.has_permissions(administrator=True)
    async def addinvite(self, ctx, member: discord.Member, amount: int):
        col = Database.get_collection("invites")
        col.update_one(
            {"guild_id": str(ctx.guild.id), "user_id": str(member.id)},
            {"$inc": {"bonus": amount}},
            upsert=True
        )
        
        embed = discord.Embed(description=f"<:Star:1472268505238863945> Added **{amount}** bonus invites to {member.mention}", color=discord.Color.green())
        embed.set_author(name=f"Action by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ================= 🗑️ ৫. REMOVE INVITE =================
    @commands.hybrid_command(name="removeinvite")
    @commands.has_permissions(administrator=True)
    async def removeinvite(self, ctx, member: discord.Member, amount: int):
        col = Database.get_collection("invites")
        col.update_one(
            {"guild_id": str(ctx.guild.id), "user_id": str(member.id)},
            {"$inc": {"bonus": -amount}},
            upsert=True
        )
        embed = discord.Embed(description=f"<:dot:1472268394391670855> Removed **{amount}** bonus invites from {member.mention}", color=discord.Color.orange())
        embed.set_author(name=f"Action by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ================= 🧹 ৬. CLEAR INVITE (USER RESET) =================
    @commands.hybrid_command(name="clearinvite", aliases=["resetinvite", "ci"], description="⚠️ Clear ALL data for a user")
    @commands.has_permissions(administrator=True)
    async def clearinvite(self, ctx, member: discord.Member):
        col = Database.get_collection("invites")
        result = col.delete_one({"guild_id": str(ctx.guild.id), "user_id": str(member.id)})
            
        if result.deleted_count > 0:
            embed = discord.Embed(description=f"<:dot:1472268394391670855> **Success:** All invite data for {member.mention} has been wiped!", color=discord.Color.red())
            embed.set_author(name=f"Action by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send(embed=discord.Embed(description="❌ This user already has 0 invites.", color=discord.Color.red()))

    # ================= ⚠️ ৭. RESET ALL (SERVER RESET) =================
    @commands.hybrid_command(name="resetallinvite")
    @commands.has_permissions(administrator=True)
    async def resetallinvite(self, ctx):
        col = Database.get_collection("invites")
        
        # শুধুমাত্র এই সার্ভারের ডাটা ডিলিট হবে
        col.delete_many({"guild_id": str(ctx.guild.id)})
        
        embed = discord.Embed(description="<:dot:1472268394391670855> All invite counts and history for this server have been reset!", color=discord.Color.red())
        embed.set_author(name=f"Action by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(InviteTracker(bot))
        
