import discord
from discord.ext import commands
from discord import app_commands
import random
import datetime
from database import Database
from utils import get_theme_color

# ================= 🐾 ANIMAL DATABASE =================
ANIMALS = {
    "Common": ["🐛 Worm", "🐜 Ant", "🪳 Cockroach", "🦟 Mosquito"],
    "Uncommon": ["🐭 Mouse", "🐸 Frog", "🐍 Snake", "🦇 Bat"],
    "Rare": ["🐺 Wolf", "🦊 Fox", "🐻 Bear", "🐼 Panda"],
    "Epic": ["🦁 Lion", "🐯 Tiger", "🦈 Shark", "🐊 Crocodile"],
    "Mythic": ["🐉 Dragon", "🦄 Unicorn", "🦅 Griffin", "🦕 Dino"],
    "Legendary": ["👹 Demon", "👼 Angel", "👽 Alien", "👾 Glitch"],
    "Gem": ["💎 Diamond Animal", "🔮 Emerald Animal"]
}

RANK_EMOJIS = {
    "Common": "⚪", "Uncommon": "🟢", "Rare": "🔵", 
    "Epic": "🟣", "Mythic": "🟠", "Legendary": "🔴", "Gem": "💎"
}

RARITIES = ["Common", "Uncommon", "Rare", "Epic", "Mythic", "Legendary", "Gem"]
WEIGHTS = [50, 30, 15, 8, 4, 1, 0.1]

# ================= 💎 GEM CONFIGURATION =================
GEM_TYPES = {
    "Common Gem": {"type": "rarity", "value": "Common"},
    "Mythic Gem": {"type": "rarity", "value": "Mythic"},
    "Legendary Gem": {"type": "rarity", "value": "Legendary"},
    "Hunting Gem": {"type": "hunting", "value": 2}, 
    "Empowering Gem": {"type": "empower", "value": 2}
}

class HuntSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= 💎 USE COMMAND (UNCHANGED) =================
    @commands.hybrid_command(name="use", description="🔮 Use gems (Stackable!)")
    async def use(self, ctx: commands.Context, item: str):
        user = ctx.author
        uid = str(user.id)
        item_name = item.title()
        
        gem_data = GEM_TYPES.get(item_name)
        if not gem_data:
            return await ctx.send("❌ Invalid Item! Try: `Hunting Gem`, `Empowering Gem`, or `Mythic Gem`.")

        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        
        if user_data.get("items", {}).get(item_name, 0) < 1:
            return await ctx.send(f"❌ You don't have **{item_name}**!")

        buff_type = gem_data["type"]
        buff_value = gem_data["value"]

        col.update_one(
            {"_id": uid},
            {
                "$inc": {f"items.{item_name}": -1},
                "$set": {f"buffs.{buff_type}": buff_value}
            },
            upsert=True
        )
        
        embed = discord.Embed(
            description=f"🔮 **Activated:** {item_name}\nEffect Type: `{buff_type.upper()}`",
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)

    # ================= 🏹 HUNT COMMAND (UPDATED) =================
    @commands.hybrid_command(name="hunt", aliases=["h"], description="🐾 Hunt animals (No Cash, XP requires Team)")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def hunt(self, ctx: commands.Context):
        user = ctx.author
        uid = str(user.id)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        
        # --- ১. বাফ লোড করা ---
        buffs = user_data.get("buffs", {})
        
        # A. Rarity Check
        forced_rarity = buffs.get("rarity")
        if forced_rarity:
            chosen_rarity = forced_rarity
            rarity_msg = f"\n💎 **Rarity Gem:** Guaranteed {forced_rarity}!"
        else:
            chosen_rarity = random.choices(RARITIES, weights=WEIGHTS, k=1)[0]
            rarity_msg = ""

        # B. Quantity Check (Hunting Gem)
        base_qty = 1
        if buffs.get("hunting"):
            extra = random.randint(1, 2)
            base_qty += extra
            hunt_msg = f"\n🏹 **Hunting Gem:** Found +{extra} extra animals!"
        else:
            hunt_msg = ""

        # C. Multiplier Check (Empowering Gem)
        final_qty = base_qty
        if buffs.get("empower"):
            final_qty *= 2
            emp_msg = f"\n⚡ **Empowering Gem:** Doubled the catch!"
        else:
            emp_msg = ""

        # --- ২. প্রাণী জেনারেট ---
        caught_animals = {}
        
        for _ in range(final_qty):
            animal = random.choice(ANIMALS[chosen_rarity])
            caught_animals[animal] = caught_animals.get(animal, 0) + 1
            
        # --- ৩. XP লজিক (Battle Team Check) ---
        # ডাটাবেসে 'team' বা 'battle_team' নামে লিস্ট থাকতে হবে
        battle_team = user_data.get("team", []) 
        
        xp_gain = 0
        xp_msg = ""

        if battle_team and len(battle_team) > 0:
            # যদি টিম থাকে, তবেই XP পাবে
            xp_gain = 20 * final_qty # প্রতি হান্টে ২০ XP (প্রাণীর সংখ্যার সাথে গুণ হবে)
            xp_msg = f" | ✨ +{xp_gain} XP"
        else:
            # টিম না থাকলে
            xp_msg = "" # XP মেসেজ দেখাবে না

        # --- ৪. ডাটাবেস আপডেট ---
        update_query = {
            "$unset": {"buffs": ""}, # বাফ ক্লিয়ার
            "$set": {"last_hunt": datetime.datetime.now().isoformat()}
        }
        
        inc_data = {}
        for anim, qty in caught_animals.items():
            inc_data[f"zoo.{anim}"] = qty
        
        # শুধু XP যোগ হবে, কোনো Balance (Cash) যোগ হবে না
        if xp_gain > 0:
            inc_data["xp"] = xp_gain
        
        update_query["$inc"] = inc_data
        
        col.update_one({"_id": uid}, update_query, upsert=True)

        # --- ৫. রেজাল্ট এম্বেড ---
        unique_animals = ", ".join([f"**{k}** x{v}" for k, v in caught_animals.items()])
        
        embed = discord.Embed(
            description=f"🌿 You caught **{final_qty}** animals!\n{unique_animals}\n{rarity_msg}{hunt_msg}{emp_msg}",
            color=get_theme_color(ctx.guild.id)
        )
        embed.set_author(name=f"{user.name}'s Hunt", icon_url=user.display_avatar.url)
        
        # Rewards সেকশনে শুধু XP দেখাবে (যদি পায়)
        if xp_gain > 0:
            embed.add_field(name="Rewards", value=f"✨ +{xp_gain} XP", inline=True)
            
        embed.add_field(name="Rarity", value=f"{RANK_EMOJIS.get(chosen_rarity)} **{chosen_rarity}**", inline=True)
        
        if xp_gain == 0:
            embed.set_footer(text="Tip: Create a battle team to earn XP from hunting!")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HuntSystem(bot))
    
