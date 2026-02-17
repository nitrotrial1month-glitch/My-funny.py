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
# কোন জেম কি কাজ করবে
GEM_TYPES = {
    # 1. Tier Gems (Rarity Guarantee)
    "Common Gem": {"type": "rarity", "value": "Common"},
    "Mythic Gem": {"type": "rarity", "value": "Mythic"},
    "Legendary Gem": {"type": "rarity", "value": "Legendary"},
    
    # 2. Special Gems
    "Hunting Gem": {"type": "hunting", "value": 2}, # ২-৩টি অতিরিক্ত প্রাণী
    "Empowering Gem": {"type": "empower", "value": 2} # প্রাণী দ্বিগুণ হবে
}

class HuntSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= 💎 USE COMMAND (MULTI-SLOT) =================
    @commands.hybrid_command(name="use", description="🔮 Use gems (Stackable!)")
    async def use(self, ctx: commands.Context, item: str):
        user = ctx.author
        uid = str(user.id)
        item_name = item.title() # "hunting gem" -> "Hunting Gem"
        
        # ১. জেম ভ্যালিড কিনা চেক
        gem_data = GEM_TYPES.get(item_name)
        if not gem_data:
            return await ctx.send("❌ Invalid Item! Try: `Hunting Gem`, `Empowering Gem`, or `Mythic Gem`.")

        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        
        # ২. ইনভেন্টরি চেক
        if user_data.get("items", {}).get(item_name, 0) < 1:
            return await ctx.send(f"❌ You don't have **{item_name}**!")

        # ৩. বাফ সেট করা (Slot অনুযায়ী)
        buff_type = gem_data["type"] # rarity / hunting / empower
        buff_value = gem_data["value"]

        # ডাটাবেস আপডেট (Slot-based)
        # buffs.rarity, buffs.hunting, buffs.empower আলাদা আলাদা সেভ হবে
        col.update_one(
            {"_id": uid},
            {
                "$inc": {f"items.{item_name}": -1}, # ১টা জেম কমবে
                "$set": {f"buffs.{buff_type}": buff_value} # নির্দিষ্ট স্লটে বাফ বসবে
            },
            upsert=True
        )
        
        embed = discord.Embed(
            description=f"🔮 **Activated:** {item_name}\nEffect Type: `{buff_type.upper()}`",
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)

    # ================= 🏹 HUNT COMMAND (COMBO LOGIC) =================
    @commands.hybrid_command(name="hunt", aliases=["h"], description="🐾 Hunt with Gem Combos!")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def hunt(self, ctx: commands.Context):
        user = ctx.author
        uid = str(user.id)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        
        # --- ১. বাফ লোড করা ---
        buffs = user_data.get("buffs", {})
        
        # A. Rarity Check (Tier Gem)
        forced_rarity = buffs.get("rarity") # যেমন: Mythic
        if forced_rarity:
            chosen_rarity = forced_rarity
            rarity_msg = f"\n💎 **Rarity Gem:** Guaranteed {forced_rarity}!"
        else:
            chosen_rarity = random.choices(RARITIES, weights=WEIGHTS, k=1)[0]
            rarity_msg = ""

        # B. Quantity Check (Hunting Gem)
        # নরমাল ১টি, হান্টিং জেম থাকলে ২-৩টি
        base_qty = 1
        if buffs.get("hunting"):
            extra = random.randint(1, 2)
            base_qty += extra
            hunt_msg = f"\n🏹 **Hunting Gem:** Found +{extra} extra animals!"
        else:
            hunt_msg = ""

        # C. Multiplier Check (Empowering Gem)
        # এমপাওয়ার জেম থাকলে মোট সংখ্যা দ্বিগুণ
        final_qty = base_qty
        if buffs.get("empower"):
            final_qty *= 2
            emp_msg = f"\n⚡ **Empowering Gem:** Doubled the catch!"
        else:
            emp_msg = ""

        # --- ২. প্রাণী জেনারেট ---
        # একই প্রাণী বারবার না দিয়ে ওই র‍্যাংক থেকে র‍্যান্ডম প্রাণী দিবে
        caught_animals = {}
        found_names = []
        
        for _ in range(final_qty):
            animal = random.choice(ANIMALS[chosen_rarity])
            caught_animals[animal] = caught_animals.get(animal, 0) + 1
            found_names.append(animal)
            
        # --- ৩. ডাটাবেস আপডেট ---
        # সব বাফ রিমুভ করা (একবার ব্যবহারের পর)
        update_query = {
            "$unset": {"buffs": ""}, # সব বাফ ক্লিয়ার
            "$set": {"last_hunt": datetime.datetime.now().isoformat()}
        }
        
        # ইনভেন্টরি আপডেট লুপ
        inc_data = {}
        for anim, qty in caught_animals.items():
            inc_data[f"zoo.{anim}"] = qty
            
        # টাকা এবং XP
        total_cash = random.randint(20, 50) * final_qty
        inc_data["balance"] = total_cash
        
        update_query["$inc"] = inc_data
        
        col.update_one({"_id": uid}, update_query)
        Database.update_balance(uid, total_cash) # ইকোনমি সিঙ্ক

        # --- ৪. রেজাল্ট এম্বেড ---
        unique_animals = ", ".join([f"**{k}** x{v}" for k, v in caught_animals.items()])
        
        embed = discord.Embed(
            description=f"🌿 You caught **{final_qty}** animals!\n{unique_animals}\n{rarity_msg}{hunt_msg}{emp_msg}",
            color=get_theme_color(ctx.guild.id)
        )
        embed.set_author(name=f"{user.name}'s Hunt", icon_url=user.display_avatar.url)
        embed.add_field(name="Rarity", value=f"{RANK_EMOJIS.get(chosen_rarity)} **{chosen_rarity}**", inline=True)
        embed.add_field(name="Earned", value=f"💰 {total_cash}", inline=True)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HuntSystem(bot))
      
