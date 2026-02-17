import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import collections
from utils import get_theme_color
from database import Database # 👇 ডাটাবেস ইমপোর্ট

# ================= 1. PROGRESS BAR GENERATOR =================
def create_bar(count, total, length=10):
    """ভোটের সংখ্যার ওপর ভিত্তি করে সুন্দর বার তৈরি করে"""
    if total == 0:
        return "⬛" * length
    
    percent = count / total
    filled = int(percent * length)
    empty = length - filled
    
    return "🟦" * filled + "⬛" * empty

# ================= 2. POLL BUTTON (ভোট বাটন) =================
class PollButton(Button):
    def __init__(self, label, index):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=label[:80],
            custom_id=f"poll_btn_{index}", # ইউনিক ID
            row=index // 5
        )
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        # ডাটাবেস কল করা
        col = Database.get_collection("polls")
        poll_data = col.find_one({"_id": interaction.message.id})

        if not poll_data or not poll_data.get("active"):
            return await interaction.response.send_message("❌ This poll has ended!", ephemeral=True)

        user_id = str(interaction.user.id)
        votes = poll_data.get("votes", {})
        
        # লজিক: আগে ভোট দিয়েছে কিনা
        previous_vote = votes.get(user_id)
        
        msg = ""
        if previous_vote == self.index:
            # আন-ভোট (Unvote)
            del votes[user_id]
            msg = "🗑️ You removed your vote."
        else:
            # নতুন ভোট (New Vote)
            votes[user_id] = self.index
            msg = f"✅ You voted for **{self.label}**!"

        # ডাটাবেস আপডেট
        col.update_one({"_id": interaction.message.id}, {"$set": {"votes": votes}})
        
        # ইউজারকে কনফার্মেশন
        await interaction.response.send_message(msg, ephemeral=True)
        
        # লাইভ এম্বেড আপডেট (Parent View কল করা)
        await self.view.update_poll_display(interaction.message, poll_data["options"], votes, poll_data["question"], poll_data["host_name"])

# ================= 3. POLL VIEW (কন্ট্রোল প্যানেল) =================
class PollView(View):
    def __init__(self, options):
        super().__init__(timeout=None) # বাটন আজীবন কাজ করবে
        
        # ডাইনামিক বাটন তৈরি
        for i, option in enumerate(options):
            self.add_item(PollButton(option, i))

    # --- এন্ড পোল বাটন ---
    @discord.ui.button(label="End Poll", style=discord.ButtonStyle.danger, custom_id="poll_end_btn", row=4)
    async def end_poll(self, interaction: discord.Interaction, button: Button):
        col = Database.get_collection("polls")
        poll_data = col.find_one({"_id": interaction.message.id})

        # চেক করা যিনি ক্লিক করেছেন তিনি হোস্ট কিনা
        if str(interaction.user.id) != str(poll_data.get("host_id")):
            return await interaction.response.send_message("❌ Only the host can end this poll!", ephemeral=True)
        
        # ডাটাবেসে স্ট্যাটাস আপডেট
        col.update_one({"_id": interaction.message.id}, {"$set": {"active": False}})

        # বাটন ডিজেবল করা
        for child in self.children:
            child.disabled = True
        
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"🛑 **Poll Ended by** {interaction.user.mention}!")
        self.stop()

    # --- এম্বেড আপডেটার ফাংশন ---
    async def update_poll_display(self, message, options, votes, question, host_name):
        # ভোট গণনা
        counts = collections.Counter(votes.values())
        total_votes = sum(counts.values())

        description = ""
        for i, option in enumerate(options):
            count = counts[i]
            percent = (count / total_votes * 100) if total_votes > 0 else 0
            bar = create_bar(count, total_votes)
            
            icon = "👑" if total_votes > 0 and count == max(counts.values()) else "🔹"
            
            description += (
                f"{icon} **{option}**\n"
                f"{bar} `{int(percent)}%` ({count} votes)\n\n"
            )

        embed = discord.Embed(
            title=f"📊 **{question}**",
            description=description,
            color=get_theme_color(message.guild.id)
        )
        embed.set_footer(text=f"Total Votes: {total_votes} • Host: {host_name}")
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2618/2618529.png")

        await message.edit(embed=embed, view=self)

# ================= 4. MAIN COMMAND & LISTENER =================
class PollSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Bot Restart হলে বাটন যাতে কাজ করে ---
    @commands.Cog.listener()
    async def on_ready(self):
        col = Database.get_collection("polls")
        if col is None: return

        # শুধু একটিভ পোলগুলো লোড করবে
        active_polls = col.find({"active": True})
        
        count = 0
        for poll in active_polls:
            view = PollView(poll["options"])
            self.bot.add_view(view, message_id=poll["_id"])
            count += 1
        
        print(f"✅ Restored {count} active polls.")

    @app_commands.command(name="poll", description="📊 Start a Database-Backed Live Poll")
    @app_commands.describe(question="What is the poll about?", options="Separate options with commas (e.g., Red, Blue, Green)")
    async def poll(self, interaction: discord.Interaction, question: str, options: str):
        # ১. অপশন প্রসেসিং
        option_list = [opt.strip() for opt in options.split(",") if opt.strip()]
        
        if len(option_list) < 2:
            return await interaction.response.send_message("❌ Need at least 2 options!", ephemeral=True)
        if len(option_list) > 10:
            return await interaction.response.send_message("❌ Max 10 options allowed!", ephemeral=True)

        # ২. ইনিশিয়াল এম্বেড
        description = ""
        for opt in option_list:
            description += f"🔹 **{opt}**\n⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛ `0%` (0 votes)\n\n"

        embed = discord.Embed(
            title=f"📊 **{question}**",
            description=description,
            color=get_theme_color(interaction.guild.id)
        )
        embed.set_footer(text=f"Total Votes: 0 • Host: {interaction.user.name}")
        
        # ৩. ভিউ তৈরি এবং মেসেজ পাঠানো
        view = PollView(option_list)
        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()

        # ৪. ডাটাবেসে সেভ
        col = Database.get_collection("polls")
        poll_doc = {
            "_id": message.id, # Message ID as Key
            "channel_id": interaction.channel_id,
            "guild_id": interaction.guild_id,
            "host_id": str(interaction.user.id),
            "host_name": interaction.user.name,
            "question": question,
            "options": option_list,
            "votes": {}, # {user_id: option_index}
            "active": True
        }
        col.insert_one(poll_doc)

async def setup(bot):
    await bot.add_cog(PollSystem(bot))
    
