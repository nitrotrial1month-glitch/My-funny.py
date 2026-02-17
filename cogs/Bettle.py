import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import random
import asyncio
from database import Database
from utils import get_theme_color

# ================= 🖼️ ASSETS & CONFIG =================
ANIMAL_IMAGES = {
    "Dragon": "https://i.imgur.com/example_dragon.png",
    "Wolf": "https://i.imgur.com/example_wolf.png",
    "default": "https://media.discordapp.net/attachments/1000000000000000000/1111111111111111111/battle_scene.png"
}

BASE_STATS = {
    "Common": {"hp": 100, "atk": 15},
    "Uncommon": {"hp": 150, "atk": 25},
    "Rare": {"hp": 250, "atk": 40},
    "Epic": {"hp": 400, "atk": 60},
    "Mythic": {"hp": 700, "atk": 90},
    "Legendary": {"hp": 1000, "atk": 150}
}

# এনিমেল র‍্যাংক ম্যাপ
ANIMAL_RARITY_MAP = {
    "Worm": "Common", "Ant": "Common", "Wolf": "Rare", "Fox": "Rare",
    "Lion": "Epic", "Dragon": "Mythic", "Demon": "Legendary"
}

def calculate_stats(name, lvl):
    """লেভেল অনুযায়ী স্ট্যাটাস ক্যালকুলেট করা"""
    clean_name = name.split(" ")[-1] if " " in name else name
    rarity = ANIMAL_RARITY_MAP.get(clean_name, "Common")
    base = BASE_STATS.get(rarity, BASE_STATS["Common"])
    
    multiplier = 1 + (lvl * 0.1) # প্রতি লেভেলে ১০% বাড়ে
    return {
        "hp": int(base["hp"] * multiplier),
        "atk": int(base["atk"] * multiplier),
        "max_hp": int(base["hp"] * multiplier),
        "name": f"{clean_name} (Lvl {lvl})",
        "name_clean": clean_name
    }

def get_hp_bar(current, max_hp):
    if max_hp == 0: return "⬛" * 10
    percent = max(0, current / max_hp)
    filled = int(percent * 10)
    return "🟩" * filled + "⬛" * (10 - filled)

# ================= 🤖 PVE BATTLE VIEW (User vs Bot) =================
class PVEBattleView(View):
    def __init__(self, ctx, player, enemy):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.player = player
        self.enemy = enemy
        self.turn = ctx.author
        self.log = "⚔️ **Wild Encounter!** Choose your move."

    async def update_board(self, interaction, ended=False):
        embed = discord.Embed(
            title="⚔️ PVE BATTLE",
            description=f"**Battle Log:**\n> {self.log}",
            color=discord.Color.orange()
        )
        img_url = ANIMAL_IMAGES.get(self.player['name_clean'], ANIMAL_IMAGES["default"])
        embed.set_image(url=img_url)

        embed.add_field(
            name=f"🛡️ YOU: {self.player['name']}",
            value=f"{get_hp_bar(self.player['hp'], self.player['max_hp'])}\n❤️ {self.player['hp']}/{self.player['max_hp']}",
            inline=True
        )
        embed.add_field(
            name=f"💀 ENEMY: {self.enemy['name']}",
            value=f"{get_hp_bar(self.enemy['hp'], self.enemy['max_hp'])}\n❤️ {self.enemy['hp']}/{self.enemy['max_hp']}",
            inline=True
        )

        if ended:
            self.clear_items()
            embed.set_footer(text="Battle Ended")
        else:
            embed.set_footer(text="Your Turn 👇")
        
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Attack", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def attack(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.turn: return
        
        dmg = random.randint(self.player['atk'] - 5, self.player['atk'] + 5)
        self.enemy['hp'] -= dmg
        self.log = f"💥 You dealt **{dmg}** DMG!"
        
        if self.enemy['hp'] <= 0:
            self.enemy['hp'] = 0
            return await self.end_game(interaction, win=True)
            
        await self.update_board(interaction)
        await self.enemy_turn(interaction)

    @discord.ui.button(label="Heal", style=discord.ButtonStyle.success, emoji="💊")
    async def heal(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.turn: return
        
        heal = int(self.player['max_hp'] * 0.3)
        self.player['hp'] = min(self.player['max_hp'], self.player['hp'] + heal)
        self.log = f"💊 Recovered **{heal}** HP!"
        
        await self.update_board(interaction)
        await self.enemy_turn(interaction)

    async def enemy_turn(self, interaction):
        await asyncio.sleep(1)
        dmg = random.randint(self.enemy['atk'] - 5, self.enemy['atk'] + 5)
        self.player['hp'] -= dmg
        self.log = f"💢 Enemy hit you for **{dmg}** DMG!"
        
        if self.player['hp'] <= 0:
            self.player['hp'] = 0
            return await self.end_game(interaction, win=False)
            
        try:
            # Re-update embed
            embed = interaction.message.embeds[0]
            embed.description = f"**Battle Log:**\n> {self.log}"
            embed.set_field_at(0, name=f"🛡️ YOU: {self.player['name']}", value=f"{get_hp_bar(self.player['hp'], self.player['max_hp'])}\n❤️ {self.player['hp']}/{self.player['max_hp']}", inline=True)
            embed.set_field_at(1, name=f"💀 ENEMY: {self.enemy['name']}", value=f"{get_hp_bar(self.enemy['hp'], self.enemy['max_hp'])}\n❤️ {self.enemy['hp']}/{self.enemy['max_hp']}", inline=True)
            await interaction.message.edit(embed=embed)
        except: pass

    async def end_game(self, interaction, win):
        if win:
            xp = random.randint(30, 60)
            Database.update_balance(str(self.ctx.author.id), 50)
            # এখানে লেভেল আপ লজিক বসাতে পারেন
            self.log += f"\n🏆 **VICTORY!** Earned 50 Coins & {xp} XP."
        else:
            self.log += "\n☠️ **DEFEAT!**"
        await self.update_board(interaction, ended=True)


# ================= ⚔️ PVP BATTLE VIEW (User vs User) =================
class PVPBattleView(View):
    def __init__(self, ctx, p1, p2):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.p1 = p1
        self.p2 = p2
        self.turn = p1['id'] # P1 starts
        self.log = f"⚔️ **Duel Started!**\n> <@{p1['id']}>'s Turn!"

    async def update_board(self, interaction, ended=False, winner=None):
        embed = discord.Embed(
            title="⚔️ PVP ARENA",
            description=f"**Battle Log:**\n{self.log}",
            color=discord.Color.red()
        )
        
        # যার টার্ন তার ইমেজ
        current_p = self.p1 if self.turn == self.p1['id'] else self.p2
        img_url = ANIMAL_IMAGES.get(current_p['name_clean'], ANIMAL_IMAGES["default"])
        embed.set_image(url=img_url)

        embed.add_field(name=f"🛡️ {self.p1['user_name']}", value=f"{get_hp_bar(self.p1['hp'], self.p1['max_hp'])}\n❤️ {self.p1['hp']}/{self.p1['max_hp']}", inline=True)
        embed.add_field(name=f"🛡️ {self.p2['user_name']}", value=f"{get_hp_bar(self.p2['hp'], self.p2['max_hp'])}\n❤️ {self.p2['hp']}/{self.p2['max_hp']}", inline=True)

        if ended:
            self.clear_items()
            embed.set_footer(text=f"🏆 Winner: {winner}")
        else:
            embed.set_footer(text=f"Waiting for current turn...")
        
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Attack", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def attack(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.turn:
            return await interaction.response.send_message("❌ Not your turn!", ephemeral=True)
        
        if self.turn == self.p1['id']:
            attacker, defender, next_turn = self.p1, self.p2, self.p2['id']
        else:
            attacker, defender, next_turn = self.p2, self.p1, self.p1['id']

        dmg = random.randint(attacker['atk'] - 5, attacker['atk'] + 5)
        defender['hp'] -= dmg
        self.log = f"💥 **{attacker['user_name']}** hit for **{dmg}**!"

        if defender['hp'] <= 0:
            defender['hp'] = 0
            Database.update_balance(str(attacker['id']), 200)
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
        self.log = f"💊 **{player['user_name']}** healed **{heal}** HP!"
        
        self.turn = next_turn
        await self.update_board(interaction)

# ================= 🤝 CHALLENGE VIEW =================
class ChallengeView(View):
    def __init__(self, ctx, opponent):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.opponent = opponent
        self.accepted = False

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.opponent: return
        self.accepted = True
        self.stop()
        await interaction.response.send_message("✅ Challenge Accepted!", ephemeral=True)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.opponent: return
        self.stop()
        await interaction.message.delete()

# ================= 🚀 MAIN COG =================
class BattleSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- 1. TEAM COMMAND GROUP (t add / team add) ---
    @commands.hybrid_group(name="team", aliases=["t"], description="Manage your battle team")
    async def team(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Use `/team add [animal]` to set your fighter.")

    @team.command(name="add", description="Set your main fighter")
    async def add(self, ctx, animal_name: str):
        uid = str(ctx.author.id)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid})
        
        # নাম খোঁজা
        found_name = None
        if user_data and "zoo" in user_data:
            for anim in user_data["zoo"]:
                if animal_name.lower() in anim.lower():
                    found_name = anim
                    break
        
        if not found_name:
            return await ctx.send("❌ You don't own this animal!")

        col.update_one(
            {"_id": uid},
            {
                "$set": {"team_name": found_name, "team_lvl": 1, "team_xp": 0}
            },
            upsert=True
        )
        await ctx.send(f"✅ **{found_name}** selected as your fighter!")

    # --- 2. UNIFIED BATTLE COMMAND (b / battle) ---
    @commands.hybrid_command(name="battle", aliases=["b", "fight"], description="⚔️ Start a battle (PVE or PVP)")
    @app_commands.describe(opponent="Mention a user to PVP, or leave empty for PVE")
    async def battle(self, ctx, opponent: discord.Member = None):
        uid = str(ctx.author.id)
        col = Database.get_collection("inventory")
        p1_data = col.find_one({"_id": uid})

        # ১. প্লেয়ারের টিম চেক
        if not p1_data or "team_name" not in p1_data:
            return await ctx.send("❌ You need a team! Use `!t add [animal]` first.")

        p1_stats = calculate_stats(p1_data["team_name"], p1_data.get("team_lvl", 1))
        p1_stats["id"] = ctx.author.id
        p1_stats["user_name"] = ctx.author.name

        # --- CASE A: PVP (If user mentioned) ---
        if opponent:
            if opponent.bot or opponent == ctx.author:
                return await ctx.send("❌ Invalid opponent!")
            
            p2_data = col.find_one({"_id": str(opponent.id)})
            if not p2_data or "team_name" not in p2_data:
                return await ctx.send(f"❌ **{opponent.name}** doesn't have a team!")

            # চ্যালেঞ্জ পাঠানো
            view = ChallengeView(ctx, opponent)
            msg = await ctx.send(f"⚔️ {opponent.mention}, **{ctx.author.name}** challenged you!", view=view)
            await view.wait()

            if view.accepted:
                p2_stats = calculate_stats(p2_data["team_name"], p2_data.get("team_lvl", 1))
                p2_stats["id"] = opponent.id
                p2_stats["user_name"] = opponent.name

                battle_view = PVPBattleView(ctx, p1_stats, p2_stats)
                await msg.edit(content=None, embed=discord.Embed(title="⚔️ PVP START!", color=discord.Color.red()), view=battle_view)
                await battle_view.update_board(msg.interaction if ctx.interaction else ctx)
            return

        # --- CASE B: PVE (Normal Battle) ---
        # এনিমি জেনারেট
        e_lvl = random.randint(p1_data.get("team_lvl", 1), p1_data.get("team_lvl", 1) + 2)
        enemy_name = random.choice(["Dark Wolf", "Bear", "Goblin"])
        e_stats = calculate_stats(enemy_name, e_lvl) # বেস স্ট্যাটাস ব্যবহার করবে
        
        embed = discord.Embed(title="⚔️ PVE ENCOUNTER!", color=discord.Color.orange())
        msg = await ctx.send(embed=embed)
        
        view = PVEBattleView(ctx, p1_stats, e_stats)
        await view.update_board(msg.interaction if ctx.interaction else ctx)
        await msg.edit(view=view)

async def setup(bot):
    await bot.add_cog(BattleSystem(bot))
    
