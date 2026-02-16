import discord
from discord.ext import commands
from discord import app_commands

class UserInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="userinfo",
        aliases=["ui", "profile"], # শর্টকাট কমান্ড
        description="👤 Get detailed information about a user"
    )
    @app_commands.describe(member="Select a user (Leave empty for yourself)")
    async def userinfo(self, ctx, member: discord.Member = None):
        # যদি কেউ মেনশন না করে, তবে নিজের ইনফো দেখাবে
        if member is None:
            member = ctx.author

        # --- ১. রোল প্রসেসিং ---
        # @everyone রোল বাদ দিয়ে বাকি সব রোল লিস্ট করা
        roles = [role.mention for role in member.roles if role.name != "@everyone"]
        # রোলগুলো উল্টো অর্ডারে সাজানো (বড় রোল আগে)
        roles.reverse()
        
        # যদি অনেক বেশি রোল থাকে, তবে ১০টার বেশি দেখাবে না
        if len(roles) > 10:
            role_list = ", ".join(roles[:10]) + f" and {len(roles) - 10} more..."
        elif not roles:
            role_list = "None"
        else:
            role_list = ", ".join(roles)

        # --- ২. পারমিশন চেক (Key Permissions) ---
        key_perms = []
        if member.guild_permissions.administrator: key_perms.append("Administrator")
        if member.guild_permissions.manage_server: key_perms.append("Manage Server")
        if member.guild_permissions.manage_messages: key_perms.append("Manage Messages")
        if member.guild_permissions.kick_members: key_perms.append("Kick Members")
        if member.guild_permissions.ban_members: key_perms.append("Ban Members")
        
        perms_text = ", ".join(key_perms) if key_perms else "Standard Member"

        # --- ৩. স্টাইলিশ ইমবেড তৈরি ---
        embed = discord.Embed(
            title=f"👤 User Information: {member.display_name}",
            color=member.color if member.color != discord.Color.default() else 0x2b2d31
        )
        
        # থাম্বনেইল হিসেবে ইউজারের অবতার
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # যদি ইউজারের ব্যানার থাকে তবে সেটি দেখাবে
        if member.banner:
            embed.set_image(url=member.banner.url)

        # --- ফিল্ডস ---
        
        # Identity
        embed.add_field(
            name="🆔 Identity", 
            value=f"**Name:** {member}\n**ID:** `{member.id}`\n**Mention:** {member.mention}", 
            inline=True
        )
        
        # Status & Activity
        status_emoji = {
            discord.Status.online: "🟢 Online",
            discord.Status.idle: "🌙 Idle",
            discord.Status.dnd: "⛔ DND",
            discord.Status.offline: "⚫ Offline"
        }
        # মোবাইল বা পিসি ডিটেকশন (Optional)
        client_status = "Desktop"
        if member.is_on_mobile(): client_status = "Mobile"
        
        embed.add_field(
            name="📊 Status", 
            value=f"**Current:** {status_emoji.get(member.status, '⚫ Offline')}\n**Device:** {client_status}\n**Bot:** {'Yes 🤖' if member.bot else 'No 👤'}", 
            inline=True
        )

        # Important Dates (Time Formatted)
        embed.add_field(
            name="📅 Important Dates", 
            value=f"**Joined Server:** <t:{int(member.joined_at.timestamp())}:R>\n**Account Created:** <t:{int(member.created_at.timestamp())}:D>", 
            inline=False
        )
        
        # Roles
        embed.add_field(
            name=f"🎭 Roles [{len(roles)}]", 
            value=role_list, 
            inline=False
        )

        # Permissions
        embed.add_field(
            name="🛡️ Key Permissions", 
            value=f"`{perms_text}`", 
            inline=False
        )
        
        # Footer
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(UserInfo(bot))
      
