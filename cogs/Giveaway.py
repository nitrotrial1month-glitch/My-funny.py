import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import asyncio
import random
import datetime
from utils import get_theme_color # আপনার utils থেকে কালার নিবে

# ================= 1. TIME CONVERTER (সময় কনভার্টার) =================
def convert_time(time_str):
    pos = ["s", "m", "h", "d"]
    time_dict = {"s": 1, "m": 60, "h": 3600, "d": 3600*24}
    unit = time_str[-1]
    if unit not in pos:
        return -1
    try:
        val = int(time_str[:-1])
    except:
        return -2
    return val * time_dict[unit]

# ================= 2. GIVEAWAY VIEW (জয়েন বাটন) =================
class GiveawayView(View):
    def __init__(self, bot, timeout_seconds, prize, host):
        super().__init__(timeout=None) # বাটন সবসময় কাজ করবে
        self.bot = bot
        self.entrants = set() # ডুপ্লিকেট আটকাতে সেট ব্যবহার করা হলো
        self.ended = False
        self.prize = prize
        self.host = host

    @discord.ui.button(label="🎉 Join Giveaway", style=discord.ButtonStyle.primary, custom_id="join_btn")
    async def join_button(self, interaction: discord.Interaction, button: Button):
        if self.ended:
            await interaction.response.send_message("❌ This giveaway has ended!", ephemeral=True)
            return

        if interaction.user.id in self.entrants:
            # যদি আগে থেকেই জয়েন থাকে, তবে লিভ নিবে
            self.entrants.remove(interaction.user.id)
            await interaction.response.send_message("❌ You left the giveaway.", ephemeral=True)
        else:
            # জয়েন করবে
            self.entrants.add(interaction.user.id)
            await interaction.response.send_message("✅ **Entry Confirmed!** Good Luck!", ephemeral=True)
        
        # বাটন লেবেল আপডেট (কতজন জয়েন করেছে দেখাবে)
        button.label = f"🎉 Join ({len(self.entrants)})"
        await interaction.message.edit(view=self)

# ================= 3. DASHBOARD (এডমিন কন্ট্রোল প্যানেল) =================
class GiveawayDashboard(View):
    def __init__(self, view, message):
        super().__init__(timeout=None)
        self.gv_view = view # মেইন গিভঅ্যাওয়ে ভিউ
        self.message = message # গিভঅ্যাওয়ে মেসেজ

    @discord.ui.button(label="🛑 End Now", style=discord.ButtonStyle.danger)
    async def end_now(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.gv_view.host.id:
            await interaction.response.send_message("❌ Only the host can end this!", ephemeral=True)
            return
        
        await interaction.response.send_message("✅ Ending giveaway...", ephemeral=True)
        self.gv_view.ended = True # লুপ বন্ধ করার জন্য
        self.stop() # ড্যাশবোর্ড বন্ধ

    @discord.ui.button(label="🎲 Reroll", style=discord.ButtonStyle.secondary)
    async def reroll(self, interaction: discord.Interaction, button: Button):
        if not self.gv_view.entrants:
            await interaction.response.send_message("❌ No entrants to reroll!", ephemeral=True)
            return
        
        winner_id = random.choice(list(self.gv_view.entrants))
        await self.message.channel.send(f"🎲 **Reroll!** The new winner is <@{winner_id}>! 🎉")
        await interaction.response.send_message("✅ Reroll successful!", ephemeral=True)

# ================= 4. MAIN SYSTEM =================
class GiveawaySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="gstart", description="🎁 Start a Premium Giveaway with Dashboard")
    @app_commands.describe(prize="What is the prize?", duration="Time (e.g., 10s, 1m, 1h)", winners="Number of winners")
    async def gstart(self, interaction: discord.Interaction, prize: str, duration: str, winners: int = 1):
        # ১. সময় চেক
        seconds = convert_time(duration)
        if seconds == -1:
            await interaction.response.send_message("❌ Invalid time format! Use s/m/h/d (e.g., `10m`).", ephemeral=True)
            return

        # ২. এম্বেড ডিজাইন (UNIQUE LOOK)
        end_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        timestamp = int(end_time.timestamp())
        
        embed = discord.Embed(
            title="🎁 **GRAND GIVEAWAY EVENT**",
            description=(
                f"### 💎 Prize: **{prize}**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👑 **Host:** {interaction.user.mention}\n"
                f"🏆 **Winners:** `{winners}`\n"
                f"⏳ **Ends:** <t:{timestamp}:R>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👇 Click the button below to join!"
            ),
            color=discord.Color.purple() # প্রিমিয়াম পার্পল কালার
        )
        embed.set_thumbnail(url="https://media.tenor.com/J_wWw7jJbPIAAAAi/giveaway-gift.gif") # অ্যানিমেটেড গিফ
        embed.set_footer(text="Nova Premium Giveaways")

        # ৩. মেসেজ পাঠানো
        view = GiveawayView(self.bot, seconds, prize, interaction.user)
        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()

        # ৪. হোস্টকে ড্যাশবোর্ড দেওয়া (Secret Panel)
        dashboard = GiveawayDashboard(view, message)
        await interaction.followup.send(
            content=f"⚙️ **Giveaway Dashboard for: {prize}**\nUse this to control the event.",
            view=dashboard,
            ephemeral=True
        )

        # ৫. টাইমার লুপ (Countdown)
        while seconds > 0:
            if view.ended: break # ড্যাশবোর্ড থেকে এন্ড করলে লুপ ভাঙবে
            await asyncio.sleep(5) # প্রতি ৫ সেকেন্ডে চেক করবে
            seconds -= 5

        # ৬. গিভঅ্যাওয়ে শেষ করা
        view.ended = True
        
        # বাটন ডিসএবল করা
        for child in view.children:
            child.disabled = True
            child.label = "Giveaway Ended"
            child.style = discord.ButtonStyle.secondary
        
        await message.edit(view=view)

        # ৭. উইনার সিলেক্ট করা
        entrants_list = list(view.entrants)
        
        if len(entrants_list) < winners:
            await message.reply(f"❌ **Giveaway Cancelled!** Not enough entrants for **{prize}**.")
            return

        # র‍্যান্ডম উইনার
        winner_ids = random.sample(entrants_list, winners)
        winners_mention = ", ".join([f"<@{uid}>" for uid in winner_ids])

        # ৮. রেজাল্ট ঘোষণা (Unique Style)
        result_embed = discord.Embed(
            title="🎉 **GIVEAWAY ENDED** 🎉",
            description=(
                f"🎁 **Prize:** {prize}\n"
                f"👑 **Winner(s):** {winners_mention}\n"
                f"👥 **Total Entries:** {len(entrants_list)}"
            ),
            color=discord.Color.gold()
        )
        await message.reply(content=f"Congratulations {winners_mention}!", embed=result_embed)

async def setup(bot):
    await bot.add_cog(GiveawaySystem(bot))
  
