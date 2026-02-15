import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

# আপনার সাপোর্ট সার্ভারের আইডি এখানে দিন
SUPPORT_SERVER_ID = 123456789012345678  # <--- এখানে আপনার সার্ভার আইডি দিন

class HelpCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="help", 
        aliases=["commands", "cmds"], 
        description="📖 View all available commands and support info"
    )
    @app_commands.describe(command_name="The specific command you want to learn about")
    async def help(self, ctx, command_name: Optional[str] = None):
        
        # --- ১. সাপোর্ট সার্ভার ইনভাইট লিঙ্ক তৈরি ---
        support_link = "https://discord.gg/your-backup-link" # ব্যাকআপ লিঙ্ক যদি বট লিঙ্ক তৈরি করতে না পারে
        try:
            guild = self.bot.get_guild(1464995423604178968)
            if guild:
                # বটের পারমিশন থাকলে মেইন চ্যানেল থেকে লিঙ্ক তৈরি করবে
                target_channel = guild.rules_channel or guild.text_channels[0]
                invite = await target_channel.create_invite(max_age=3600, reason="Help Command Invite")
                support_link = invite.url
        except Exception:
            pass

        # সাপোর্ট বাটন তৈরি
        view = discord.ui.View()
        button = discord.ui.Button(label="Join Support Server", url=support_link, emoji="🆘")
        view.add_item(button)

        # --- ২. নির্দিষ্ট কমান্ডের ডিটেইলস দেখা ---
        if command_name:
            cmd = self.bot.get_command(command_name.lower()) or self.bot.tree.get_command(command_name.lower())
            
            if cmd:
                embed = discord.Embed(
                    title=f"🔍 Command Detail: {cmd.name.capitalize()}",
                    description=f"**Description:** {cmd.description or 'No description provided.'}",
                    color=0x2b2d31
                )
                usage = f"/{cmd.name}" if isinstance(cmd, app_commands.Command) else f"{ctx.prefix}{cmd.name}"
                embed.add_field(name="Usage", value=f"`{usage}`", inline=False)
                return await ctx.send(embed=embed, view=view)
            else:
                return await ctx.send(f"❌ Command `{command_name}` not found!", delete_after=10)

        # --- ৩. মেইন ডাইনামিক হেল্প লিস্ট ---
        embed = discord.Embed(
            title=f"✨ {self.bot.user.name} Help Menu",
            description=f"Use `{ctx.prefix}help <command>` for more details.\n\nNeed more help? Join our support server below!",
            color=0x2b2d31
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        # অটোমেটিক সব Cog এবং কমান্ড খুঁজে বের করা
        for cog_name, cog in self.bot.cogs.items():
            cmd_list = [f"`{cmd.name}`" for cmd in cog.get_commands() if not cmd.hidden]
            
            if cmd_list:
                embed.add_field(
                    name=f"📁 {cog_name}",
                    value=" ".join(cmd_list),
                    inline=False
                )

        standalone_cmds = [f"`{c.name}`" for c in self.bot.commands if c.cog is None and not c.hidden]
        if standalone_cmds:
            embed.add_field(name="⚙️ Others", value=" ".join(standalone_cmds), inline=False)

        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        
        # মেসেজ পাঠানো (সাথে বাটন ভিউ)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(HelpCommand(bot))
                              
