    # ================= 🎁 ১. ইনভাইট যোগ করা (Add Invite) =================
    @commands.hybrid_command(
        name="addinvite", 
        description="🎁 নির্দিষ্ট কোনো মেম্বারকে বোনাস ইনভাইট যোগ করে দিন"
    )
    @commands.has_permissions(administrator=True)
    @app_commands.describe(member="যাকে ইনভাইট দিবেন", amount="কতগুলো ইনভাইট যোগ করবেন")
    async def addinvite(self, ctx: commands.Context, member: discord.Member, amount: int):
        config = load_config()
        guild_id, user_id = str(ctx.guild.id), str(member.id)
        
        # ডাটাবেস চেক ও আপডেট
        if "invite_data" not in config: config["invite_data"] = {}
        if guild_id not in config["invite_data"]: config["invite_data"][guild_id] = {}
        if user_id not in config["invite_data"][guild_id]:
            config["invite_data"][guild_id][user_id] = {"regular": 0, "fake": 0, "leave": 0, "bonus": 0, "bots": 0}
            
        config["invite_data"][guild_id][user_id]["bonus"] += amount
        save_config(config)
        
        embed = discord.Embed(
            description=f"<:Star:1472268505238863945> সফলভাবে {member.mention}-কে **{amount}** বোনাস ইনভাইট দেওয়া হয়েছে।",
            color=get_theme_color(ctx.guild.id)
        )
        # কমান্ডদাতার নাম ও ছবি ডিসপ্লে
        embed.set_author(name=f"Action by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ================= 🗑️ ২. মেম্বার ডাটা রিসেট (Reset User) =================
    @commands.hybrid_command(
        name="resetinvite", 
        description="🗑️ নির্দিষ্ট কোনো মেম্বারের সব ইনভাইট ডাটা মুছে ফেলুন"
    )
    @commands.has_permissions(administrator=True)
    @app_commands.describe(member="যার ডাটা রিসেট করবেন")
    async def resetinvite(self, ctx: commands.Context, member: discord.Member):
        config = load_config()
        guild_id, user_id = str(ctx.guild.id), str(member.id)
        
        if guild_id in config.get("invite_data", {}) and user_id in config["invite_data"][guild_id]:
            del config["invite_data"][guild_id][user_id]
            save_config(config)
            
        embed = discord.Embed(
            description=f"<:dot:1472268394391670855> {member.mention}-এর আগের সব ইনভাইট ডাটা রিসেট করা হয়েছে।",
            color=get_theme_color(ctx.guild.id)
        )
        embed.set_author(name=f"Action by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ================= ⚠️ ৩. পুরো সার্ভার রিসেট (Reset All) =================
    @commands.hybrid_command(
        name="resetallinvite", 
        description="⚠️ পুরো সার্ভারের সবার ইনভাইট ডাটা রিসেট করুন (সাবধান!)"
    )
    @commands.has_permissions(administrator=True)
    async def resetallinvite(self, ctx: commands.Context):
        config = load_config()
        guild_id = str(ctx.guild.id)
        
        if "invite_data" in config and guild_id in config["invite_data"]:
            config["invite_data"][guild_id] = {}
            save_config(config)
            
        embed = discord.Embed(
            description=f"<:dot:1472268394391670855> **{ctx.guild.name}** সার্ভারের সবার ইনভাইট ডাটা সফলভাবে রিসেট করা হয়েছে!",
            color=discord.Color.red()
        )
        embed.set_author(name=f"Action by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
      
