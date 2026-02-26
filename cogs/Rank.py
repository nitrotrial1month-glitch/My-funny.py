import discord
from discord.ext import commands
from discord import app_commands
import math
from database import Database
from utils import get_theme_color

class LeaderboardView(discord.ui.View):
    """Interactive Ranking View for Cash, Coinflip, and Hunt"""
    def __init__(self, ctx, bot, cash_emoji):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.bot = bot
        self.cash_emoji = cash_emoji
        self.category = "cash"  # Default starting category
        self.page = 0
        self.per_page = 10

    async def fetch_leaderboard_data(self):
        """Fetches global data sorted by the selected category"""
        col = Database.get_collection("inventory")
        
        # Determine the field based on the selected button
        if self.category == "cash":
            field = "balance"
        elif self.category == "coinflip":
            field = "cf_wins" # Standard field for coinflip wins
        else:
            field = "hunts" # Standard field for hunt count
        
        # Sort users by highest value in the selected field
        cursor = col.find({field: {"$exists": True, "$gt": 0}}).sort(field, -1)
        return list(cursor), field

    def create_embed(self, data, field):
        """Generates the high-fidelity OwO-style ranking embed"""
        theme_color = get_theme_color(self.ctx.guild.id)
        embed = discord.Embed(color=theme_color)
        
        titles = {
            "cash": "Global Cash Rankings",
            "coinflip": "Global Coinflip Wins",
            "hunt": "Global Hunting Masters"
        }
        embed.set_author(name=f"🏆 {titles.get(self.category)}", icon_url=self.bot.user.display_avatar.url)

        # Pagination calculations
        total_users = len(data)
        max_pages = max(1, math.ceil(total_users / self.per_page))
        start = self.page * self.per_page
        end = start + self.per_page
        current_page_data = data[start:end]

        # 1. Your Personal Rank Section
        user_rank = "N/A"
        user_val = 0
        for index, entry in enumerate(data):
            if str(entry["_id"]) == str(self.ctx.author.id):
                user_rank = index + 1
                user_val = entry.get(field, 0)
                break
        
        icons = {"cash": self.cash_emoji, "coinflip": "🪙", "hunt": "🏹"}
        current_icon = icons.get(self.category)

        embed.add_field(
            name="📊 Your Current Stats",
            value=f"**User:** {self.ctx.author.name}\n**Rank:** #{user_rank}\n**Total:** {current_icon} `{user_val:,}`",
            inline=False
        )

        # 2. Global Leaderboard Section
        rank_list = ""
        for i, entry in enumerate(current_page_data, start=start + 1):
            uid = int(entry["_id"])
            user = self.bot.get_user(uid)
            name = user.name if user else f"User({uid})"
            val = entry.get(field, 0)
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
            rank_list += f"{medal} **{name}**\n {current_icon} `{val:,}`\n"

        embed.description = f"**Global Top {total_users:,} Players**\n{rank_list or '*No data available.*'}"

        # 3. Footer Pagination Info
        embed.set_footer(text=f"Page {self.page + 1}/{max_pages} • Total Players: {total_users:,} • Global Economy")
        return embed

    @discord.ui.button(label="Cash", style=discord.ButtonStyle.success, emoji="💰")
    async def show_cash(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return
        self.category, self.page = "cash", 0
        data, field = await self.fetch_leaderboard_data()
        await interaction.response.edit_message(embed=self.create_embed(data, field), view=self)

    @discord.ui.button(label="Coinflip", style=discord.ButtonStyle.primary, emoji="🪙")
    async def show_cf(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return
        self.category, self.page = "coinflip", 0
        data, field = await self.fetch_leaderboard_data()
        await interaction.response.edit_message(embed=self.create_embed(data, field), view=self)

    @discord.ui.button(label="Hunt", style=discord.ButtonStyle.primary, emoji="🏹")
    async def show_hunt(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return
        self.category, self.page = "hunt", 0
        data, field = await self.fetch_leaderboard_data()
        await interaction.response.edit_message(embed=self.create_embed(data, field), view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id or self.page == 0: return
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
        self.cash_emoji = "<:Nova:1453460518764548186>" #

    @commands.hybrid_command(name="leaderboard", aliases=["top", "rank"], description="View global rankings")
    async def leaderboard(self, ctx: commands.Context):
        """Displays the stylish global ranking system with automated category switching"""
        view = LeaderboardView(ctx, self.bot, self.cash_emoji)
        data, field = await view.fetch_leaderboard_data()
        embed = view.create_embed(data, field)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
            
