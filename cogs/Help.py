import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

# আপনার সাপোর্ট সার্ভারের আইডি এখানে দিন
SUPPORT_SERVER_ID = 1464995423604178968  # আগে আপনার কোডে এই আইডিটি ছিল

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
        support_link = "https://discord.gg/your-backup-link" # ব্যাকআপ লিঙ্ক (যদি বট ইনভাইট তৈরি করতে ফেইল করে)
        
        try:
            guild = self.bot.get_guild(SUPPORT_SERVER_ID)
            if guild:
                # বটের পারমিশন থাকলে রুলস চ্যানেল বা প্রথম টেক্সট চ্যানেল থেকে লিঙ্ক তৈরি করবে
                target_channel = guild.rules_channel or guild.text_channels[0]
                if target_channel:
                    invite = await target_channel.create_invite(max_age=3600, reason="Help Command Invite")
                    support_link = invite.url
        except Exception as e:
            print(f"⚠️ Invite Link Error: {e}") # কনসোলে এরর দেখার জন্য

        # সাপোর্ট বাটন তৈরি
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Join Support Server", url=support_link, emoji="🆘"))

        # --- ২. নির্দিষ্ট কমান্ডের ডিটেইলস দেখা ---
        if command_name:
            cmd = self.bot.get_command(command_name.lower())
            
            if cmd:
                # ডেসক্রিপশন সেট করা
                desc = cmd.help or cmd.description or 'No description provided.'
                embed = discord.Embed(
                    title=f"🔍 Command Detail: {cmd.name.capitalize()}",
                    description=f"**Description:** {desc}",
                    color=0x2b2d31
                )
                
                # হাইব্রিড/টেক্সট কমান্ড অনুযায়ী প্রিফিক্স এবং আর্গুমেন্ট (Signature) সেট করা
                usage_prefix = f"/{cmd.name}" if hasattr(cmd, "app_command") else f"{ctx.prefix}{cmd.name}"
                signature = f" {cmd.signature}" if cmd.signature else ""
                embed.add_field(name="Usage", value=f"`{usage_prefix}{signature}`", inline=False)
                
                # যদি কমান্ডের অন্য কোনো নাম (Aliases) থাকে
                if cmd.aliases:
                    embed.add_field(name="Aliases", value=", ".join([f"`{a}`" for a in cmd.aliases]), inline=False)
                    
                return await ctx.send(embed=embed, view=view)
            else:
                return await ctx.send(f"❌ Command `{command_name}` not found!", ephemeral=True)

        # --- ৩. মেইন ডাইনামিক হেল্প লিস্ট ---
        embed = discord.Embed(
            title=f"✨ {self.bot.user.name} Help Menu",
            description=f"Use `{ctx.prefix}help <command>` for more details.\n\nNeed more help? Join our support server below!",
            color=0x2b2d31
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        # অটোমেটিক সব Cog এবং কমান্ড খুঁজে বের করা
        for cog_name, cog in self.bot.cogs.items():
            # HelpCommand ক্যাটাগরিটি লিস্ট থেকে হাইড করতে চাইলে নিচের লাইনটি ব্যবহার করতে পারেন (ঐচ্ছিক)
            # if cog_name == "HelpCommand": continue 
            
            cmd_list = [f"`{cmd.name}`" for cmd in cog.get_commands() if not cmd.hidden]
            
            if cmd_list:
                embed.add_field(
                    name=f"📁 {cog_name}",
                    value=" ".join(cmd_list),
                    inline=False
                )

        # যে কমান্ডগুলো কোনো Cog-এর আন্ডারে নেই (Standalone Commands)
        standalone_cmds = [f"`{c.name}`" for c in self.bot.commands if c.cog is None and not c.hidden]
        if standalone_cmds:
            embed.add_field(name="⚙️ Others", value=" ".join(standalone_cmds), inline=False)

        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        
        # মেসেজ পাঠানো (সাথে বাটন ভিউ)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(HelpCommand(bot))
    
