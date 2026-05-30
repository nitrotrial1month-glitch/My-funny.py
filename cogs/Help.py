import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

SUPPORT_SERVER_ID = 1464995423604178968

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
        support_link = "https://discord.gg/your-backup-link"
        
        try:
            guild = self.bot.get_guild(SUPPORT_SERVER_ID)
            if guild:
                target_channel = guild.rules_channel or guild.text_channels[0]
                if target_channel:
                    invite = await target_channel.create_invite(max_age=3600, reason="Help Command Invite")
                    support_link = invite.url
        except Exception:
            pass 

        # সাপোর্ট বাটন তৈরি
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Join Support Server", url=support_link, emoji="🆘"))

        # --- ২. নির্দিষ্ট কমান্ডের ডিটেইলস দেখা ---
        if command_name:
            cmd = self.bot.get_command(command_name.lower())
            
            if cmd:
                desc = cmd.help or cmd.description or 'No description provided.'
                embed = discord.Embed(
                    title=f"🔍 Command Detail: {cmd.name.capitalize()}",
                    description=f"**Description:** {desc}",
                    color=0x2b2d31
                )
                usage_prefix = f"/{cmd.name}" if hasattr(cmd, "app_command") else f"{ctx.prefix}{cmd.name}"
                signature = f" {cmd.signature}" if cmd.signature else ""
                embed.add_field(name="Usage", value=f"`{usage_prefix}{signature}`", inline=False)
                
                if cmd.aliases:
                    embed.add_field(name="Aliases", value=", ".join([f"`{a}`" for a in cmd.aliases]), inline=False)
                    
                return await ctx.send(embed=embed, view=view)
            else:
                return await ctx.send(f"❌ Command `{command_name}` not found!", ephemeral=True)

        # --- ৩. মেইন ডাইনামিক হেল্প লিস্ট (২৫ লিমিট ফিক্স) ---
        embeds = [] # সব এম্বেড স্টোর করার লিস্ট
        
        def create_base_embed():
            emb = discord.Embed(
                title=f"✨ {self.bot.user.name} Help Menu",
                description=f"Use `{ctx.prefix}help <command>` for more details.\n\nNeed more help? Join our support server below!",
                color=0x2b2d31
            )
            emb.set_thumbnail(url=self.bot.user.display_avatar.url)
            return emb

        current_embed = create_base_embed()
        field_count = 0

        # অটোমেটিক সব Cog এবং কমান্ড খুঁজে বের করা
        for cog_name, cog in self.bot.cogs.items():
            cmd_list = [f"`{cmd.name}`" for cmd in cog.get_commands() if not cmd.hidden]
            
            if cmd_list:
                # ২৫টি ফিল্ড হয়ে গেলে নতুন এম্বেড তৈরি করবে
                if field_count >= 25:
                    embeds.append(current_embed)
                    current_embed = create_base_embed()
                    field_count = 0
                
                # ভ্যালু ফিল্ডে ডিসকর্ডের ১০২৪ ক্যারেক্টার লিমিট প্রোটেকশন দেওয়া হলো
                commands_str = " ".join(cmd_list)
                if len(commands_str) > 1024:
                    commands_str = commands_str[:1020] + "..."

                current_embed.add_field(
                    name=f"📁 {cog_name}",
                    value=commands_str,
                    inline=False
                )
                field_count += 1

        standalone_cmds = [f"`{c.name}`" for c in self.bot.commands if c.cog is None and not c.hidden]
        if standalone_cmds:
            if field_count >= 25:
                embeds.append(current_embed)
                current_embed = create_base_embed()
                
            cmds_str = " ".join(standalone_cmds)
            current_embed.add_field(name="⚙️ Others", value=cmds_str[:1024], inline=False)

        # শেষের এম্বেডটি লিস্টে যোগ করা
        embeds.append(current_embed)

        # লাস্ট এম্বেডে রিকোয়েস্টারের নাম সেট করা
        embeds[-1].set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        
        # মেসেজ পাঠানো (একসাথে একাধিক এম্বেড)
        await ctx.send(embeds=embeds, view=view)

async def setup(bot):
    await bot.add_cog(HelpCommand(bot))
    
