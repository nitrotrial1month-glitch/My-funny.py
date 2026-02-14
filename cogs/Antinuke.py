import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio
from utils import load_config, save_config, get_theme_color

class AntiNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # ডিলিট ট্র্যাক করার জন্য একটি ডিকশনারি
        self.deletion_tracker = {} # {user_id: [timestamp1, timestamp2]}

    # ================= 1. LISTENER (চ্যানেল ডিলিট ডিটেকশন) =================
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        guild = channel.guild
        config = load_config()
        
        # সিস্টেম অন আছে কি না চেক করা
        if not config.get("antinuke_enabled", False):
            return

        # ১. কে ডিলিট করেছে তা অডিট লগ থেকে খুঁজে বের করা
        async for entry in guild.audit_logs(action=discord.AuditLogAction.channel_delete, limit=1):
            user = entry.user

            # যদি ইউজার বটের মালিক বা সার্ভার মালিক হয়, তবে ইগনোর করবে
            if user.id == guild.owner_id or user.id == self.bot.user.id:
                return

            # ২. টাইম ট্র্যাকিং লজিক
            now = datetime.datetime.now()
            user_id = user.id
            
            if user_id not in self.deletion_tracker:
                self.deletion_tracker[user_id] = []
            
            self.deletion_tracker[user_id].append(now)

            # গত ১০ সেকেন্ডের ভেতরের ডিলিটগুলো রাখা
            self.deletion_tracker[user_id] = [t for t in self.deletion_tracker[user_id] if (now - t).total_seconds() < 10]

            # ৩. যদি ১০ সেকেন্ডে ৩টির বেশি চ্যানেল ডিলিট হয় (Nuke Attempt)
            if len(self.deletion_tracker[user_id]) >= 3:
                await self.take_action(guild, user)

    # ================= 2. PUNISHMENT (অ্যাকশন নেওয়া) =================
    async def take_action(self, guild, user):
        try:
            # ইউজারের সব রোল কেড়ে নেওয়া (Security Lockdown)
            # এটি ব্যান করার চেয়ে নিরাপদ কারণ ভুল হলে রোল ফেরত দেওয়া যায়
            roles_to_remove = [role for role in user.roles if role.name != "@everyone" and not role.managed]
            await user.remove_roles(*roles_to_remove, reason="Anti-Nuke System: Mass Channel Deletion Detected")
            
            # এলার্ট মেসেজ পাঠানো
            log_channel = guild.system_channel or guild.text_channels[0]
            embed = discord.Embed(
                title="🚨 ANTI-NUKE ALERT 🚨",
                description=f"Mass channel deletion detected by {user.mention}!",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name="Action Taken", value="All roles have been removed to prevent further damage.")
            embed.set_footer(text="Wow Protection System", icon_url=self.bot.user.display_avatar.url)
            
            await log_channel.send(embed=embed)
        except Exception as e:
            print(f"Failed to take Anti-Nuke action: {e}")

    # ================= 3. SETUP COMMAND =================
    @app_commands.command(name="antinuke_setup", description="🛡️ Enable or Disable Anti-Nuke Protection")
    @app_commands.checks.has_permissions(administrator=True)
    async def antinuke_setup(self, interaction: discord.Interaction, status: bool):
        config = load_config()
        config["antinuke_enabled"] = status
        save_config(config)

        state = "Enabled 🟢" if status else "Disabled 🔴"
        embed = discord.Embed(
            title="🛡️ Security Update",
            description=f"Anti-Nuke / Wipe Protection is now **{state}**",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(AntiNuke(bot))
  
