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

# ================= 💰 SELL PRICES (দাম) =================
PRICES = {
    "Common": 5,
    "Uncommon": 15,
    "Rare": 50,
    "Epic": 200,
    "Mythic": 1000,
    "Legendary": 5000,
    "Gem": 20000
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

    # ================= 💰 SELL COMMAND (NEW) =================
    @commands.hybrid_command(name="sell", description="💰 Sell animals for cash")
    @app_commands.describe(query="What to sell? (all, common, worm, etc.)")
    async def sell(self, ctx: commands.Context, query: str):
        user = ctx.author
        uid = str(user.id)
        query = query.lower().strip()

        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid})
        
        if not user_data or "zoo" not in user_data or not user_data["zoo"]:
            return await ctx.send("❌ You have no animals to sell!")

        zoo = user_data["zoo"]
        total_earnings = 0
        sold_count = 0
        update_fields = {} # ডিলিট করার লিস্ট
        
        # 1. SELL ALL
        if query == "all":
            for rarity in RARITIES:
                for animal in ANIMALS[rarity]:
                    count = zoo.get(animal, 0)
                    if count > 0:
                        price = PRICES[rarity] * count
                        total_earnings += price
                        sold_count += count
                        update_fields[f"zoo.{animal}"] = ""
            
        # 2. SELL BY RARITY (e.g. sell common)
        elif query.title() in RARITIES:
            target_rarity = query.title()
            for animal in ANIMALS[target_rarity]:
                count = zoo.get(animal, 0)
                if count > 0:
                    price = PRICES[target_rarity] * count
                    total_earnings += price
                    sold_count += count
                    update_fields[f"zoo.{animal}"] = ""

        # 3. SELL SPECIFIC ANIMAL (e.g. sell worm)
        else:
            target_animal = None
            found_rarity = None
            
            # নাম খুঁজে বের করা
            for rarity, animal_list in ANIMALS.items():
                for animal in animal_list:
                    # ইমোজি বাদে নাম (Worm) অথবা পুরো নাম (🐛 Worm)
                    clean_name = animal.split(" ")[1].lower()
                    if query == clean_name or query == animal.lower():
                        target_animal = animal
                        found_rarity = rarity
                        break
                if target_animal: break
            
            if not target_animal:
                return await ctx.send(f"❌ Animal not found: **{query}**")
            
            count = zoo.get(target_animal, 0)
            if count == 0:
                return await ctx.send(f"❌ You don't have any **{target_animal}**!")
            
            total_earnings = PRICES[found_rarity] * count
            sold_count = count
            update_fields[f"zoo.{target_animal}"] = ""

        # --- আপডেট ---
        if sold_count == 0:
            return await ctx.send("❌ Nothing found to sell!")

        # ইনভেন্টরি থেকে ডিলিট
        col.update_one({"_id": uid}, {"$unset": update_fields})
        
        # ব্যালেন্স অ্যাড (যেহেতু হান্টে টাকা নেই, তাই এখানে টাকা পাবে)
        Database.update_balance(uid, total_earnings)

        embed = discord.Embed(
            description=f"💰 Sold **{sold_count}** animals for **{total_earnings}** coins!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    # ================= 💎 USE COMMAND =================
    @commands.hybrid_command(name="use", description="🔮 Use gems (Stackable!)")
    async def use(self, ctx: commands.Context, item: str):
        user = ctx.author
        uid = str(user.id)
        item_name = item.title()
        
        gem_data = GEM_TYPES.get(item_name)
        if not gem_data:
            return await ctx.send("❌ Invalid Item! Try: `Hunting Gem`, `Empowering Gem`.")

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

    # ================= 🏹 HUNT COMMAND (No Cash, Team XP) =================
    @commands.hybrid_command(name="hunt", aliases=["h"], description="🐾 Hunt animals (XP requires Team)")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def hunt(self, ctx: commands.Context):
        user = ctx.author
        uid = str(user.id)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        
        # --- Buff Logic ---
        buffs = user_data.get("buffs", {})
        
        forced_rarity = buffs.get("rarity")
        chosen_rarity = forced_rarity if forced_rarity else random.choices(RARITIES, weights=WEIGHTS, k=1)[0]
        rarity_msg = f"\n💎 **Rarity Gem:** Guaranteed {forced_rarity}!" if forced_rarity else ""

        base_qty = 1
        if buffs.get("hunting"):
            extra = random.randint(1, 2)
            base_qty += extra
            hunt_msg = f"\n🏹 **Hunting Gem:** Found +{extra} extra animals!"
        else:
            hunt_msg = ""

        final_qty = base_qty
        if buffs.get("empower"):
            final_qty *= 2
            emp_msg = f"\n⚡ **Empowering Gem:** Doubled the catch!"
        else:
            emp_msg = ""

        # --- Generate Animals ---
        caught_animals = {}
        for _ in range(final_qty):
            animal = random.choice(ANIMALS[chosen_rarity])
            caught_animals[animal] = caught_animals.get(animal, 0) + 1
            
        # --- XP Logic (Team Check) ---
        battle_team = user_data.get("team", [])
        xp_gain = 0
        
        if battle_team and len(battle_team) > 0:
            xp_gain = 20 * final_qty # XP পাবে
        else:
            xp_gain = 0 # টিম না থাকলে XP পাবে না

        # --- Update DB ---
        update_query = {
            "$unset": {"buffs": ""},
            "$set": {"last_hunt": datetime.datetime.now().isoformat()}
        }
        
        inc_data = {}
        for anim, qty in caught_animals.items():
            inc_data[f"zoo.{anim}"] = qty
        
        if xp_gain > 0:
            inc_data["xp"] = xp_gain
            
        # Note: কোনো ব্যালেন্স আপডেট নেই (টাকা পাবে না)
        
        update_query["$inc"] = inc_data
        col.update_one({"_id": uid}, update_query, upsert=True)

        # --- Embed ---
        unique_animals = ", ".join([f"**{k}** x{v}" for k, v in caught_animals.items()])
        
        embed = discord.Embed(
            description=f"🌿 You caught **{final_qty}** animals!\n{unique_animals}\n{rarity_msg}{hunt_msg}{emp_msg}",
            color=get_theme_color(ctx.guild.id)
        )
        embed.set_author(name=f"{user.name}'s Hunt", icon_url=user.display_avatar.url)
        
        if xp_gain > 0:
            embed.add_field(name="Rewards", value=f"✨ +{xp_gain} XP", inline=True)
            
        embed.add_field(name="Rarity", value=f"{RANK_EMOJIS.get(chosen_rarity)} **{chosen_rarity}**", inline=True)
        
        if xp_gain == 0:
            embed.set_footer(text="Tip: Create a battle team to earn XP!")
            
        await ctx.send(embed=embed)
        
    # --- Error Handler ---
    @hunt.error
    async def hunt_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ **Chill!** You can hunt again in `{error.retry_after:.1f}s`.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(HuntSystem(bot))
        
