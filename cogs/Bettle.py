import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import random
import asyncio
from database import Database
from utils import get_theme_color

# ================= 🖼️ BATTLE ASSETS =================
ANIMAL_IMAGES = {
    "Dragon": "https://i.imgur.com/example_dragon.png",
    "Wolf": "https://i.imgur.com/example_wolf.png",
    "default": "https://media.discordapp.net/attachments/1000000000000000000/1111111111111111111/battle_scene.png"
}

# ================= 📊 STATS LOGIC =================
BASE_STATS = {
    "Common": {"hp": 100, "atk": 15},
    "Uncommon": {"hp": 150, "atk": 25},
    "Rare": {"hp": 250, "atk": 40},
    "Epic": {"hp": 400, "atk": 60},
    "Mythic": {"hp": 700, "atk": 90},
    "Legendary": {"hp": 1000, "atk": 150}
}

ANIMAL_RARITY_MAP = {
    "Worm": "Common", "Ant": "Common", "Wolf": "Rare", 
    "Dragon": "Mythic", "Demon": "Legendary"
}

def get_stats(name, lvl):
    clean_name = name.split(" ")[-1] if " " in name else name
    rarity = ANIMAL_RARITY_MAP.get(clean_name, "Common")
    base = BASE_STATS.get(rarity, BASE_STATS["Common"])
    
    multiplier = 1 + (lvl * 0.1)
    return {
        "hp": int(base["hp"] * multiplier),
        "atk": int(base["atk"] * multiplier),
        "name_clean": clean_name
    }

# ================= ⚔️ PVP BATTLE VIEW =================
class PVPBattleView(View):
    def __init__(self, ctx, p1, p2):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.p1 = p1 # Player 1 Data
        self.p2 = p2 # Player 2 Data
        self.turn = p1['id'] # প্রথম টার্ন প্লেয়ার ১ এর
        self.log = f"⚔️ **Match Started!**\n> <@{p1['id']}>'s Turn!"

    def get_hp_bar(self, current, max_hp):
        percent = current / max_hp
        filled = int(percent * 10)
        return "🟩" * filled + "⬛" * (10 - filled)

    async def update_board(self, interaction, ended=False, winner=None):
        # কার টার্ন সেটা ঠিক করা
        current_player_id = self.turn
        
        embed = discord.Embed(
            title="⚔️ PVP ARENA",
            description=f"**Battle Log:**\n{self.log}",
            color=discord.Color.red()
        )
        
        # ইমেজ (যার টার্ন তার এনিমেল দেখাবে)
        current_p_data = self.p1 if current_player_id == self.p1['id'] else self.p2
        img_url = ANIMAL_IMAGES.get(current_p_data['name_clean'], ANIMAL_IMAGES["default"])
        embed.set_image(url=img_url)

        # Player 1 Stats
        embed.add_field(
            name=f"🛡️ {self.p1['name']} (P1)",
            value=f"{self.get_hp_bar(self.p1['hp'], self.p1['max_hp'])}\n❤️ {self.p1['hp']}/{self.p1['max_hp']}",
            inline=True
        )

        # Player 2 Stats
        embed.add_field(
            name=f"🛡️ {self.p2['name']} (P2)",
            value=f"{self.get_hp_bar(self.p2['hp'], self.p2['max_hp'])}\n❤️ {self.p2['hp']}/{self.p2['max_hp']}",
            inline=True
        )

        if ended:
            self.clear_items()
            embed.set_footer(text=f"🏆 Winner: {winner}")
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            embed.set_footer(text=f"Waiting for <@{self.turn}>...")
            await interaction.response.edit_message(embed=embed, view=self)

    # --- ACTION BUTTONS ---
    @discord.ui.button(label="Attack", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def attack(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.turn:
            return await interaction.response.send_message("❌ Not your turn!", ephemeral=True)
        
        # কে কাকে মারছে?
        if self.turn == self.p1['id']:
            attacker, defender = self.p1, self.p2
            next_turn = self.p2['id']
        else:
            attacker, defender = self.p2, self.p1
            next_turn = self.p1['id']

        # ড্যামেজ লজিক
        dmg = random.randint(attacker['atk'] - 5, attacker['atk'] + 5)
        defender['hp'] -= dmg
        self.log = f"💥 **{attacker['user_name']}** hit for **{dmg}** DMG!\n> <@{next_turn}>'s Turn!"

        # উইন চেক
        if defender['hp'] <= 0:
            defender['hp'] = 0
            # ডাটাবেস আপডেট (উইনারকে টাকা দেওয়া)
            Database.update_balance(str(attacker['id']), 200)
            self.log = f"🏆 **{attacker['user_name']}** WINS!\n💰 Earned 200 Coins!"
            return await self.update_board(interaction, ended=True, winner=attacker['user_name'])

        self.turn = next_turn
        await self.update_board(interaction)

    @discord.ui.button(label="Heal", style=discord.ButtonStyle.success, emoji="💊")
    async def heal(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.turn:
            return await interaction.response.send_message("❌ Not your turn!", ephemeral=True)

        if self.turn == self.p1['id']:
            player, next_turn = self.p1, self.p2['id']
        else:
            player, next_turn = self.p2, self.p1['id']

        heal = int(player['max_hp'] * 0.25)
        player['hp'] = min(player['max_hp'], player['hp'] + heal)
        
        self.log = f"💊 **{player['user_name']}** healed **{heal}** HP!\n> <@{next_turn}>'s Turn!"
        self.turn = next_turn
        await self.update_board(interaction)


# ================= 🤝 CHALLENGE VIEW (Confirmation) =================
class ChallengeView(View):
    def __init__(self, ctx, challenger, opponent):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.challenger = challenger
        self.opponent = opponent
        self.accepted = False

    @discord.ui.button(label="Accept Duel", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.opponent:
            return await interaction.response.send_message("❌ Only the opponent can accept!", ephemeral=True)
        
        self.accepted = True
        self.stop() # ভিউ থামিয়ে মেইন ব্যাটেল শুরু হবে
        await interaction.response.send_message("✅ Challenge Accepted! Preparing arena...", ephemeral=True)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.opponent: return
        await interaction.message.delete()
        self.stop()


# ================= 🚀 MAIN CLASS =================
class BattleSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- TEAM ADD (Existing) ---
    @commands.hybrid_command(name="team_add")
    async def team_add(self, ctx, animal_name: str):
        # (আগের কোড সেইম থাকবে)
        pass

    # --- PVP BATTLE COMMAND ---
    @commands.hybrid_command(name="pvp", description="⚔️ Duel another player!")
    async def pvp(self, ctx, opponent: discord.Member):
        if opponent.bot or opponent == ctx.author:
            return await ctx.send("❌ You cannot battle bots or yourself!")

        col = Database.get_collection("inventory")
        
        # ১. প্লেয়ার ১ ডাটা
        p1_data = col.find_one({"_id": str(ctx.author.id)})
        if not p1_data or "team_name" not in p1_data:
            return await ctx.send("❌ You don't have a team! Use `/team_add`.")

        # ২. প্লেয়ার ২ ডাটা
        p2_data = col.find_one({"_id": str(opponent.id)})
        if not p2_data or "team_name" not in p2_data:
            return await ctx.send(f"❌ **{opponent.name}** doesn't have a team yet!")

        # ৩. স্ট্যাটাস লোড করা
        def load_stats(user, data):
            stats = get_stats(data["team_name"], data.get("team_lvl", 1))
            stats["id"] = user.id
            stats["user_name"] = user.name
            stats["name"] = f"{data['team_name']} (Lvl {data.get('team_lvl', 1)})"
            stats["max_hp"] = stats["hp"]
            return stats

        p1_stats = load_stats(ctx.author, p1_data)
        p2_stats = load_stats(opponent, p2_data)

        # ৪. চ্যালেঞ্জ পাঠানো
        view = ChallengeView(ctx, ctx.author, opponent)
        msg = await ctx.send(f"⚔️ {opponent.mention}, **{ctx.author.name}** challenged you to a duel!", view=view)
        
        await view.wait() # বাটন ক্লিকের অপেক্ষা

        if view.accepted:
            # ৫. ব্যাটেল শুরু
            battle_view = PVPBattleView(ctx, p1_stats, p2_stats)
            
            # ইনিশিয়াল এম্বেড
            embed = discord.Embed(title="⚔️ PVP MATCH STARTING...", color=discord.Color.red())
            await msg.edit(content=None, embed=embed, view=battle_view)
            
            # বোর্ড আপডেট
            await battle_view.update_board(msg.interaction if ctx.interaction else ctx)

async def setup(bot):
    await bot.add_cog(BattleSystem(bot))
                                                           
