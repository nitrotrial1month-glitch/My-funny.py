import discord
from discord.ext import commands
from database import Database
from utils import get_theme_color

class PayView(discord.ui.View):
    def __init__(self, ctx, sender, target, amount, cash_emoji):
        super().__init__(timeout=60) # ৬০ সেকেন্ড পর বাটন কাজ করা বন্ধ করবে
        self.ctx = ctx
        self.sender = sender
        self.target = target
        self.amount = amount
        self.cash_emoji = cash_emoji
        self.message = None # Timeout এর জন্য মেসেজ রেফারেন্স

    # যদি ইউজার ৬০ সেকেন্ডের মধ্যে বাটনে ক্লিক না করে
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            if self.message:
                await self.message.edit(content="⏳ **Transaction timed out.**", view=self)
        except:
            pass

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        # অন্য কেউ ক্লিক করলে আটকে দেওয়া
        if interaction.user.id != self.sender.id:
            return await interaction.response.send_message("❌ This isn't your transaction!", ephemeral=True)
        
        # ব্যালেন্স পুনরায় চেক করা (যাতে বাটন স্প্যাম করে গ্লিচ না করতে পারে)
        if Database.get_balance(self.sender.id) < self.amount:
            return await interaction.response.send_message("❌ You don't have enough balance!", ephemeral=True)

        # ডাটাবেস আপডেট
        Database.update_balance(self.sender.id, -self.amount)
        Database.update_balance(self.target.id, self.amount)
        
        # সাকসেস এম্বেড
        confirm_embed = discord.Embed(
            description=(
                f"**{self.sender.mention} gave {self.target.mention}:**\n"
                f"**` {self.amount:,} `** {self.cash_emoji}\n\n"
                f"✅ *Transaction Successful*"
            ),
            color=discord.Color.green()
        )
        confirm_embed.set_author(name=f"{self.sender.name} paid {self.target.name}", icon_url=self.sender.display_avatar.url)
        
        await interaction.response.edit_message(content="💳 | **Transaction Complete!**", embed=confirm_embed, view=None)
        self.stop() # ভিউ থামিয়ে দেওয়া

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.sender.id:
            return await interaction.response.send_message("❌ This isn't your transaction!", ephemeral=True)
        
        await interaction.response.edit_message(content=f"❌ | **{self.sender.mention}** declined the transaction.", embed=None, view=None)
        self.stop()

class PaySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cash_emoji = "<:Nova:1453460518764548186>"

    # Hybrid কমান্ডে সরাসরি discord.Member এবং str কল করা হয়েছে
    @commands.hybrid_command(name="give", aliases=["pay", "send"], description="Give coins to another user")
    async def give(self, ctx: commands.Context, target: discord.Member, amount: str):
        
        # ১. ডাটাবেস থেকে সেন্ডারের ব্যালেন্স লোড
        sender_bal = Database.get_balance(ctx.author.id)
        
        # ২. অ্যামাউন্ট ক্যালকুলেশন
        val = amount.lower()
        if val in ["all", "max"]: 
            amount_val = sender_bal
        elif val == "half": 
            amount_val = sender_bal // 2
        else: 
            try:
                amount_val = int(val)
            except ValueError:
                return await ctx.send("❌ **Error:** Please provide a valid amount (e.g., `100`, `all`, `half`).")

        # ৩. ভ্যালিডেশন চেকস
        if target.id == ctx.author.id: 
            return await ctx.send("❌ You cannot pay yourself!")
        if target.bot:
            return await ctx.send("❌ You cannot pay a bot!")
        if amount_val <= 0: 
            return await ctx.send("❌ Amount must be at least 1!")
        if amount_val > sender_bal: 
            return await ctx.send(f"❌ Low balance! You only have {self.cash_emoji} **`{sender_bal:,}`**")

        # ৪. মেইন এম্বেড
        embed = discord.Embed(
            description=(
                f"To confirm this transaction, click ✅ Confirm.\nTo cancel, click ❌ Cancel.\n\n"
                f"⚠️ *It is against our rules to trade coins for real money. You will be **banned** for doing so.*\n\n"
                f"**{ctx.author.mention} will give {target.mention}:**\n**` {amount_val:,} `** {self.cash_emoji}"
            ),
            color=get_theme_color(ctx.guild.id)
        )
        embed.set_author(name=f"{ctx.author.name}, verify this transaction", icon_url=ctx.author.display_avatar.url)

        # ভিউ তৈরি এবং মেসেজ সেন্ড
        view = PayView(ctx, ctx.author, target, amount_val, self.cash_emoji)
        message = await ctx.send(embed=embed, view=view)
        
        # মেসেজ অবজেক্ট ভিউতে পাস করা (টাইমআউট ইভেন্টের জন্য)
        view.message = message

async def setup(bot):
    await bot.add_cog(PaySystem(bot))
