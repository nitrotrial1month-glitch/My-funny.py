import discord
from discord.ext import commands
from datetime import datetime

class Information(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="serverinfo", 
        aliases=["si", "sinfo"], # Short form aliases for Prefix command
        description="📊 Comprehensive breakdown of all server statistics and details"
    )
    async def serverinfo(self, ctx):
        guild = ctx.guild
        
        # 1. Channel Statistics
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        stage_channels = len(guild.stage_channels)
        forum_channels = len([c for c in guild.channels if isinstance(c, discord.ForumChannel)])
        
        # 2. Member & User Breakdown
        total_members = guild.member_count
        humans = len([m for m in guild.members if not m.bot])
        bots = len([m for m in guild.members if m.bot])
        
        # 3. Security & Settings
        v_level = str(guild.verification_level).title()
        content_filter = str(guild.explicit_content_filter).title()
        mfa_level = "Enabled" if guild.mfa_level else "Disabled"
        
        # 4. Features & Assets
        features = ", ".join([f.replace("_", " ").title() for f in guild.features]) or "Standard Server"
        roles = len(guild.roles)
        emojis = len(guild.emojis)
        stickers = len(guild.stickers)

        # Stylish Embed Setup
        embed = discord.Embed(
            title=f"📊 Server Overview: {guild.name}", 
            color=0x2F3136, # Stylish Dark Gray
            timestamp=datetime.utcnow()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        if guild.banner:
            embed.set_image(url=guild.banner.url)

        # --- Fields ---
        # Identity
        embed.add_field(name="👑 Owner", value=f"{guild.owner.mention}\n(`{guild.owner.id}`)", inline=True)
        embed.add_field(name="🆔 Server ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="📅 Created On", value=f"<t:{int(guild.created_at.timestamp())}:D>\n(<t:{int(guild.created_at.timestamp())}:R>)", inline=True)
        
        # Counts
        embed.add_field(
            name="👥 Members", 
            value=f"**Total:** {total_members}\n**Humans:** {humans}\n**Bots:** {bots}", 
            inline=True
        )
        embed.add_field(
            name="📁 Channels", 
            value=f"**Categories:** {categories}\n**Text:** {text_channels}\n**Voice:** {voice_channels}\n**Forum:** {forum_channels}", 
            inline=True
        )
        embed.add_field(
            name="🚀 Nitro Status", 
            value=f"**Level:** {guild.premium_tier}\n**Boosts:** {guild.premium_subscription_count}\n**Vanity:** {guild.vanity_url_code or 'None'}", 
            inline=True
        )

        # More details
        embed.add_field(
            name="🎨 Assets", 
            value=f"**Roles:** {roles}\n**Emojis:** {emojis}\n**Stickers:** {stickers}", 
            inline=True
        )
        embed.add_field(
            name="🛡️ Security", 
            value=f"**Verification:** {v_level}\n**NSFW Filter:** {content_filter}\n**2FA:** {mfa_level}", 
            inline=True
        )
        embed.add_field(
            name="📍 Other", 
            value=f"**Language:** {guild.preferred_locale}\n**Rules Ch:** {guild.rules_channel.mention if guild.rules_channel else 'None'}", 
            inline=True
        )

        # Features block
        embed.add_field(name="🛠️ Server Features", value=f"```\n{features}\n```", inline=False)

        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Information(bot))
  
