import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import collections
from utils import get_theme_color

# ================= 1. PROGRESS BAR GENERATOR =================
def create_bar(count, total, length=10):
    """ভোটের সংখ্যার ওপর ভিত্তি করে সুন্দর বার তৈরি করে"""
    if total == 0:
        return "⬛" * length # সব কালো
    
    percent = count / total
    filled = int(percent * length)
    empty = length - filled
    
    # স্টাইলিশ বার (Blue & Black)
    return "🟦" * filled + "⬛" * empty

# ================= 2. POLL BUTTON (ভোট দেওয়ার বাটন) =================
class PollButton(Button):
    def __init__(self, label, index, view_parent):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=label[:80], # বেশি বড় লেখা ছোট করে দিবে
            custom_id=f"poll_{index}",
            row=index // 5 # ৫টা করে বাটন প্রতি লাইনে
        )
        self.index = index
        self.view_parent = view_parent

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        # ১. ভোট লজিক (Vote Logic)
        previous_vote = self.view_parent.votes.get(user_id)

        if previous_vote == self.index:
            # যদি একই বাটনে আবার ক্লিক করে, ভোট রিমুভ হবে
            del self.view_parent.votes[user_id]
            await interaction.response.send_message("🗑️ You removed your vote.", ephemeral=True)
        else:
            # নতুন ভোট বা ভোট চেঞ্জ
            self.view_parent.votes[user_id] = self.index
            await interaction.response.send_message(f"✅ You voted for **{self.label}**!", ephemeral=True)

        # ২. লাইভ আপডেট (Live Update)
        await self.view_parent.update_poll_message()

# ================= 3. POLL VIEW (কন্ট্রোল প্যানেল) =================
class PollView(View):
    def __init__(self, question, options, host):
        super().__init__(timeout=None) # পোল কখনো এক্সপায়ার হবে না
        self.question = question
        self.options = options
        self.host = host
        self.votes = {} # {user_id: option_index}
        self.message = None

        # ডাইনামিক বাটন তৈরি
        for i, option in enumerate(options):
            self.add_item(PollButton(option, i, self))

    @discord.ui.button(label="🛑 End Poll", style=discord.ButtonStyle.danger, row=4)
    async def end_poll(self, interaction: discord.Interaction, button: Button):
        # শুধু হোস্ট পোল শেষ করতে পারবে
        if interaction.user.id != self.host.id:
            await interaction.response.send_message("❌ Only the host can end this poll!", ephemeral=True)
            return
        
        # পোল শেষ হলে সব বাটন ডিজেবল হবে
        for child in self.children:
            child.disabled = True
        
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"🛑 **Poll Ended by** {interaction.user.mention}!")
        self.stop()

    async def update_poll_message(self):
        # ভোট গণনা করা
        counts = collections.Counter(self.votes.values())
        total_votes = sum(counts.values())

        # ডেসক্রিপশন তৈরি করা
        description = ""
        for i, option in enumerate(self.options):
            count = counts[i]
            percent = (count / total_votes * 100) if total_votes > 0 else 0
            bar = create_bar(count, total_votes)
            
            # লিডারবোর্ড আইকন (সবচেয়ে বেশি ভোট পেলে মুকুট 👑)
            icon = "👑" if total_votes > 0 and count == max(counts.values()) else "🔹"
            
            description += (
                f"{icon} **{option}**\n"
                f"{bar} `{int(percent)}%` ({count} votes)\n\n"
            )

        # এম্বেড ডিজাইন
        embed = discord.Embed(
            title=f"📊 **{self.question}**",
            description=description,
            color=get_theme_color(self.host.guild.id)
        )
        embed.set_footer(text=f"Total Votes: {total_votes} • Host: {self.host.name}")
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2618/2618529.png")

        if self.message:
            await self.message.edit(embed=embed, view=self)

# ================= 4. MAIN COMMAND =================
class PollSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="poll", description="📊 Start a Stylish Live Poll")
    @app_commands.describe(question="What is the poll about?", options="Separate options with commas (e.g., Red, Blue, Green)")
    async def poll(self, interaction: discord.Interaction, question: str, options: str):
        # ১. অপশন আলাদা করা
        option_list = [opt.strip() for opt in options.split(",") if opt.strip()]
        
        # ২. ভ্যালিডেশন
        if len(option_list) < 2:
            await interaction.response.send_message("❌ You need at least **2 options**! (Example: `Red, Blue`)", ephemeral=True)
            return
        if len(option_list) > 10:
            await interaction.response.send_message("❌ Maximum **10 options** allowed!", ephemeral=True)
            return

        # ৩. ইনিশিয়াল রেসপন্স
        await interaction.response.defer()

        # ৪. ভিউ তৈরি
        poll_view = PollView(question, option_list, interaction.user)
        
        # ৫. প্রথম মেসেজ পাঠানো
        # আমরা প্রথমে একটি ডামি আপডেট কল করে এম্বেড জেনারেট করবো
        counts = collections.Counter()
        total_votes = 0
        description = ""
        for i, option in enumerate(option_list):
            bar = "⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛"
            description += f"🔹 **{option}**\n{bar} `0%` (0 votes)\n\n"

        embed = discord.Embed(
            title=f"📊 **{question}**",
            description=description,
            color=get_theme_color(interaction.guild.id)
        )
        embed.set_footer(text=f"Total Votes: 0 • Host: {interaction.user.name}")
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2618/2618529.png")

        message = await interaction.followup.send(embed=embed, view=poll_view)
        poll_view.message = message # মেসেজ অবজেক্ট ভিউতে সেভ রাখা (পরে এডিটের জন্য)

async def setup(bot):
    await bot.add_cog(PollSystem(bot))
      
