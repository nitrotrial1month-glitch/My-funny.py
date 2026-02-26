import discord
from discord.ext import commands
from discord import app_commands
import re
import datetime
from database import Database
from utils import get_theme_color

class PayView(discord.ui.View):
    """Handles button interactions with dynamic color and text updates"""
    def __init__(self, ctx, sender, target, amount, cash_emoji):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.sender = sender
        self.target = target
        self.amount = amount
        self.cash_emoji = cash_emoji

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.sender.id:
            return await interaction.response.send_message("Only the sender can confirm!", ephemeral=True)
        
        sender_bal = Database.get_balance(self.sender.id)
        if sender_bal < self.amount:
            return await interaction.response.send_message("Transaction failed: Low balance.", ephemeral=True)

        # Database Process
        Database.update_balance(self.sender.id, -self.amount)
        Database.update_balance(self.target.id, self.amount)
        
        # ✅ CONFIRMED: Green Style
        confirm_embed = discord.Embed(
            description=(
                f"To confirm this transaction, click ✅ Confirm.\n"
                f"To cancel this transaction, click ❌ Cancel.\n\n"
                f"⚠️ *It is against our rules to trade cowoncy for anything of monetary value. "
                f"This includes real money, crypto, nitro, or anything similar. You will be **banned** for doing so.*\n\n"
                f"**{self.sender.mention} will give {self.target.mention}:**\n"
                f"**` {self.amount:,} `** {self.cash_emoji}"
            ),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        confirm_embed.set_author(name=f"{self.sender.name}, you are about to give cowoncy to {self.target.name}", icon_url=self.sender.display_avatar.url)
        confirm_embed.set_footer(text=f"{self.sender.name} accepted!")
        
        header_text = f"💳 | **{self.sender.mention}** sent **{self.amount:,}** {self.cash_emoji} to **{self.target.mention}**!"
        await interaction.response.edit_message(content=header_text, embed=confirm_embed, view=None)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.sender.id:
            return await interaction.response.send_message("Only the sender can cancel!", ephemeral=True)
        
        # ❌ CANCELED: Red Style
        cancel_embed = discord.Embed(
            description=(
                f"To confirm this transaction, click ✅ Confirm.\n"
                f"To cancel this transaction, click ❌ Cancel.\n\n"
                f"⚠️ *It is against our rules to trade cowoncy for anything of monetary value. "
                f"This includes real money, crypto, nitro, or anything similar. You will be **banned** for doing so.*\n\n"
                f"**{self.sender.mention} will give {self.target.mention}:**\n"
                f"**` {self.amount:,} `** {self.cash_emoji}"
            ),
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        cancel_embed.set_author(name=f"{self.sender.name}, you are about to give cowoncy to {self.target.name}", icon_url=self.sender.display_avatar.url)
        
        header_text = f"❌ | **{self.sender.mention}** declined the transaction"
        await interaction.response.edit_message(content=header_text, embed=cancel_embed, view=None)
        self.stop()

class PaySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cash_emoji = "<:Nova:1453460518764548186>" #

    @commands.hybrid_command(name="give", aliases=["pay", "send"])
    async def give(self, ctx: commands.Context, arg1: str = None, arg2: str = None):
        """Intelligent Parser for: Nova give @user 100, Nova give 100 @user, etc."""
        if not arg1:
            return await ctx.send("❌ Usage: `Nova give <user> <amount>`")

        target = None
        amount_val = None
        sender_bal = Database.get_balance(ctx.author.id)

        # Parsing Logic
        def parse_member(text):
            uid = re.sub(r'[^0-9]', '', text)
            return ctx.guild.get_member(int(uid)) if uid else None

        def parse_amount(text, bal):
            if text.lower() in ["all", "max"]: return bal
            num = re.sub(r'[^0-9]', '', text)
            return int(num) if num else None

        # Check if arg1 is Mention/ID or Amount
        if "<@" in arg1 or not arg1.isdigit():
            target = parse_member(arg1)
            amount_val = parse_amount(arg2, sender_bal) if arg2 else None
        else:
            amount_val = parse_amount(arg1, sender_bal)
            target = parse_member(arg2) if arg2 else None

        # Validations
        if not target or amount_val is None:
            return await ctx.send("❌ Please mention a user and an amount. Example: `Nova give @user 100`")
        if target.id == ctx.author.id: return await ctx.send("❌ You can't give money to yourself!")
        if amount_val <= 0: return await ctx.send("❌ Minimum transfer is 1!")
        if amount_val > sender_bal:
            return await ctx.send(f"❌ Low balance! You only have {self.cash_emoji} `{sender_bal:,}`")

        # Initial Embed
        theme_color = get_theme_color(ctx.guild.id)
        embed = discord.Embed(
            description=(
                f"To confirm this transaction, click ✅ Confirm.\n"
                f"To cancel this transaction, click ❌ Cancel.\n\n"
                f"⚠️ *It is against our rules to trade cowoncy for anything of monetary value. "
                f"This includes real money, crypto, nitro, or anything similar. You will be **banned** for doing so.*\n\n"
                f"**{ctx.author.mention} will give {target.mention}:**\n"
                f"**` {amount_val:,} `** {self.cash_emoji}"
            ),
            color=theme_color,
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=f"{ctx.author.name}, you are about to give cowoncy to {target.name}", icon_url=ctx.author.display_avatar.url)

        view = PayView(ctx, ctx.author, target, amount_val, self.cash_emoji)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(PaySystem(bot))
        
