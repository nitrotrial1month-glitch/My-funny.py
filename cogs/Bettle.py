import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import random
import asyncio
from database import Database
from utils import get_theme_color

# ================= ⚔️ XP & LEVEL CONFIG =================
XP_PER_LEVEL = 100 # প্রতি ১০০ XP তে ১ লেভেল বাড়বে

# ================= 🖼️ BATTLE ASSETS (Images) =================
# এনিমেলদের জন্য ছবি (আপনি চাইলে আরও অ্যাড করতে পারেন)
ANIMAL_IMAGES = {
    "Dragon": "https://i.imgur.com/example_dragon.png", # ডেমো লিংক
    "Wolf": "https://i.imgur.com/example_wolf.png",
    # যদি ছবি না থাকে, ডিফল্ট ছবি দেখাবে
    "default": "https://media.discordapp.net/attachments/1000000000000000000/1111111111111111111/battle_scene.png"
}

# ================= 📊 STATS CALCULATOR =================
def calculate_stats(base_stats, level):
    """লেভেল অনুযায়ী স্ট্যাটাস বাড়াবে"""
    multiplier = 1 + (level * 0.1) # প্রতি লেভেলে ১০% শক্তি বাড়বে
    return {
        "hp": int(base_stats["hp"] * multiplier),
        "atk": int(base_stats["atk"] * multiplier),
        "def": int(base_stats["def"] * multiplier)
    }

# বেস স্ট্যাটাস (Level 1 Stats)
BASE_STATS = {
    "Common": {"hp": 100, "atk": 15, "def": 5},
    "Uncommon": {"hp": 150, "atk": 25, "def": 10},
    "Rare": {"hp": 250, "atk": 40, "def": 15},
    "Epic": {"hp": 400, "atk": 60, "def": 25},
    "Mythic": {"hp": 700, "atk": 90, "def": 40},
    "Legendary": {"hp": 1000, "atk": 150, "def": 60}
}

# এনিমেল র‍্যাংক ম্যাপ (নাম থেকে র‍্যাংক বের করা)
ANIMAL_RARITY_MAP = {
    "Worm": "Common", "Ant": "Common",
    "Wolf": "Rare", "Fox": "Rare",
    "Dragon": "Mythic", "Demon": "Legendary"
    # বাকিগুলো এখানে অ্যাড করবেন
}

def get_animal_rarity(name):
    # নামের ইমোজি বাদ দিয়ে শুধু টেক্সট নেওয়া (🐛 Worm -> Worm)
    clean_name = name.split(" ")[-1] if " " in name else name
    return ANIMAL_RARITY_MAP.get(clean_name, "Common")

# ================= ⚔️ BATTLE VIEW =================
class BattleView(View):
    def __init__(self, ctx, player, enemy):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.player = player
        self.enemy = enemy
        self.turn = ctx.author
        self.log = "⚔️ **Battle Started!** Waiting for command..."

    def get_hp_bar(self, current, max_hp):
        percent = current / max_hp
        filled = int(percent * 10)
        empty = 10 - filled
        return "🟩" * filled + "⬛" * empty

    async def update_battle(self, interaction, ended=False):
        # ভিজ্যুয়াল এম্বেড
        embed = discord.Embed(
            title=f"⚔️ {self.player['name']} (Lvl {self.player['lvl']}) VS {self.enemy['name']}",
            description=f"**Battle Log:**\n> {self.log}",
            color=discord.Color.red()
        )
        
        # ইমেজ সেট করা (এনিমেলের ছবি বা ব্যাটল সিন)
        img_url = ANIMAL_IMAGES.get(self.player['name_clean'], ANIMAL_IMAGES["default"])
        embed.set_image(url=img_url)

        # প্লেয়ার স্ট্যাটাস
        embed.add_field(
            name=f"🛡️ YOU: {self.player['name']}",
            value=f"{self.get_hp_bar(self.player['hp'], self.player['max_hp'])}\n❤️ {self.player['hp']}/{self.player['max_hp']}",
            inline=True
        )

        # এনিমি স্ট্যাটাস
        embed.add_field(
            name=f"💀 ENEMY: {self.enemy['name']}",
            value=f"{self.get_hp_bar(self.enemy['hp'], self.enemy['max_hp'])}\n❤️ {self.enemy['hp']}/{self.enemy['max_hp']}",
            inline=True
        )

        if ended:
            self.clear_items()
            embed.set_footer(text="Battle Finished")
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            embed.set_footer(text="Choose your move below 👇")
            await interaction.response.edit_message(embed=embed, view=self)

    # --- ⚔️ ATTACK ---
    @discord.ui.button(label="Attack", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def attack(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.turn: return
        
        dmg = random.randint(self.player['atk'] - 5, self.player['atk'] + 5)
        self.enemy['hp'] -= dmg
        self.log = f"💥 You dealt **{dmg}** DMG!"
        
        if self.enemy['hp'] <= 0:
            self.enemy['hp'] = 0
            return await self.end_battle(interaction, win=True)
            
        await self.update_battle(interaction)
        await self.enemy_turn(interaction)

    # --- 🔥 HEAVY ---
    @discord.ui.button(label="Heavy", style=discord.ButtonStyle.primary, emoji="🔥")
    async def heavy(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.turn: return
        
        if random.random() < 0.6: # ৬০% চান্স
            dmg = int(self.player['atk'] * 1.5)
            self.enemy['hp'] -= dmg
            self.log = f"🔥 CRITICAL HIT! **{dmg}** DMG!"
        else:
            self.log = "💨 You missed the Heavy Attack!"
            
        if self.enemy['hp'] <= 0:
            self.enemy['hp'] = 0
            return await self.end_battle(interaction, win=True)

        await self.update_battle(interaction)
        await self.enemy_turn(interaction)

    # --- 💊 HEAL ---
    @discord.ui.button(label="Heal", style=discord.ButtonStyle.success, emoji="💊")
    async def heal(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.turn: return
        
        heal = int(self.player['max_hp'] * 0.3)
        self.player['hp'] = min(self.player['max_hp'], self.player['hp'] + heal)
        self.log = f"💊 Recovered **{heal}** HP!"
        
        await self.update_battle(interaction)
        await self.enemy_turn(interaction)

    # --- 🤖 ENEMY TURN ---
    async def enemy_turn(self, interaction):
        await asyncio.sleep(1.5)
        
        dmg = random.randint(self.enemy['atk'] - 5, self.enemy['atk'] + 5)
        self.player['hp'] -= dmg
        self.log = f"💢 Enemy hit you for **{dmg}** DMG!"
        
        if self.player['hp'] <= 0:
            self.player['hp'] = 0
            return await self.end_battle(interaction, win=False)
            
        # ভিউ রিফ্রেশ (Context সমস্যা এড়াতে message.edit ব্যবহার করা ভালো)
        try:
            embed = interaction.message.embeds[0]
            embed.description = f"**Battle Log:**\n> {self.log}"
            # HP আপডেট
            embed.set_field_at(0, name=f"🛡️ YOU: {self.player['name']}", value=f"{self.get_hp_bar(self.player['hp'], self.player['max_hp'])}\n❤️ {self.player['hp']}/{self.player['max_hp']}", inline=True)
            embed.set_field_at(1, name=f"💀 ENEMY: {self.enemy['name']}", value=f"{self.get_hp_bar(self.enemy['hp'], self.enemy['max_hp'])}\n❤️ {self.enemy['hp']}/{self.enemy['max_hp']}", inline=True)
            await interaction.message.edit(embed=embed)
        except:
            pass

    # --- 🏆 END BATTLE (XP Logic) ---
    async def end_battle(self, interaction, win):
        uid = str(self.ctx.author.id)
        col = Database.get_collection("inventory")
        
        if win:
            xp_gain = random.randint(50, 100) # জিতার জন্য XP
            cash_gain = random.randint(50, 150)
            
            # লেভেল আপ লজিক
            current_xp = self.player['xp'] + xp_gain
            new_level = self.player['lvl']
            
            lvl_msg = ""
            if current_xp >= (new_level * XP_PER_LEVEL):
                new_level += 1
                current_xp = 0 # লেভেল আপ হলে XP রিসেট (বা বিয়োগ করতে পারেন)
                lvl_msg = f"\n🆙 **LEVEL UP!** {self.player['name']} is now Lvl {new_level}!"
            
            # ডাটাবেস আপডেট
            col.update_one(
                {"_id": uid},
                {
                    "$set": {
                        "team_xp": current_xp,
                        "team_lvl": new_level
                    },
                    "$inc": {"balance": cash_gain} # টাকা জিতবে
                }
            )
            
            self.log += f"\n🏆 **VICTORY!**\n✨ +{xp_gain} XP | 💰 +{cash_gain} Coins{lvl_msg}"
        else:
            self.log += "\n☠️ **DEFEAT!** You gained nothing."

        await self.update_battle(interaction, ended=True)

# ================= 🚀 MAIN CLASS =================
class BattleSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- 1. TEAM SETUP ---
    @commands.hybrid_command(name="team_add", description="🐾 Set your main fighter")
    async def team_add(self, ctx, animal_name: str):
        uid = str(ctx.author.id)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid})
        
        # ইনভেন্টরি চেক
        found_name = None
        if user_data and "zoo" in user_data:
            for anim in user_data["zoo"]:
                if animal_name.lower() in anim.lower(): # Partial match
                    found_name = anim
                    break
        
        if not found_name:
            return await ctx.send("❌ You don't own this animal!")

        # টিমে সেট করা (XP এবং Level রিসেট হবে না যদি আগে থেকে থাকে)
        # কিন্তু নতুন এনিমেল দিলে লেভেল ১ থেকে শুরু হবে
        col.update_one(
            {"_id": uid},
            {
                "$set": {
                    "team_name": found_name,
                    "team_lvl": 1, # ডিফল্ট লেভেল ১
                    "team_xp": 0
                }
            },
            upsert=True
        )
        await ctx.send(f"✅ **{found_name}** selected! (Lvl 1)")

    # --- 2. BATTLE ---
    @commands.hybrid_command(name="battle", aliases=["fight"], description="⚔️ Start a visual battle!")
    async def battle(self, ctx):
        uid = str(ctx.author.id)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid})
        
        # টিম চেক
        if not user_data or "team_name" not in user_data:
            return await ctx.send("❌ You don't have a team! Use `/team_add [animal]` first.")

        # ১. প্লেয়ার লোড
        p_name = user_data["team_name"]
        p_lvl = user_data.get("team_lvl", 1)
        p_xp = user_data.get("team_xp", 0)
        
        # বেস স্ট্যাটাস এবং লেভেল অনুযায়ী শক্তি বাড়ানো
        rarity = get_animal_rarity(p_name)
        base = BASE_STATS.get(rarity, BASE_STATS["Common"])
        
        final_stats = calculate_stats(base, p_lvl)
        
        player = {
            "name": p_name,
            "name_clean": p_name.split(" ")[-1] if " " in p_name else p_name,
            "lvl": p_lvl,
            "xp": p_xp,
            "hp": final_stats["hp"],
            "max_hp": final_stats["hp"],
            "atk": final_stats["atk"]
        }

        # ২. এনিমি জেনারেট
        e_lvl = random.randint(p_lvl, p_lvl + 2) # প্লেয়ারের কাছাকাছি লেভেল
        enemy_name = random.choice(["Dark Wolf", "Forest Bear", "Goblin King"])
        
        # এনিমি স্ট্যাটাস (র‍্যান্ডম)
        e_base = {"hp": 100, "atk": 10, "def": 5}
        e_stats = calculate_stats(e_base, e_lvl)
        
        enemy = {
            "name": f"{enemy_name} (Lvl {e_lvl})",
            "hp": e_stats["hp"],
            "max_hp": e_stats["hp"],
            "atk": e_stats["atk"]
        }

        # ৩. ব্যাটেল শুরু
        embed = discord.Embed(
            title="⚔️ ENCOUNTER!",
            description="Loading battle scene...",
            color=discord.Color.orange()
        )
        msg = await ctx.send(embed=embed)
        
        view = BattleView(ctx, player, enemy)
        await view.update_battle(msg.interaction if ctx.interaction else ctx)
        await msg.edit(view=view)

async def setup(bot):
    await bot.add_cog(BattleSystem(bot))

