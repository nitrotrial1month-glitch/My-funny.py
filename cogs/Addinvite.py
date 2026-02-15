    # ================= 🎁 ADD INVITE COMMAND =================
    @commands.hybrid_command(
        name="addinvite", 
        description="🎁 Add bonus invites to a specific member"
    )
    @commands.has_permissions(administrator=True)
    @app_commands.describe(member="The user to receive bonus invites", amount="Number of invites to add")
    async def addinvite(self, ctx: commands.Context, member: discord.Member, amount: int):
        config = load_config()
        guild_id, user_id = str(ctx.guild.id), str(member.id)
        
        # ডাটাবেস চেক ও ইনিশিয়ালাইজেশন
        if "invite_data" not in config: config["invite_data"] = {}
        if guild_id not in config["invite_data"]: config["invite_data"][guild_id] = {}
        if user_id not in config["invite_data"][guild_id]:
            config["invite_data"][guild_id][user_id] = {"regular": 0, "fake": 0, "leave": 0, "bonus": 0, "bots": 0}
            
        # বোনাস ইনভাইট যোগ করা
        config["invite_data"][guild_id][user_id]["bonus"] += amount
        save_config(config)
        
        # স্টাইলিশ এম্বেড রেসপন্স
        embed = discord.Embed(
            description=f"<:Star:1472268505238863945> Successfully added **{amount}** bonus invites to {member.mention}!",
            color=get_theme_color(ctx.guild.id)
        )
        
        # অথরের নাম ও ছবি ডিসপ্লে
        embed.set_author(name=f"Action by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text="Funny Bot Security", icon_url=self.bot.user.display_avatar.url)
        
        await ctx.send(embed=embed)
