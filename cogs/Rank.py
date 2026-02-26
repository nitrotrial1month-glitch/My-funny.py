import discord
from discord.ext import commands
from discord import app_commands
import math
from database import Database
from utils import get_theme_color

class LeaderboardView(discord.ui.View):
    """Advanced View for Category Switching and Pagination"""
    def __init__(self, ctx, bot, cash_emoji):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.bot = bot
        self.cash_emoji = cash_emoji
        self.category = "cash"  # Default category
        self.page = 0
        self.per_page = 10

    async def fetch_leaderboard_data(self):
        """Fetches and sorts global user data from MongoDB"""
        col = Database.get_collection("inventory")
        field = "balance" if self.category == "cash" else "invites"
        
        # Fetch all users who have the relevant field, sorted descending
        cursor = col.find({field: {"$exists": True, "$gt": 0}}).sort(field, -1)
        return list(cursor), field

    def create_embed(self, data, field):
        """Creates the stylish OwO-themed rankings embed"""
        theme_color = get_theme_color(self.ctx.guild.id)
        embed = discord.Embed(color=theme_color)
        
        category_title = "Global Cash Leaderboard" if self.category == "cash" else "Global Invite Leaderboard"
        embed.set_author(name=f"📊 {category_title}", icon_url=self.bot.user.display_avatar.url)

        # Pagination logic
        total_players = len(data)
        max_pages = max(1, math.ceil(total_players / self.per_page))
        start = self.page * self.per_page
        end = start + self.per_page
        current_page_data = data[start:end]

        # 1. Top Section: Command User's Stats
        user_rank = "N/A"
        user_value = 0
        for index, entry in enumerate(data):
            if str(entry["_id"]) == str(self.ctx.author.id):
                user_rank = index + 1
                user_value = entry.get(field, 0)
                break
        
        stat_icon = self.cash_emoji if self.category == "cash" else "📩"
        embed.add_field(
            name="📊 Your Current Stats",
            value=f"**User:** {self.ctx.author.name}\n**Rank:** #{user_rank}\n**{self.category.title()}:** {stat_icon} `{user_value:,}`",
            inline=False
        )

        # 2. Middle Section: Rankings List
        rank_list = ""
        for i, entry in enumerate(current_page_data, start=start + 1):
            uid = int(entry["_id"])
            # Fetch user from cache or API
            member = self.bot.get_user(uid)
            name = member.name if member else f"User({uid})"
            val = entry.get(field, 0)
            
            # Medal Styling
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
            rank_list += f"{medal} **{name}**\n {stat_icon} `{val:,}`\n"

        if not rank_list:
            rank_list = "*No users found in this category.*"
        
        embed.description = f"**🏆 Rankings**\n{rank_list}"

        # 3. Footer Section
        embed.set_footer(text=f"Page {self.page + 1}/{max_pages} • Total Players: {total_players:,} • Global Economy")
        return embed

    @discord.ui.button(label="Cash", style=discord.ButtonStyle.success, emoji="💰")
    async def show_cash(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return
        self.category = "cash"
        self.page = 0
        data, field = await self.fetch_leaderboard_data()
        await interaction.response.edit_message(embed=self.create_embed(data, field), view=self)

    @discord.ui.button(label="Invites", style=discord.ButtonStyle.primary, emoji="📩")
    async def show_invites(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return
        self.category = "invites"
        self.page = 0
        data, field = await self.fetch_leaderboard_data()
        await interaction.response.edit_message(embed=self.create_embed(data, field), view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return
        if self.page > 0:
            self.page -= 1
            data, field = await self.fetch_leaderboard_data()
            await interaction.response.edit_message(embed=self.create_embed(data, field), view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return
        data, field = await self.fetch_leaderboard_data()
        if (self.page + 1) * self.per_page < len(data):
            self.page += 1
            await interaction.response.edit_message(embed=self.create_embed(data, field), view=self)

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cash_emoji = "<:Nova:1453460518764548186>"

    @commands.hybrid_command(name="leaderboard", aliases=["lb", "top", "rank"], description="View global rankings for Cash or Invites")
    async def leaderboard(self, ctx: commands.Context):
        """Displays a stylish global leaderboard with toggle buttons"""
        view = LeaderboardView(ctx, self.bot, self.cash_emoji)
        data, field = await view.fetch_leaderboard_data()
        embed = view.create_embed(data, field)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
      
