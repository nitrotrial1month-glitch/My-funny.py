import discord
from discord.ext import commands
from discord import app_commands
import re
from database import Database

class PayView(discord.ui.View):
    def __init__(self, ctx, sender, target, amount):
        super().__init__(timeout=60) # ৬০ সেকেন্ড পর বাটন কাজ করা বন্ধ করবে
        self.ctx = ctx
        self.sender = sender
        self.target = target
        self.amount = amount
        self.message = None

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self)
        except:
            pass

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, emoji="✅", custom_id="confirm_btn")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.sender.id:
            return await interaction.response.send_message("❌ This isn't your transaction!", ephemeral=True)
        
        if Database.get_balance(self.sender.id) < self.amount:
            return await interaction.response.send_message("❌ You don't have enough balance!", ephemeral=True)

        # ডাটাবেস আপডেট
        Database.update_balance(self.sender.id, -self.amount)
        Database.update_balance(self.target.id, self.amount)
        
        # ✅ সাকসেস এম্বেড
        confirm_embed = discord.Embed(
            color=discord.Color.green(),
            description=(
                f"---------------------------\n"
                f"💰 transaction Amount: **{self.amount:,}** currency!!\n\n"
                f"⚠️ Violation Warning:\n"
                f"Cowoncy never accepts transactions with real money, cryptocurrency, nitro, or anything similar.\n\n"
                f"You have Confirmed the transaction, ✅ Confirmed.\n"
                f"---------------------------"
            )
        )
        confirm_embed.set_footer(text=f"{self.sender.name}, you are about to give currency to {self.target.name}", icon_url=self.sender.display_avatar.url)
        
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(embed=confirm_embed, view=self)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌", custom_id="cancel_btn")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.sender.id:
            return await interaction.response.send_message("❌ This isn't your transaction!", ephemeral=True)
        
        # ❌ ক্যানসেল এম্বেড
        cancel_embed = discord.Embed(
            color=discord.Color.red(),
            description=(
                f"---------------------------\n"
                f"💰 transaction Amount: **{self.amount:,}** currency!!\n\n"
                f"⚠️ Violation Warning:\n"
                f"Cowoncy never accepts transactions with real money, cryptocurrency, nitro, or anything similar.\n\n"
                f"You have canceled your transaction. ❌ Canceled.\n"
                f"---------------------------"
            )
        )
        cancel_embed.set_footer(text=f"{self.sender.name}, you are about to give currency to {self.target.name}", icon_url=self.sender.display_avatar.url)
        
        for child in self.children:
            child.disabled = True
            if child.custom_id == "cancel_btn":
                child.label = "Cancelled"

        await interaction.response.edit_message(embed=cancel_embed, view=self)
        self.stop()


class PaySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="give", aliases=["pay", "send"], description="Give currency to another user")
    @app_commands.describe(query="Type User and Amount (e.g., @user 100 or 100 @user)")
    async def give(self, ctx: commands.Context, *, query: str = None):
        # 🟢 স্ল্যাশ কমান্ডে "Application did not respond" ফিক্স করার জন্য defer() করা হলো
        await ctx.defer() 

        if not query:
            return await ctx.send("❌ **Usage:** `/give <@user> <amount>`")

        target = None
        amount_str = None

        # 🟢 Smart Parser: ইনপুটকে স্পেস দিয়ে ভাগ করে ইউজার এবং অ্যামাউন্ট খুঁজবে
        parts = query.split()
        for part in parts:
            try:
                # যদি এটি কোনো ইউজার আইডি, মেনশন বা নাম হয়
                found_member = await commands.MemberConverter().convert(ctx, part)
                if not target:
                    target = found_member
                    continue
            except commands.MemberNotFound:
                pass
            
            # যদি ইউজার না হয়, তবে চেক করবে এটি অ্যামাউন্ট কিনা (100, 1k, all)
            if re.match(r'^(\d+[kKmMbB]?|all|max|half)$', part.lower()):
                amount_str = part.lower()

        # ভ্যালিডেশন
        if not target:
            return await ctx.send("❌ **Error:** Could not find the user. Please mention them properly.")
        if not amount_str:
            return await ctx.send("❌ **Error:** Please provide a valid amount (e.g., 100, 1k, all).")
        if target.id == ctx.author.id: 
            return await ctx.send("❌ You cannot pay yourself!")
        if target.bot: 
            return await ctx.send("❌ You cannot pay a bot!")

        sender_bal = Database.get_balance(ctx.author.id)

        # অ্যামাউন্ট ক্যালকুলেশন
        if amount_str in ["all", "max"]: 
            amount_val = sender_bal
        elif amount_str == "half": 
            amount_val = sender_bal // 2
        else:
            if amount_str[-1] in ['k', 'm', 'b']:
                multipliers = {'k': 1000, 'm': 1000000, 'b': 1000000000}
                amount_val = int(float(amount_str[:-1]) * multipliers[amount_str[-1]])
            else:
                amount_val = int(amount_str)

        if amount_val <= 0: 
            return await ctx.send("❌ Amount must be at least 1!")
        if amount_val > sender_bal: 
            return await ctx.send(f"❌ Low balance! You only have **`{sender_bal:,}`** currency.")

        # ⏳ মেইন পেন্ডিং এম্বেড
        embed = discord.Embed(
            color=0x2b2d31,
            description=(
                f"---------------------------\n"
                f"💰 Transaction Amount: **{amount_val:,}** currency\n\n"
                f"⚠️ Violation Warning:\n"
                f"Cowoncy never accepts transactions with real money, cryptocurrency, nitro, or anything similar.\n\n"
                f"To confirm the transaction, press ✅ Confirm.\n"
                f"To cancel the transaction, press ❌ Cancel.\n"
                f"---------------------------"
            )
        )
        embed.set_footer(text=f"{ctx.author.name}, you are about to give currency to {target.name}", icon_url=ctx.author.display_avatar.url)

        msg_content = f"💳 | {ctx.author.mention} Sent **{amount_val:,}** currency to {target.mention}"

        view = PayView(ctx, ctx.author, target, amount_val)
        
        # যেহেতু defer() করা হয়েছে, তাই সরাসরি ctx.send কাজ করবে এবং মেসেজ পাঠাবে
        message = await ctx.send(content=msg_content, embed=embed, view=view)
        view.message = message

async def setup(bot):
    await bot.add_cog(PaySystem(bot))
