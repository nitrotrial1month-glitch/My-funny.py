import discord
from discord.ext import commands
import re
from database import Database
from utils import get_theme_color

class PayView(discord.ui.View):
    def __init__(self, ctx, sender, target, amount, cash_emoji):
        super().__init__(timeout=60)
        self.ctx, self.sender, self.target = ctx, sender, target
        self.amount, self.cash_emoji = amount, cash_emoji

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.sender.id:
            return await interaction.response.send_message("This isn't your transaction!", ephemeral=True)
        
        if Database.get_balance(self.sender.id) < self.amount:
            return await interaction.response.send_message("You don't have enough balance!", ephemeral=True)

        Database.update_balance(self.sender.id, -self.amount)
        Database.update_balance(self.target.id, self.amount)
        
        # ✅ Confirmed Embed Style
        confirm_embed = discord.Embed(
            description=(
                f"To confirm this transaction, click ✅ Confirm.\nTo cancel, click ❌ Cancel.\n\n"
                f"⚠️ *It is against our rules to trade coins for real money. You will be **banned** for doing so.*\n\n"
                f"**{self.sender.mention} will give {self.target.mention}:**\n**` {self.amount:,} `** {self.cash_emoji}"
            ),
            color=discord.Color.green()
        )
        confirm_embed.set_author(name=f"{self.sender.name}, you are giving coins", icon_url=self.sender.display_avatar.url)
        confirm_embed.set_footer(text=f"{self.sender.name} accepted! • Transaction Successful")
        
        await interaction.response.edit_message(content=f"💳 | **{self.sender.mention}** sent **{self.amount:,}** {self.cash_emoji} to **{self.target.mention}**!", embed=confirm_embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.sender.id: return
        await interaction.response.edit_message(content=f"❌ | **{self.sender.mention}** declined the transaction.", embed=None, view=None)

class PaySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cash_emoji = "<:Nova:1453460518764548186>"

    @commands.hybrid_command(name="give", aliases=["pay", "send"])
    async def give(self, ctx: commands.Context, *, args: str = None):
        """Intelligent Parser: give @user 100, give 100 @user, give @user100"""
        if not args:
            return await ctx.send(f"❌ **Usage:** `Nova give <user> <amount>`")

        # ১. Regex দিয়ে ইউজার এবং অ্যামাউন্ট আলাদা করা
        user_match = re.search(r'<@!?(\d+)>', args)
        amount_match = re.search(r'\b(\d+)\b|(?i)\b(all|max|half)\b', args.replace(user_match.group(0) if user_match else "", ""))

        if not user_match or not amount_match:
            return await ctx.send(f"❌ **Error:** Could not find the user or amount in your message.")

        target = ctx.guild.get_member(int(user_match.group(1)))
        sender_bal = Database.get_balance(ctx.author.id)
        
        # ২. অ্যামাউন্ট ভ্যালু সেট করা
        val = amount_match.group(0).lower()
        if val in ["all", "max"]: amount_val = sender_bal
        elif val == "half": amount_val = sender_bal // 2
        else: amount_val = int(val)

        # ৩. ভ্যালিডেশন
        if not target: return await ctx.send("❌ User not found in this server!")
        if target.id == ctx.author.id: return await ctx.send("❌ You cannot pay yourself!")
        if amount_val <= 0: return await ctx.send("❌ Amount must be at least 1!")
        if amount_val > sender_bal: return await ctx.send(f"❌ Low balance! You have {self.cash_emoji} `{sender_bal:,}`")

        # ৪. মেইন এম্বেড (OwO Style)
        embed = discord.Embed(
            description=(
                f"To confirm this transaction, click ✅ Confirm.\nTo cancel, click ❌ Cancel.\n\n"
                f"⚠️ *It is against our rules to trade coins for real money. You will be **banned** for doing so.*\n\n"
                f"**{ctx.author.mention} will give {target.mention}:**\n**` {amount_val:,} `** {self.cash_emoji}"
            ),
            color=get_theme_color(ctx.guild.id)
        )
        embed.set_author(name=f"{ctx.author.name}, verify this transaction", icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed, view=PayView(ctx, ctx.author, target, amount_val, self.cash_emoji))

async def setup(bot):
    await bot.add_cog(PaySystem(bot))
    
