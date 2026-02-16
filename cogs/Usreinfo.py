import discord
from discord.ext import commands
from discord import app_commands

class UserInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="userinfo",
        aliases=["ui", "whois", "profile"], 
        description="👤 Get detailed information about a user"
    )
    @app_commands.describe(member="Select a user (Leave empty for yourself)")
    async def userinfo(self, ctx, member: discord.Member = None):
        await ctx.defer() # প্রসেসিং এর জন্য সময় নেওয়া

        try:
            # যদি কেউ মেনশন না করে, তবে নিজের ইনফো দেখাবে
            if member is None:
                member = ctx.author

            # ইউজারের ব্যানার পাওয়ার জন্য এপিআই থেকে ফেচ করা প্রয়োজন
            user_data = await self.bot.fetch_user(member.id)

            # --- ১. রোল প্রসেসিং ---
            roles = [role.mention for role in member.roles if role.name != "@everyone"]
            roles.reverse()
            
            if len(roles) > 10:
                role_list = ", ".join(roles[:10]) + f" and {len(roles) - 10} more..."
            elif not roles:
                role_list = "No Roles"
            else:
                role_list = ", ".join(roles)

            # --- ২. পারমিশন চেক ---
            key_perms = []
            if member.guild_permissions.administrator: key_perms.append("Administrator")
            elif member.guild_permissions.manage_guild: key_perms.append("Manage Server")
            if member.guild_permissions.ban_members: key_perms.append("Ban Members")
            if member.guild_permissions.kick_members: key_perms.append("Kick Members")
            if member.guild_permissions.manage_messages: key_perms.append("Manage Messages")
            
            perms_text = ", ".join(key_perms) if key_perms else "Standard Member"

            # --- ৩. স্টাইলিশ ইমবেড ---
            # কালার: ইউজারের প্রোফাইল কালার অথবা রোলের কালার
            embed_color = user_data.accent_color or member.color or discord.Color(0x2b2d31)

            embed = discord.Embed(
                title=f"👤 User Info: {member.display_name}",
                color=embed_color
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            
            # ব্যানার সেট করা (যদি থাকে)
            if user_data.banner:
                embed.set_image(url=user_data.banner.url)

            # --- ফিল্ডস ---
            embed.add_field(
                name="🆔 Identity", 
                value=f"**Name:** {member}\n**ID:** `{member.id}`\n**Mention:** {member.mention}", 
                inline=True
            )
            
            # স্ট্যাটাস (মোবাইল/পিসি)
            status = "Offline/Invisible"
            if member.status != discord.Status.offline:
                status = str(member.status).title()
            
            bot_status = "🤖 Bot" if member.bot else "👤 Human"

            embed.add_field(
                name="📊 Status", 
                value=f"**Activity:** {status}\n**Type:** {bot_status}", 
                inline=True
            )

            # ডেট ফরম্যাটিং
            joined_at = int(member.joined_at.timestamp()) if member.joined_at else 0
            created_at = int(member.created_at.timestamp()) if member.created_at else 0

            embed.add_field(
                name="📅 Dates", 
                value=f"**Joined:** <t:{joined_at}:R>\n**Created:** <t:{created_at}:D>", 
                inline=False
            )
            
            embed.add_field(
                name=f"🎭 Roles [{len(roles)}]", 
                value=role_list, 
                inline=False
            )

            embed.add_field(
                name="🛡️ Key Permissions", 
                value=f"`{perms_text}`", 
                inline=False
            )
            
            embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)

            # মেসেজ পাঠানো (Followup ব্যবহার করা কারণ defer দেওয়া আছে)
            await ctx.send(embed=embed)

        except Exception as e:
            # যদি কোনো এরর হয় তবে তা দেখাবে
            await ctx.send(f"❌ **Error:** `{str(e)}`\n(Please check if 'Server Members Intent' is enabled in Developer Portal)")

async def setup(bot):
    await bot.add_cog(UserInfo(bot))
        
