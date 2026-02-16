import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime

# ডাটা সেভ করার ফাইল
DATA_FILE = "user_stats.json"

class UserHistory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stats = self.load_data()

    def load_data(self):
        """JSON ফাইল থেকে ডাটা লোড করে"""
        if not os.path.exists(DATA_FILE):
            return {}
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return {}

    def save_data(self):
        """JSON ফাইলে ডাটা সেভ করে"""
        with open(DATA_FILE, "w") as f:
            json.dump(self.stats, f, indent=4)

    # --- ১. মেসেজ ট্র্যাকার (Message Counter) ---
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        uid = str(message.author.id)
        gid = str(message.guild.id)

        # সার্ভার ও ইউজার অনুযায়ী ডাটা স্ট্রাকচার তৈরি
        if gid not in self.stats:
            self.stats[gid] = {}
        if uid not in self.stats[gid]:
            self.stats[gid][uid] = {"messages": 0, "last_msg": None}

        # মেসেজ কাউন্ট আপডেট করা
        self.stats[gid][uid]["messages"] += 1
        self.stats[gid][uid]["last_msg"] = str(datetime.now())
        
        # প্রতি ৫ মেসেজ পরপর সেভ করবে (পারফরমেন্সের জন্য)
        if self.stats[gid][uid]["messages"] % 5 == 0:
            self.save_data()

    # --- ২. হাইব্রিড হিস্ট্রি কমান্ড ---
    @commands.hybrid_command(
        name="history",
        description="📜 View detailed server activity of a user"
    )
    @app_commands.describe(user="Select a user (Optional)")
    async def history(self, ctx, user: discord.Member = None):
        if not user:
            user = ctx.author

        await ctx.defer() # ডাটা লোড হতে সময় লাগলে এরর আসবে না

        # --- মেসেজ স্ট্যাটাস বের করা ---
        gid = str(ctx.guild.id)
        uid = str(user.id)
        
        msg_count = 0
        last_active = "No recent activity"

        if gid in self.stats and uid in self.stats[gid]:
            msg_count = self.stats[gid][uid]["messages"]
            if self.stats[gid][uid]["last_msg"]:
                dt = datetime.strptime(self.stats[gid][uid]["last_msg"], "%Y-%m-%d %H:%M:%S.%f")
                last_active = f"<t:{int(dt.timestamp())}:R>"

        # --- মডারেটর অ্যাকশন চেক (Audit Log) ---
        # ইউজার যদি মডারেটর হয়, সে সার্ভারে কি কি কাজ করেছে তা চেক করা
        kicks = 0
        bans = 0
        role_updates = 0
        
        if ctx.guild.me.guild_permissions.view_audit_log:
            try:
                # গত ১০০টি এন্ট্রি চেক করবে
                async for entry in ctx.guild.audit_logs(limit=100, user=user):
                    if entry.action == discord.AuditLogAction.kick:
                        kicks += 1
                    elif entry.action == discord.AuditLogAction.ban:
                        bans += 1
                    elif entry.action == discord.AuditLogAction.member_role_update:
                        role_updates += 1
            except:
                pass
        
        mod_text = f"🚫 **Bans:** {bans}\nBOOT **Kicks:** {kicks}\n🎭 **Role Edits:** {role_updates}"

        # --- বর্তমান অবস্থা (Voice & Status) ---
        voice_state = "Not in Voice"
        if user.voice:
            voice_state = f"🔊 In {user.voice.channel.mention}"
            if user.voice.self_mute: voice_state += " (Muted)"
            if user.voice.self_deaf: voice_state += " (Deafened)"

        # --- স্টাইলিশ ইমবেড ---
        embed = discord.Embed(
            title=f"📜 Activity Report: {user.display_name}",
            description=f"Tracking stats since bot joined.",
            color=user.color if user.color != discord.Color.default() else 0x2b2d31
        )
        embed.set_thumbnail(url=user.display_avatar.url)

        # ১. মেসেজ এবং অ্যাক্টিভিটি
        embed.add_field(
            name="💬 Message Activity",
            value=f"**Total Messages:** `{msg_count}`\n**Last Message:** {last_active}",
            inline=True
        )

        # ২. ভয়েস স্ট্যাটাস
        embed.add_field(
            name="🎙️ Voice Status",
            value=voice_state,
            inline=True
        )

        # ৩. মডারেটর কাজ (যদি থাকে)
        embed.add_field(
            name="🛡️ Mod Actions (Last 100)",
            value=mod_text,
            inline=False
        )

        # ৪. মেম্বারশিপ ইনফো
        embed.add_field(
            name="📅 Membership",
            value=f"**Joined:** <t:{int(user.joined_at.timestamp())}:D>\n**Top Role:** {user.top_role.mention}",
            inline=False
        )

        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(UserHistory(bot))
