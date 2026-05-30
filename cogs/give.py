import discord
from discord.ext import commands
from discord import app_commands
import re
from database import Database

class PayView(discord.ui.View):
    def __init__(self, ctx, sender, target, amount):
        super().__init__(timeout=60) # ৬০ সেকেন্ডের টাইমআউট
        self.ctx = ctx
        self.sender = sender
        self.target = target
        self.amount = amount
        self.message = None

    # টাইমআউট হলে বাটনগুলো অটোমেটিক ডিজেবল হবে
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
        
        # ব্যালেন্স আবার চেক করা যাতে স্প্যাম না করতে পারে
        if Database.get_balance(self.sender.id) < self.amount:
            return await interaction.response.send_message("❌ You don't have enough balance!", ephemeral=True)

        # ডাটাবেস আপডেট
        Database.update_balance(self.sender.id, -self.amount)
        Database.update_balance(self.target.id, self.amount)
        
        # ✅ সাকসেস এম্বেড (ছবি ২-এর মতো হুবহু)
        confirm_embed = discord.Embed(
            color=discord.Color.green(), # সাইডে সবুজ বর্ডার
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
        
        # বাটন ডিজেবল করা
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(embed=confirm_embed, view=self)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌", custom_id="cancel_btn")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.sender.id:
            return await interaction.response.send_message("❌ This isn't your transaction!", ephemeral=True)
        
        # ❌ ক্যানসেল এম্বেড (ছবি ৩-এর মতো হুবহু)
        cancel_embed = discord.Embed(
            color=discord.Color.red(), # সাইডে লাল বর্ডার
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
        
        # বাটন ডিজেবল করা এবং Cancel লেখাটিকে Cancelled-এ পরিবর্তন করা
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
        """Intelligent Parser: give @user 100, give 100 @user, give @user all"""
        if not query:
            return await ctx.send("❌ **Usage:** `Nova give <@user> <amount>`")

        # ১. Regex দিয়ে ইউজার মেনশন আলাদা করা (<@ID>)
        user_match = re.search(r'<@!?(\d+)>', query)
        if not user_match:
            return await ctx.send("❌ **Error:** Please mention a user!")

        target_id = int(user_match.group(1))
        target = ctx.guild.get_member(target_id)

        # ২. স্ট্রিং থেকে ইউজার মেনশনটা বাদ দিয়ে অ্যামাউন্ট খোঁজা
        amount_str = query.replace(user_match.group(0), "").strip()
        # অ্যামাউন্টে নাম্বার অথবা all, max, half, 1k, 1m কাজ করবে
        amount_match = re.search(r'\b(\d+[kKmMbB]?)\b|(?i)\b(all|max|half)\b', amount_str)

        if not amount_match:
            return await ctx.send("❌ **Error:** Could not find a valid amount in your message.")

        # ৩. ভ্যালিডেশন
        if not target: 
            return await ctx.send("❌ User not found in this server!")
        if target.id == ctx.author.id: 
            return await ctx.send("❌ You cannot pay yourself!")
        if target.bot: 
            return await ctx.send("❌ You cannot pay a bot!")

        sender_bal = Database.get_balance(ctx.author.id)
        val = amount_match.group(0).lower()

        # ৪. অ্যামাউন্ট ক্যালকুলেশন (all, half এবং k, m, b সাপোর্ট)
        if val in ["all", "max"]: 
            amount_val = sender_bal
        elif val == "half": 
            amount_val = sender_bal // 2
        else:
            if val[-1] in ['k', 'm', 'b']:
                multipliers = {'k': 1000, 'm': 1000000, 'b': 1000000000}
                amount_val = int(float(val[:-1]) * multipliers[val[-1]])
            else:
                amount_val = int(val)

        if amount_val <= 0: 
            return await ctx.send("❌ Amount must be at least 1!")
        if amount_val > sender_bal: 
            return await ctx.send(f"❌ Low balance! You only have **`{sender_bal:,}`** currency.")

        # ৫. মেইন পেন্ডিং এম্বেড (ছবি ১-এর মতো হুবহু)
        embed = discord.Embed(
            color=0x2b2d31, # ডিসকর্ডের ডিফল্ট ডার্ক ব্যাকগ্রাউন্ড কালার (যাতে কোনো কালার দেখা না যায়)
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

        # মেসেজ কন্টেন্ট
        msg_content = f"💳 | {ctx.author.mention} Sent **{amount_val:,}** currency to {target.mention}"

        view = PayView(ctx, ctx.author, target, amount_val)
        message = await ctx.send(content=msg_content, embed=embed, view=view)
        
        # টাইমআউট হ্যান্ডেল করার জন্য ভিউতে মেসেজের অবজেক্ট পাঠানো হলো
        view.message = message

async def setup(bot):
    await bot.add_cog(PaySystem(bot))
