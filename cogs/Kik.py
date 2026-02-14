import discord
from discord.ext import commands
from discord import app_commands
import datetime
from utils import get_theme_color

class KickSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="kick",
        description="👢 Kick a member from the server with a stylish embed"
    )
    @commands.has_permissions(kick_members=True)
    @app_commands.describe(member="The user you want to kick", reason="Reason for the kick")
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        # ১. সিকিউরিটি চেক: নিজেকে কিক করা যাবে না
        if member.id == ctx.author.id:
            return await ctx.send("❌ You cannot kick yourself!", ephemeral=True)

        # ২. সিকিউরিটি চেক: হায়ার রোল বা সমান রোলের কাউকে কিক করা যাবে না
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("❌ You cannot kick someone with a higher or equal role!", ephemeral=True)

        # ৩. সিকিউরিটি চেক: বট নিজে কি ওই ইউজারকে কিক করতে পারবে?
        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send("❌ I cannot kick this user because their role is higher than mine!", ephemeral=True)

        try:
            # কিক করার আগে ইউজারকে একটি ডিএম (DM) পাঠানো
            try:
                dm_embed = discord.Embed(
                    title="👢 You have been Kicked!",
                    description=f"You were kicked from **{ctx.guild.name}**.",
                    color=discord.Color.orange()
                )
                dm_embed.add_field(name="📝 Reason", value=reason)
                dm_embed.set_footer(text="Please follow the server rules to avoid further actions.")
                await member.send(embed=dm_embed)
            except:
                pass # যদি ইউজারের ডিএম অফ থাকে

            # ইউজারকে কিক করা
            await member.kick(reason=reason)

            # --- STYLISH KICK EMBED ---
            embed = discord.Embed(
                title="👢 User Kicked Successfully",
                description=f"**{member.name}** has been kicked from the server.",
                color=discord.Color.orange(), # কিকের জন্য কমলা রঙ
                timestamp=datetime.datetime.now()
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="👤 Target", value=f"{member.mention}\nID: `{member.id}`", inline=True)
            embed.add_field(name="🛡️ Moderator", value=f"{ctx.author.mention}", inline=True)
            embed.add_field(name="📝 Reason", value=f"`{reason}`", inline=False)
            
            # একটি স্টাইলিশ বুট বা কিক GIF
            embed.set_image(url="https://media.tenor.com/796Ie855C_IAAAAM/kick-get-out.gif")
            
            embed.set_footer(
                text=f"Funny Bot Moderation", 
                icon_url=self.bot.user.display_avatar.url
            )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Failed to kick user: {e}", ephemeral=True)

    # পারমিশন এরর হ্যান্ডলিং
    @kick.error
    async def kick_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need **Kick Members** permission to use this command!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(KickSystem(bot))
  
