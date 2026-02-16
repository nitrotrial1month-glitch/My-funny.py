import discord
from discord.ext import commands
from discord import app_commands

class RoleInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="roleinfo",
        aliases=["ri", "role"], # শর্টকাট কমান্ড
        description="📜 Get detailed information about a specific role"
    )
    @app_commands.describe(role="Select a role to view details")
    async def roleinfo(self, ctx, role: discord.Role):
        # --- ১. পারমিশন ফিল্টার করা ---
        # সব পারমিশন দেখালে লিস্ট অনেক বড় হয়ে যাবে, তাই শুধু মেইনগুলো দেখানো হচ্ছে
        permissions = []
        if role.permissions.administrator: permissions.append("Administrator")
        if role.permissions.manage_guild: permissions.append("Manage Server")
        if role.permissions.manage_roles: permissions.append("Manage Roles")
        if role.permissions.manage_channels: permissions.append("Manage Channels")
        if role.permissions.ban_members: permissions.append("Ban Members")
        if role.permissions.kick_members: permissions.append("Kick Members")
        if role.permissions.mention_everyone: permissions.append("Mention Everyone")
        if role.permissions.manage_messages: permissions.append("Manage Messages")
        
        # যদি কোনো স্পেশাল পারমিশন না থাকে
        perms_text = ", ".join(permissions) if permissions else "Standard Permissions"

        # --- ২. স্টাইলিশ ইমবেড সেটআপ ---
        # রোলের কালার যদি ডিফল্ট (কালো) হয়, তবে ডার্ক গ্রে কালার দেখাবে
        embed_color = role.color if role.color.value != 0 else 0x2b2d31

        embed = discord.Embed(
            title=f"📜 Role Information: {role.name}",
            color=embed_color
        )

        # রোলের কালার হেক্স কোড (Hex Code)
        hex_color = str(role.color).upper()

        # --- ফিল্ডস (Fields) ---
        
        # Basic Info
        embed.add_field(
            name="🆔 ID", 
            value=f"`{role.id}`", 
            inline=True
        )
        embed.add_field(
            name="🎨 Color", 
            value=f"`{hex_color}`", 
            inline=True
        )
        embed.add_field(
            name="👥 Members", 
            value=f"**{len(role.members)}** users have this role", 
            inline=True
        )

        # Settings (True/False check)
        embed.add_field(
            name="⚙️ Settings", 
            value=f"**Hoisted:** {'✅ Yes' if role.hoist else '❌ No'}\n"
                  f"**Mentionable:** {'✅ Yes' if role.mentionable else '❌ No'}\n"
                  f"**Managed:** {'✅ Yes' if role.managed else '❌ No'}", # বট বা ইন্টিগ্রেশন রোল কি না
            inline=True
        )
        
        # Position & Creation
        embed.add_field(
            name="📍 Position", 
            value=f"`{role.position}` (Hierarchy)", 
            inline=True
        )
        embed.add_field(
            name="📅 Created On", 
            value=f"<t:{int(role.created_at.timestamp())}:D> (<t:{int(role.created_at.timestamp())}:R>)", 
            inline=True
        )

        # Key Permissions Block
        embed.add_field(
            name="🛡️ Key Permissions", 
            value=f"```{perms_text}```", 
            inline=False
        )
        
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(RoleInfo(bot))
          
