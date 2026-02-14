import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import asyncio
import random
import datetime
from utils import get_theme_color

# ================= 1. CUSTOM EMOJIS (আপনার দেওয়া ইমোজি) =================
ARROW = "<a:emoji_53:1429365638673072300>"
GIVEAWAY_ICON = "<a:Giveaway2:1470530788322705599>"
GIFT_ANIM = "<a:gift:1470830259329826826>"

# ================= 2. TIME CONVERTER =================
def convert_time(time_str):
    pos = ["s", "m", "h", "d"]
    time_dict = {"s": 1, "m": 60, "h": 3600, "d": 3600*24}
    unit = time_str[-1]
    if unit not in pos: return -1
    try: val = int(time_str[:-1])
    except: return -2
    return val * time_dict[unit]

# ================= 3. EDIT MODALS (লাইভ এডিট করার জন্য) =================
class EditGiveawayModal(Modal, title="✏️ Edit Giveaway Details"):
    prize = TextInput(label="New Prize Name", required=True)
    image = TextInput(label="New GIF/Image URL", required=False, placeholder="https://...")
    
    def __init__(self, view, embed_message):
        super().__init__()
        self.gv_view = view
        self.embed_message = embed_message
        # আগের ভ্যালুগুলো প্রি-ফিল করা
        self.prize.default = view.prize
        self.image.default = view.image_url

    async def on_submit(self, interaction: discord.Interaction):
        # ডাটা আপডেট
        self.gv_view.prize = self.prize.value
        if self.image.value: self.gv_view.image_url = self.image.value
        
        # এম্বেড আপডেট
        await self.gv_view.update_embed(self.embed_message)
        await interaction.response.send_message("✅ **Giveaway Updated Successfully!**", ephemeral=True)

# ================= 4. DASHBOARD VIEW (লুকানো কন্ট্রোল প্যানেল) =================
class HostDashboard(View):
    def __init__(self, gv_view, message):
        super().__init__(timeout=None)
        self.gv_view = gv_view
        self.message = message

    @discord.ui.button(label="✏️ Edit Info", style=discord.ButtonStyle.primary, row=0)
    async def edit_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(EditGiveawayModal(self.gv_view, self.message))

    @discord.ui.button(label="🛑 End Fast", style=discord.ButtonStyle.danger, row=0)
    async def end_btn(self, interaction: discord.Interaction, button: Button):
        self.gv_view.time_left = 0 # লুপ ব্রেক করবে
        await interaction.response.send_message("✅ Ending giveaway immediately...", ephemeral=True)
        self.stop()

    @discord.ui.button(label="🎲 Reroll", style=discord.ButtonStyle.secondary, row=1)
    async def reroll_btn(self, interaction: discord.Interaction, button: Button):
        if not self.gv_view.entrants:
            await interaction.response.send_message("❌ No entries found!", ephemeral=True)
            return
        winner = random.choice(list(self.gv_view.entrants))
        await self.message.channel.send(f"{GIFT_ANIM} **Reroll Winner:** <@{winner}>! Congratulations!")
        await interaction.response.send_message("✅ Reroll Complete!", ephemeral=True)

# ================= 5. PUBLIC GIVEAWAY VIEW (জয়েন বাটন) =================
class GiveawayView(View):
    def __init__(self, bot, prize, host, end_timestamp, winners, image_url):
        super().__init__(timeout=None)
        self.bot = bot
        self.prize = prize
        self.host = host
        self.end_timestamp = end_timestamp
        self.winners_count = winners
        self.image_url = image_url
        
        self.entrants = set()
        self.ended = False
        self.time_left = 999 # প্লেসহোল্ডার

    async def update_embed(self, message):
        # প্রিমিয়াম ডিজাইন
        embed = discord.Embed(
            title=f"{GIVEAWAY_ICON} **PREMIUM GIVEAWAY EVENT**",
            description=(
                f"### {self.prize}\n"
                f"{ARROW} **Host:** {self.host.mention}\n"
                f"{ARROW} **Winners:** `{self.winners_count}`\n"
                f"{ARROW} **Ends:** <t:{int(self.end_timestamp)}:R>\n"
                f"{ARROW} **Status:** `🟢 Active`\n\n"
                f"👇 **React with {GIFT_ANIM} below to enter!**"
            ),
            color=0x2b2d31 # ডার্ক প্রিমিয়াম কালার
        )
        if self.image_url:
            embed.set_image(url=self.image_url)
        embed.set_footer(text=f"Total Entries: {len(self.entrants)} • Nova System")
        
        await message.edit(embed=embed, view=self)

    @discord.ui.button(emoji=discord.PartialEmoji.from_str(GIFT_ANIM), label="Join Entry", style=discord.ButtonStyle.secondary, custom_id="join_gv")
    async def join_giveaway(self, interaction: discord.Interaction, button: Button):
        if self.ended:
            return await interaction.response.send_message("❌ Giveaway Ended!", ephemeral=True)

        if interaction.user.id in self.entrants:
            self.entrants.remove(interaction.user.id)
            await interaction.response.send_message(f"❌ You left the giveaway for **{self.prize}**.", ephemeral=True)
        else:
            self.entrants.add(interaction.user.id)
            await interaction.response.send_message(f"✅ **Entry Confirmed!** You joined for **{self.prize}**.", ephemeral=True)
        
        # বাটন লেবেল আপডেট
        button.label = f"Join ({len(self.entrants)})"
        await interaction.message.edit(view=self)

# ================= 6. MAIN SYSTEM LOGIC =================
class GiveawaySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="giveaway", description="🎁 Start a Fully Editable Premium Giveaway")
    @app_commands.describe(prize="Prize Name", duration="Duration (10s, 1m, 1h)", winners="Winner Count", image="GIF/Image URL")
    async def giveaway(self, interaction: discord.Interaction, prize: str, duration: str, winners: int = 1, image: str = None):
        
        # ১. ডিফল্ট ইমেজ (যদি না দেওয়া থাকে)
        if not image:
            image = "https://media1.tenor.com/m/K0a4qgA9wGMAAAAC/giveaway-gift.gif"

        # ২. সময় কনভার্ট
        seconds = convert_time(duration)
        if seconds < 5:
            return await interaction.response.send_message("❌ Time must be at least 5 seconds!", ephemeral=True)

        end_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        timestamp = end_time.timestamp()

        # ৩. ইনিশিয়াল এম্বেড তৈরি
        embed = discord.Embed(
            title=f"{GIVEAWAY_ICON} **PREMIUM GIVEAWAY EVENT**",
            description=(
                f"### {prize}\n"
                f"{ARROW} **Host:** {interaction.user.mention}\n"
                f"{ARROW} **Winners:** `{winners}`\n"
                f"{ARROW} **Ends:** <t:{int(timestamp)}:R>\n"
                f"{ARROW} **Status:** `🟢 Active`\n\n"
                f"👇 **React with {GIFT_ANIM} below to enter!**"
            ),
            color=0x2b2d31
        )
        embed.set_image(url=image)
        embed.set_footer(text="Total Entries: 0 • Nova System")

        # ৪. ভিউ সেটআপ
        gv_view = GiveawayView(self.bot, prize, interaction.user, timestamp, winners, image)
        await interaction.response.send_message(embed=embed, view=gv_view)
        message = await interaction.original_response()

        # ৫. সিক্রেট ড্যাশবোর্ড পাঠানো (Only Host)
        dashboard = HostDashboard(gv_view, message)
        await interaction.followup.send(
            f"⚙️ **Host Controls for: {prize}**\nUse this menu to Edit, End or Reroll.",
            view=dashboard,
            ephemeral=True
        )

        # ৬. টাইমার লুপ
        gv_view.time_left = seconds
        while gv_view.time_left > 0:
            await asyncio.sleep(5)
            gv_view.time_left -= 5

        # ৭. গিভঅ্যাওয়ে শেষ
        gv_view.ended = True
        
        # বাটন ডিসএবল করা
        for child in gv_view.children:
            child.disabled = True
            child.label = "Ended"
        
        # ফাইনাল এম্বেড আপডেট
        embed.description = (
            f"### {gv_view.prize}\n"
            f"{ARROW} **Host:** {interaction.user.mention}\n"
            f"{ARROW} **Winners:** `{gv_view.winners_count}`\n"
            f"{ARROW} **Ended:** <t:{int(timestamp)}:R>\n"
            f"{ARROW} **Status:** `🔴 Ended`"
        )
        embed.color = discord.Color.red()
        await message.edit(embed=embed, view=gv_view)

        # ৮. উইনার সিলেক্ট
        entries = list(gv_view.entrants)
        if len(entries) < gv_view.winners_count:
            await message.reply(f"❌ **Giveaway Cancelled!** Not enough entries for **{gv_view.prize}**.")
            return

        winner_ids = random.sample(entries, gv_view.winners_count)
        winner_mentions = ", ".join([f"<@{uid}>" for uid in winner_ids])

        # ৯. উইনার এনাউন্সমেন্ট
        win_embed = discord.Embed(
            title=f"🎉 **CONGRATULATIONS!** 🎉",
            description=(
                f"{GIVEAWAY_ICON} **Prize:** {gv_view.prize}\n"
                f"{GIFT_ANIM} **Winner(s):** {winner_mentions}\n"
                f"👥 **Total Entries:** {len(entries)}"
            ),
            color=discord.Color.gold()
        )
        await message.reply(f"{winner_mentions}", embed=win_embed)

async def setup(bot):
    await bot.add_cog(GiveawaySystem(bot))
