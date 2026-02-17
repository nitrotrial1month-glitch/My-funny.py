import discord
from discord.ext import commands
from discord import app_commands, ui
from datetime import datetime
import os

# 👇 ডাটাবেস ইমপোর্ট
from database import Database

# আপনার কনফিগারেশন
OWNER_ID = 1311355680640208926
PAYMENT_INFO = """
**Payment Methods:**

🇮🇳 **India (UPI):**
📱 `UPI ID:` **kstomh05@okicici** (GPay / PhonePe / Paytm)

🌍 **International:**
🎁 `Nitro:` Gift Classic/Boost (DM Owner)
"""

class PremiumSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- ১. ডাটাবেসে প্রিমিয়াম যোগ করা ---
    def add_premium_db(self, target_id, type, duration_days):
        # সরাসরি ডাটাবেস ফাংশন কল করা হচ্ছে
        Database.add_premium(target_id, type, duration_days)

    # --- ২. মেইন কমান্ড (Buy Premium Panel) ---
    @commands.hybrid_command(name="buypremium", description="Buy Premium for User or Server")
    async def buy_premium(self, ctx):
        embed = discord.Embed(
            title="💎 Premium Store",
            description=f"{PAYMENT_INFO}\n\n👇 **Select your Plan below:**",
            color=0xffd700
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/6941/6941697.png")
        
        embed.add_field(name="👤 User Premium", value="• 1 Month: ₹80 / 100৳\n• 1 Year: ₹800 / 1000৳", inline=True)
        embed.add_field(name="🏰 Server Premium", value="• 1 Month: ₹150 / 200৳\n• 1 Year: ₹1500 / 2000৳", inline=True)
        
        view = PremiumSelectView(self.bot)
        await ctx.send(embed=embed, view=view)

# --- ৩. সিলেকশন বাটন ---
class PremiumSelectView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(label="👤 User (1 Month)", style=discord.ButtonStyle.primary, custom_id="user_1m", emoji="👤")
    async def user_monthly(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(PaymentModal(self.bot, "User", "1 Month", 30))

    @ui.button(label="👤 User (1 Year)", style=discord.ButtonStyle.primary, custom_id="user_1y", emoji="👑")
    async def user_yearly(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(PaymentModal(self.bot, "User", "1 Year", 365))

    @ui.button(label="🏰 Server (1 Month)", style=discord.ButtonStyle.success, custom_id="server_1m", emoji="🏰")
    async def server_monthly(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(PaymentModal(self.bot, "Server", "1 Month", 30))

    @ui.button(label="🏰 Server (1 Year)", style=discord.ButtonStyle.success, custom_id="server_1y", emoji="🌟")
    async def server_yearly(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(PaymentModal(self.bot, "Server", "1 Year", 365))

# --- ৪. পেমেন্ট ফর্ম (Modal) ---
class PaymentModal(ui.Modal):
    def __init__(self, bot, p_type, p_duration, days):
        self.bot = bot
        self.p_type = p_type
        self.p_duration = p_duration
        self.days = days
        title = f"Confirm {p_type} Premium ({p_duration})"
        super().__init__(title=title)

    trx_id = ui.TextInput(label="Transaction ID / Screenshot Link", placeholder="Enter TrxID or Link...", required=True)
    method = ui.TextInput(label="Payment Method", placeholder="UPI / Bkash / Crypto", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ **Request Sent!** Wait for Admin approval via DM.", ephemeral=True)
        
        try:
            owner = await self.bot.fetch_user(OWNER_ID)
            target_id = interaction.user.id if self.p_type == "User" else interaction.guild.id
            target_name = interaction.user.name if self.p_type == "User" else interaction.guild.name
            
            embed = discord.Embed(title="🔔 New Premium Request", color=discord.Color.orange())
            embed.add_field(name="Buyer", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
            embed.add_field(name="Type", value=f"**{self.p_type}** Premium", inline=True)
            embed.add_field(name="Duration", value=self.p_duration, inline=True)
            embed.add_field(name="Target ID", value=f"`{target_id}`\nName: {target_name}", inline=False)
            embed.add_field(name="Method", value=self.method.value, inline=True)
            embed.add_field(name="TrxID/Proof", value=f"`{self.trx_id.value}`", inline=False)
            
            view = AdminApprovalView(self.bot, interaction.user, target_id, self.p_type, self.days)
            await owner.send(embed=embed, view=view)
        except Exception as e:
            print(f"Failed to DM Owner: {e}")

# --- ৫. ওনার অ্যাপ্রুভাল সিস্টেম ---
class AdminApprovalView(ui.View):
    def __init__(self, bot, buyer_user, target_id, p_type, days):
        super().__init__(timeout=None)
        self.bot = bot
        self.buyer = buyer_user
        self.target_id = target_id
        self.p_type = p_type
        self.days = days

    @ui.button(label="✅ Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: ui.Button):
        # ডাটাবেসে সেভ করা
        Database.add_premium(self.target_id, self.p_type, self.days)
            
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name="Action", value="✅ **Approved & Saved to DB**", inline=False)
        
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)
        
        try: await self.buyer.send(f"🎉 **Approved!** Your **{self.p_type} Premium** is active for **{self.days} days**.")
        except: pass

    @ui.button(label="❌ Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: ui.Button):
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(name="Action", value="❌ **Declined**", inline=False)
        
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)
        
        try: await self.buyer.send(f"⚠️ **Declined.** Check payment details and try again.")
        except: pass

async def setup(bot):
    await bot.add_cog(PremiumSystem(bot))
               
