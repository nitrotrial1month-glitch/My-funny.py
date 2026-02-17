import discord
from discord.ext import commands
from discord import app_commands, ui
import json
import os
from datetime import datetime, timedelta

# --- কনফিগারেশন ---
PREMIUM_FILE = "premium.json"
OWNER_ID = 1311355680640208926  # আপনার দেওয়া Discord ID

# পেমেন্ট ইনফরমেশন (আপনার দেওয়া UPI সহ)
PAYMENT_INFO = """
**Payment Methods:**

🇮🇳 **India (UPI):**
📱 `UPI ID:` **kstomh05@okicici** (GPay / PhonePe / Paytm)

Nitro:` Gift Classic/Boost (DM Owner)
"""

class PremiumSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- ১. ডাটা লোড ও সেভ ---
    def get_data(self):
        if not os.path.exists(PREMIUM_FILE):
            return {"users": {}, "servers": {}}
        try:
            with open(PREMIUM_FILE, "r") as f:
                return json.load(f)
        except:
            return {"users": {}, "servers": {}}

    def save_data(self, data):
        with open(PREMIUM_FILE, "w") as f:
            json.dump(data, f, indent=4)

    # --- ২. প্রিমিয়াম ডাটাবেসে যোগ করা ---
    def add_premium_db(self, target_id, type, duration_days):
        data = self.get_data()
        category = "users" if type == "User" else "servers"
        
        # বর্তমান সময় + মেয়াদ = এক্সপায়ার ডেট
        expire_date = datetime.now() + timedelta(days=duration_days)
        
        data[category][str(target_id)] = {
            "plan": "premium",
            "start_at": datetime.now().isoformat(),
            "expire_at": expire_date.isoformat()
        }
        self.save_data(data)

    # --- ৩. মেইন কমান্ড (Buy Premium Panel) ---
    @commands.hybrid_command(name="buypremium", description="Buy Premium for User or Server")
    async def buy_premium(self, ctx):
        embed = discord.Embed(
            title="💎 Premium Store",
            description=f"{PAYMENT_INFO}\n\n👇 **Select your Plan below:**",
            color=0xffd700 # Gold Color
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/6941/6941697.png") # Premium Icon
        
        # প্রাইস লিস্ট
        embed.add_field(name="👤 User Premium", value="• 1 Month: ₹80 / 100৳\n• 1 Year: ₹800 / 1000৳", inline=True)
        embed.add_field(name="🏰 Server Premium", value="• 1 Month: ₹150 / 200৳\n• 1 Year: ₹1500 / 2000৳", inline=True)
        
        view = PremiumSelectView(self.bot)
        await ctx.send(embed=embed, view=view)

# --- ৪. সিলেকশন বাটন (User/Server & Month/Year) ---
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

# --- ৫. পেমেন্ট ফর্ম (Modal) ---
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
        # ইউজারকে কনফার্মেশন মেসেজ
        await interaction.response.send_message("✅ **Request Sent!** Wait for Admin approval. You will get a DM shortly.", ephemeral=True)
        
        # ওনারের কাছে মেসেজ পাঠানো
        try:
            owner = await self.bot.fetch_user(OWNER_ID)
            
            # টার্গেট ইনফো বের করা
            target_id = interaction.user.id if self.p_type == "User" else interaction.guild.id
            target_name = interaction.user.name if self.p_type == "User" else interaction.guild.name
            
            embed = discord.Embed(title="🔔 New Premium Request", color=discord.Color.orange())
            embed.add_field(name="Buyer", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
            embed.add_field(name="Type", value=f"**{self.p_type}** Premium", inline=True)
            embed.add_field(name="Duration", value=self.p_duration, inline=True)
            embed.add_field(name="Target ID", value=f"`{target_id}`\nName: {target_name}", inline=False)
            embed.add_field(name="Method", value=self.method.value, inline=True)
            embed.add_field(name="TrxID/Proof", value=f"`{self.trx_id.value}`", inline=False)
            embed.set_footer(text="Accept or Decline using buttons below")

            # অ্যাপ্রুভাল ভিউ পাঠানো
            view = AdminApprovalView(self.bot, interaction.user, target_id, self.p_type, self.days)
            await owner.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"Failed to send DM to owner: {e}")

# --- ৬. ওনার অ্যাপ্রুভাল সিস্টেম (DM Buttons) ---
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
        # ১. ডাটাবেসে সেভ করা
        cog = self.bot.get_cog("PremiumSystem")
        if cog:
            cog.add_premium_db(self.target_id, self.p_type, self.days)
            
            # ২. ওনার প্যানেল আপডেট (Approved)
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.green()
            embed.add_field(name="Action", value="✅ **Approved**", inline=False)
            
            # বাটন ডিজেবল করা
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(embed=embed, view=self)
            
            # ৩. বায়ারকে মেসেজ পাঠানো
            try:
                await self.buyer.send(f"🎉 **Payment Accepted!**\nYour **{self.p_type} Premium** is now ACTIVE for **{self.days} days**.")
            except:
                pass
        else:
            await interaction.response.send_message("❌ Error: Cog not loaded properly.", ephemeral=True)

    @ui.button(label="❌ Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: ui.Button):
        # ১. ওনার প্যানেল আপডেট (Declined)
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(name="Action", value="❌ **Declined**", inline=False)
        
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)
        
        # ২. বায়ারকে মেসেজ পাঠানো
        try:
            await self.buyer.send(f"⚠️ **Payment Declined!**\nYour request for {self.p_type} Premium was rejected. Please check your TrxID/Amount and try again.")
        except:
            pass

async def setup(bot):
    await bot.add_cog(PremiumSystem(bot))
  
