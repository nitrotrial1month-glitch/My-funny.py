import discord
from discord.ext import commands
from discord import app_commands
from utils import get_theme_color # এখানে আমরা আসল utils.py থেকে কালার ফাংশন আনছি

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= 🖼️ AVATAR COMMAND =================
    @commands.hybrid_command(name="avatar", aliases=["av", "pfp", "pic"], description="🖼️ View a user's avatar")
    @app_commands.describe(member="The user whose avatar you want to see")
    async def avatar(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        
        embed = discord.Embed(
            title=f"Avatar of {member.display_name}",
            color=member.color if member.color != discord.Color.default() else get_theme_color(ctx.guild.id)
        )
        embed.set_image(url=member.display_avatar.url)
        embed.description = (
            f"👤 **User:** {member.mention} (`@{member.name}`)\n"
            f"🔗 **Download:** [PNG]({member.display_avatar.with_format('png').url}) | "
            f"[JPG]({member.display_avatar.with_format('jpg').url}) | "
            f"[WEBP]({member.display_avatar.with_format('webp').url})"
        )
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Download PNG", url=member.display_avatar.with_format("png").url, style=discord.ButtonStyle.link))
        view.add_item(discord.ui.Button(label="Download JPG", url=member.display_avatar.with_format("jpg").url, style=discord.ButtonStyle.link))
        
        await ctx.send(embed=embed, view=view)

    # ================= 🚩 BANNER COMMAND =================
    @commands.hybrid_command(name="banner", aliases=["bn", "cover", "bg"], description="🚩 View a user's banner")
    @app_commands.describe(member="The user whose banner you want to see")
    async def banner(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        user = await self.bot.fetch_user(member.id)
        
        if not user.banner:
            embed = discord.Embed(
                description=f"❌ **{member.display_name}** (`@{member.name}`) does not have a banner.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title=f"Banner of {member.display_name}",
            color=member.color if member.color != discord.Color.default() else get_theme_color(ctx.guild.id)
        )
        embed.set_image(url=user.banner.url)
        embed.description = (
            f"👤 **User:** {member.mention} (`@{member.name}`)\n"
            f"🔗 **Download:** [PNG]({user.banner.with_format('png').url}) | "
            f"[JPG]({user.banner.with_format('jpg').url}) | "
            f"[WEBP]({user.banner.with_format('webp').url})"
        )
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Download Banner", url=user.banner.url, style=discord.ButtonStyle.link))
        
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Profile(bot))
