import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import asyncio
import random
import datetime
import time
from utils import get_theme_color

# 👇 ডাটাবেস ইমপোর্ট
from database import Database

# ================= 1. CUSTOM EMOJIS (আপনার ইমোজি) =================
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

# ================= 3. EDIT MODALS (ডাটাবেস সাপোর্টেড) =================
class EditGiveawayModal(Modal, title="✏️ Edit Giveaway Details"):
    prize = TextInput(label="New Prize Name", required=True)
    image = TextInput(label="New GIF/Image URL", required=False, placeholder="https://...")
    
    def __init__(self, message_id, current_prize, current_image):
        super().__init__()
        self.message_id = message_id
        self.prize.default = current_prize
        self.image.default = current_image

    async def on_submit(self, interaction: discord.Interaction):
        col = Database.get_collection("giveaways")
        
        update_data = {"prize": self.prize.value}
        if self.image.value:
            update_data["image_url"] = self.image.value
            
        # ডাটাবেস আপডেট
        col.update_one({"_id": self.message_id}, {"$set": update_data})
        
        # মেসেজ আপডেট করার জন্য কনফার্মেশন
        await interaction.response.send_message("✅ **Giveaway Updated!** (Changes will reflect on next refresh)", ephemeral=True)

# ================= 4. DASHBOARD VIEW (লুকানো কন্ট্রোল প্যানেল) =================
class HostDashboard(View):
    def __init__(self, message_id):
        super().__init__(timeout=None)
        self.message_id = message_id

    @discord.ui.button(label="✏️ Edit Info", style=discord.ButtonStyle.primary, row=0)
    async def edit_btn(self, interaction: discord.Interaction, button: Button):
        # ডাটাবেস থেকে বর্তমান তথ্য নেওয়া
        col = Database.get_collection("giveaways")
        data = col.find_one({"_id": self.message_id})
        if not data: return await interaction.response.send_message("❌ Data not found!", ephemeral=True)
        
        await interaction.response.send_modal(EditGiveawayModal(self.message_id, data["prize"], data.get("image_url", "")))

    @discord.ui.button(label="🛑 End Fast", style=discord.ButtonStyle.danger, row=0)
    async def end_btn(self, interaction: discord.Interaction, button: Button):
        col = Database.get_collection("giveaways")
        # সময় কমিয়ে এখনই শেষ করে দেওয়া
        col.update_one({"_id": self.message_id}, {"$set": {"end_timestamp": time.time()}})
        await interaction.response.send_message("✅ Ending giveaway immediately...", ephemeral=True)

    @discord.ui.button(label="🎲 Reroll", style=discord.ButtonStyle.secondary, row=1)
    async def reroll_btn(self, interaction: discord.Interaction, button: Button):
        # ডাটাবেস চেক করা
        col = Database.get_collection("giveaways")
        # শেষ হয়ে যাওয়া গিভঅ্যাওয়ে চেক করা (যেহেতু ডাটাবেস থেকে ডিলিট হচ্ছে না)
        # তবে আমার লজিক অনুযায়ী শেষ হলে ডিলিট হয়, তাই রিরোল এর জন্য ডাটা রাখা জরুরি।
        # *ফিক্স:* আমি এখানে শেষ হওয়ার পর ডাটা ডিলিট না করে `ended: True` করে রাখবো।
        
        data = col.find_one({"_id": self.message_id})
        if not data or not data.get("entrants"):
             return await interaction.response.send_message("❌ No entrants found in database!", ephemeral=True)
             
        winner = random.choice(data["entrants"])
        await interaction.channel.send(f"{GIFT_ANIM} **Reroll Winner:** <@{winner}>! Congratulations!")
        await interaction.response.send_message("✅ Reroll Complete!", ephemeral=True)


# ================= 5. PUBLIC GIVEAWAY VIEW (জয়েন বাটন) =================
class GiveawayView(View):
    def __init__(self, bot, message_id, prize, host_id, end_timestamp, winners_count, image_url):
        super().__init__(timeout=None)
        self.bot = bot
        self.message_id = message_id
        self.prize = prize
        self.host_id = host_id
        self.end_timestamp = end_timestamp
        self.winners_count = winners_count
        self.image_url = image_url

    @discord.ui.button(emoji=discord.PartialEmoji.from_str(GIFT_ANIM), label="Join Entry", style=discord.ButtonStyle.secondary, custom_id="join_gv_db")
    async def join_giveaway(self, interaction: discord.Interaction, button: Button):
        col = Database.get_collection("giveaways")
        data = col.find_one({"_id": self.message_id})
        
        if not data or data.get("ended", True):
            return await interaction.response.send_message("❌ This giveaway has ended!", ephemeral=True)

        user_id = interaction.user.id
        entrants = data.get("entrants", [])

        if user_id in entrants:
            # Leave
            col.update_one({"_id": self.message_id}, {"$pull": {"entrants": user_id}})
            new_count = len(entrants) - 1
            await interaction.response.send_message(f"❌ You left the giveaway for **{self.prize}**.", ephemeral=True)
        else:
            # Join
            col.update_one({"_id": self.message_id}, {"$addToSet": {"entrants": user_id}})
            new_count = len(entrants) + 1
            await interaction.response.send_message(f"✅ **Entry Confirmed!** You joined for **{self.prize}**.", ephemeral=True)
        
        # বাটন আপডেট
        button.label = f"Join ({new_count})"
        await interaction.message.edit(view=self)

# ================= 6. MAIN SYSTEM LOGIC =================
class GiveawaySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_giveaways.start() # ব্যাকগ্রাউন্ড টাস্ক

    def cog_unload(self):
        self.check_giveaways.cancel()

    # --- Background Loop (Data Checking) ---
    @tasks.loop(seconds=10)
    async def check_giveaways(self):
        col = Database.get_collection("giveaways")
        if col is None: return

        now = time.time()
        # যেগুলোর সময় শেষ এবং এখনো ended মার্ক করা হয়নি
        ended_gvs = col.find({"end_timestamp": {"$lte": now}, "ended": False})

        for gv in ended_gvs:
            await self.end_giveaway_logic(gv)

    async def end_giveaway_logic(self, data):
        col = Database.get_collection("giveaways")
        message_id = data["_id"]
        channel_id = data["channel_id"]
        
        try:
            channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
            message = await channel.fetch_message(message_id)
        except:
            # মেসেজ না পেলে ডাটাবেস থেকে রিমুভ (Clean up)
            col.delete_one({"_id": message_id})
            return

        entrants = data.get("entrants", [])
        winners_count = data["winners_count"]
        prize = data["prize"]
        host_id = data["host_id"]

        # উইনার লজিক
        if len(entrants) < winners_count:
            await message.reply(f"❌ **Giveaway Cancelled!** Not enough entries for **{prize}**.")
            
            # এম্বেড আপডেট (Cancelled)
            embed = message.embeds[0]
            embed.color = discord.Color.red()
            embed.description = f"### {prize}\n🚫 **Cancelled due to lack of entries.**"
            await message.edit(embed=embed, view=None)
            
            # ডাটাবেসে Ended মার্ক করা
            col.update_one({"_id": message_id}, {"$set": {"ended": True}})
            return

        # উইনার পিক করা
        winner_ids = random.sample(entrants, winners_count)
        winner_mentions = ", ".join([f"<@{uid}>" for uid in winner_ids])

        # উইনার এনাউন্সমেন্ট
        win_embed = discord.Embed(
            title=f"🎉 **CONGRATULATIONS!** 🎉",
            description=(
                f"{GIVEAWAY_ICON} **Prize:** {prize}\n"
                f"{GIFT_ANIM} **Winner(s):** {winner_mentions}\n"
                f"👥 **Total Entries:** {len(entrants)}"
            ),
            color=discord.Color.gold()
        )
        await message.reply(f"{winner_mentions}", embed=win_embed)

        # অরিজিনাল মেসেজ আপডেট
        orig_embed = message.embeds[0]
        orig_embed.color = discord.Color.red() # Red for Ended
        orig_embed.description = (
            f"### {prize}\n"
            f"{ARROW} **Host:** <@{host_id}>\n"
            f"{ARROW} **Winners:** {winner_mentions}\n"
            f"{ARROW} **Ended:** <t:{int(time.time())}:R>\n"
            f"{ARROW} **Status:** `🔴 Ended`"
        )
        # ভিউ সরিয়ে নেওয়া
        await message.edit(embed=orig_embed, view=None)

        # ডাটাবেসে আপডেট (যাতে পরে রিরোল করা যায়)
        col.update_one({"_id": message_id}, {"$set": {"ended": True}})

    # --- Start Command ---
    @app_commands.command(name="giveaway", description="🎁 Start a Database-Backed Premium Giveaway")
    @app_commands.describe(prize="Prize Name", duration="Duration (10s, 1m, 1h)", winners="Winner Count", image="GIF/Image URL")
    async def giveaway(self, interaction: discord.Interaction, prize: str, duration: str, winners: int = 1, image: str = None):
        
        if not image:
            image = "https://media1.tenor.com/m/K0a4qgA9wGMAAAAC/giveaway-gift.gif"

        seconds = convert_time(duration)
        if seconds < 10:
            return await interaction.response.send_message("❌ Minimum time is 10 seconds!", ephemeral=True)

        end_timestamp = time.time() + seconds

        # ১. এম্বেড তৈরি
        embed = discord.Embed(
            title=f"{GIVEAWAY_ICON} **PREMIUM GIVEAWAY EVENT**",
            description=(
                f"### {prize}\n"
                f"{ARROW} **Host:** {interaction.user.mention}\n"
                f"{ARROW} **Winners:** `{winners}`\n"
                f"{ARROW} **Ends:** <t:{int(end_timestamp)}:R>\n"
                f"{ARROW} **Status:** `🟢 Active`\n\n"
                f"👇 **React with {GIFT_ANIM} below to enter!**"
            ),
            color=0x2b2d31
        )
        embed.set_image(url=image)
        embed.set_footer(text="Total Entries: 0 • Nova System")

        # ২. মেসেজ পাঠানো
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()

        # ৩. ডাটাবেসে সেভ
        col = Database.get_collection("giveaways")
        if col is not None:
            gv_data = {
                "_id": message.id,
                "channel_id": interaction.channel_id,
                "host_id": interaction.user.id,
                "prize": prize,
                "winners_count": winners,
                "end_timestamp": end_timestamp,
                "image_url": image,
                "entrants": [],
                "ended": False
            }
            col.insert_one(gv_data)

            # ৪. ভিউ সেট করা
            view = GiveawayView(self.bot, message.id, prize, interaction.user.id, end_timestamp, winners, image)
            await message.edit(view=view)

            # ৫. হোস্ট ড্যাশবোর্ড
            dash = HostDashboard(message.id)
            await interaction.followup.send(
                f"⚙️ **Host Controls for: {prize}**\nUse this to Edit, End Fast or Reroll.",
                view=dash,
                ephemeral=True
            )
        else:
            await interaction.followup.send("❌ Database Error! Check connection.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(GiveawaySystem(bot))
                                                            
