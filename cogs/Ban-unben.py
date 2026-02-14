import discord
from discord.ext import commands
from discord import app_commands
import datetime
from utils import get_theme_color

class BanSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= 🔨 BAN COMMAND =================
    @commands.hybrid_command(
        name="ban",
        description="🔨 Ban a member from the server with a stylish embed"
    )
    @commands.has_permissions(ban_members=True)
    @app_commands.describe(member="The user you want to ban", reason="Reason for the ban")
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        # বটের নিজের থেকে বড় রোল বা অ্যাডমিনকে ব্যান করা আটকানো
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("❌ You cannot ban someone with a higher or equal role!", ephemeral=True)

        try:
            # ব্যান করার আগে ইউজারকে ডিএম (DM) পাঠানো
            try:
                dm_embed = discord.Embed(
                    title="🚫 You have been Banned!",
                    description=f"You were banned from **{ctx.guild.name}**.",
                    color=discord.Color.red()
                )
                dm_embed.add_field(name="💬 Reason", value=reason)
                await member.send(embed=dm_embed)
            except:
                pass # যদি ডিএম অফ থাকে

            await member.ban(reason=reason)

            # --- STYLISH BAN EMBED ---
            embed = discord.Embed(
                title="🔨 User Banned Successfully",
                description=f"**{member.name}** has been removed from the server.",
                color=discord.Color.from_rgb(255, 0, 0), # Red Color
                timestamp=datetime.datetime.now()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="👤 Target", value=f"{member.mention}\nID: `{member.id}`", inline=True)
            embed.add_field(name="🛡️ Moderator", value=f"{ctx.author.mention}", inline=True)
            embed.add_field(name="📝 Reason", value=f"`{reason}`", inline=False)
            
            # একটি হ্যামার (Hammer) GIF
            embed.set_image(url="https://media.tenor.com/4Kms9Hh8_YQAAAAM/ban-hammer.gif")
            embed.set_footer(text="Funny Bot Moderation", icon_url=self.bot.user.display_avatar.url)

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Failed to ban user: {e}", ephemeral=True)

    # ================= 🔓 UNBAN COMMAND =================
    @commands.hybrid_command(
        name="unban",
        description="🔓 Unban a user using their User ID"
    )
    @commands.has_permissions(ban_members=True)
    @app_commands.describe(user_id="The ID of the user you want to unban", reason="Reason for the unban")
    async def unban(self, ctx: commands.Context, user_id: str, *, reason: str = "No reason provided"):
        try:
            user = await self.bot.fetch_user(int(user_id))
            await ctx.guild.unban(user, reason=reason)

            # --- STYLISH UNBAN EMBED ---
            embed = discord.Embed(
                title="🔓 User Unbanned",
                description=f"**{user.name}** is now allowed to join the server again.",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(name="👤 User", value=f"{user.mention}\nID: `{user.id}`", inline=True)
            embed.add_field(name="🛡️ Moderator", value=f"{ctx.author.mention}", inline=True)
            
            embed.set_footer(text="Funny Bot Moderation", icon_url=self.bot.user.display_avatar.url)

            await ctx.send(embed=embed)

        except ValueError:
            await ctx.send("❌ Please provide a valid **User ID** (numbers only).", ephemeral=True)
        except discord.NotFound:
            await ctx.send("❌ This user was not found in the ban list.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}", ephemeral=True)

    # পারমিশন এরর হ্যান্ডলিং
    @ban.error
    @unban.error
    async def mod_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need **Ban Members** permission to use this command!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(BanSystem(bot))
                           
