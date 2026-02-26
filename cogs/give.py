import discord
from discord.ext import commands
from discord import app_commands
import typing
import re
from database import Database
from utils import get_theme_color

class PayView(discord.ui.View):
    """View for handling Confirm/Cancel buttons"""
    def __init__(self, ctx, sender, target, amount, cash_emoji):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.sender = sender
        self.target = target
        self.amount = amount
        self.cash_emoji = cash_emoji
        self.value = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.sender.id:
            return await interaction.response.send_message("This transaction isn't for you!", ephemeral=True)
        
        # Double check balance before processing
        sender_bal = Database.get_balance(self.sender.id)
        if sender_bal < self.amount:
            return await interaction.response.send_message("Transaction failed: Insufficient balance.", ephemeral=True)

        # Update Database
        Database.update_balance(self.sender.id, -self.amount)
        Database.update_balance(self.target.id, self.amount)
        
        self.value = True
        self.stop()
        
        # Success Embed style
        success_embed = discord.Embed(
            description=f"💳 | **{self.sender.name}** sent **{self.amount:,}** {self.cash_emoji} to **{self.target.name}**!",
            color=discord.Color.green()
        )
        success_embed.set_footer(text=f"Transaction ID: {interaction.message.id}")
        await interaction.response.edit_message(content=None, embed=success_embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.sender.id:
            return await interaction.response.send_message("Only the sender can cancel this.", ephemeral=True)
        
        self.value = False
        self.stop()
        
        cancel_embed = discord.Embed(
            description=f"❌ | **{self.sender.name}** declined the transaction.",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(content=None, embed=cancel_embed, view=None)

class PaySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cash_emoji = "<:Nova:1453460518764548186>" # Your custom emoji

    @commands.hybrid_command(name="give", aliases=["pay", "send"], description="Transfer coins to another user")
    @app_commands.describe(user="The user to receive coins", amount="Amount to send (e.g. 100 or 'all')")
    async def give(self, ctx: commands.Context, user: typing.Optional[discord.Member] = None, amount: str = None):
        """
        Handles: Nova give @user 100, Nova give 100 @user, Nova give@user100
        """
        # Logic to handle flexible input orders
        target = None
        final_amount = None

        # Helper to parse amount
        def parse_amount(val, balance):
            if val.lower() in ["all", "max"]: return balance
            if val.lower() == "half": return balance // 2
            try: return int(re.sub(r'[^0-9]', '', val))
            except: return None

        sender_bal = Database.get_balance(ctx.author.id)

        # Handle 'give@user100' or similar sticked inputs if prefix is 'Nova'
        if user is None and amount is not None:
            # Try to extract ID or mention and number from a single string
            match = re.search(r'<@!?(\[0-9]+)>', amount)
            num_match = re.search(r'(\[0-9]+)', amount)
            if match:
                target = ctx.guild.get_member(int(match.group(1)))
                if num_match: final_amount = parse_amount(num_match.group(1), sender_bal)
        elif user and amount:
            target = user
            final_amount = parse_amount(amount, sender_bal)
        elif amount is None and ctx.message.content:
            # Manual split for tricky prefix inputs like "Nova give 100 @user"
            parts = ctx.message.content.split()[2:] # Skip 'Nova' and 'give'
            for part in parts:
                if "<@" in part:
                    uid = int(re.sub(r'[^0-9]', '', part))
                    target = ctx.guild.get_member(uid)
                elif part.isdigit() or part.lower() in ["all", "max", "half"]:
                    final_amount = parse_amount(part, sender_bal)

        # Validations
        if not target or not final_amount:
            return await ctx.send(f"❌ Usage: `Nova give <user> <amount>` or `Nova give <amount> <user>`")
        if target.id == ctx.author.id:
            return await ctx.send("❌ You cannot send coins to yourself!")
        if target.bot:
            return await ctx.send("❌ You cannot send coins to a bot!")
        if final_amount <= 0:
            return await ctx.send("❌ Amount must be greater than 0!")
        if final_amount > sender_bal:
            return await ctx.send(f"❌ Insufficient balance! You have {self.cash_emoji} `{sender_bal:,}`")

        # Confirmation Embed
        theme_color = get_theme_color(ctx.guild.id)
        embed = discord.Embed(color=theme_color)
        embed.set_author(name=f"{ctx.author.name}, you are about to give coins", icon_url=ctx.author.display_avatar.url)
        embed.description = (
            f"To confirm this transaction, click **Confirm** ✅\n"
            f"To cancel this transaction, click **Cancel** ❌\n\n"
            f"⚠️ *It is against the rules to trade coins for anything of monetary value. "
            f"You will be **banned** for doing so.*\n\n"
            f"**{ctx.author.mention} will give {target.mention}:**\n"
            f"**` {final_amount:,} `** {self.cash_emoji}"
        )

        view = PayView(ctx, ctx.author, target, final_amount, self.cash_emoji)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(PaySystem(bot))
                                                   
