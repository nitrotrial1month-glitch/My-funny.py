import discord
from discord.ext import commands
import random
import datetime
from collections import Counter
from database import Database
from utils import get_theme_color

# ================= 🐾 ANIMAL & RARITY CONFIG =================
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
BASE_WEIGHTS = [50, 30, 15, 8, 4, 1, 0.1] 

# ================= 💰 SELL PRICES =================
PRICES = {
    "Common": 5, "Uncommon": 15, "Rare": 50, "Epic": 200, 
    "Mythic": 1000, "Legendary": 5000, "Gem": 20000
}

# ================= 💎 ADVANCED GEM DATA & UNIQUE EMOJIS =================
GEM_DATA = {
    # 🏹 Hunting Gems: Base additive for animal count
    "61": {"name": "Common Hunting Gem", "type": "hunting", "val": 2, "dur": 40, "emoji": "🏹⚪"},
    "62": {"name": "Uncommon Hunting Gem", "type": "hunting", "val": 4, "dur": 60, "emoji": "🏹🟢"},
    "63": {"name": "Rare Hunting Gem", "type": "hunting", "val": 7, "dur": 80, "emoji": "🏹🔵"},
    "64": {"name": "Legendary Hunting Gem", "type": "hunting", "val": 12, "dur": 100, "emoji": "🏹🟣"},
    
    # 🌲 Forest Gems: Multiplier for Hunting Gem power
    "71": {"name": "Common Forest Gem", "type": "forest", "val": 1.5, "dur": 40, "emoji": "🌲⚪"},
    "72": {"name": "Uncommon Forest Gem", "type": "forest", "val": 2.0, "dur": 60, "emoji": "🌲🟢"},
    "73": {"name": "Rare Forest Gem", "type": "forest", "val": 3.0, "dur": 80, "emoji": "🌲🔵"},
    "74": {"name": "Legendary Forest Gem", "type": "forest", "val": 5.0, "dur": 100, "emoji": "🌲🟣"},

    # 🍀 Lucky Gems: Increase Rarity Chance + Lootbox Drops
    "81": {"name": "Common Lucky Gem", "type": "lucky", "val": 1.2, "dur": 40, "emoji": "🍀⚪"},
    "82": {"name": "Uncommon Lucky Gem", "type": "lucky", "val": 1.5, "dur": 60, "emoji": "🍀🟢"},
    "83": {"name": "Rare Lucky Gem", "type": "lucky", "val": 2.5, "dur": 80, "emoji": "🍀🔵"},
    "84": {"name": "Legendary Lucky Gem", "type": "lucky", "val": 5.0, "dur": 100, "emoji": "🍀🟣"},
}

NAME_TO_ID = {v["name"]: k for k, v in GEM_DATA.items()}
GEM_DROPS = list(NAME_TO_ID.keys())
DROP_WEIGHTS = [45, 25, 12, 8, 4, 1, 3, 2] # Drop rates from Lootbox

class HuntSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= 🎒 CATEGORIZED INVENTORY =================
    @commands.hybrid_command(name="inventory", aliases=["inv"], description="🎒 Categorized Gem Inventory")
    async def inventory(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        uid = str(target.id)
        col = Database.get_collection("inventory")
        data = col.find_one({"_id": uid}) or {}
        
        lootbox = data.get("inventory", {}).get("lootbox", 0) 
        items = data.get("items", {})

        embed = discord.Embed(title=f"🎒 Inventory of {target.name}", color=get_theme_color(ctx.guild.id))
        
        if lootbox > 0:
            embed.add_field(name="📦 Supplies", value=f"**Lootbox**: {lootbox} (Use `/lb` to open)", inline=False)

        categories = {
            "hunting": "🏹 Hunting Gems (Count +)",
            "forest": "🌲 Forest Gems (Multiplier x)",
            "lucky": "🍀 Lucky Gems (Rarity %)"
        }

        for cat_type, cat_title in categories.items():
            gem_list = []
            for name, count in items.items():
                gem_id = NAME_TO_ID.get(name)
                if gem_id and GEM_DATA[gem_id]["type"] == cat_type and count > 0:
                    gem_list.append(f"`{gem_id}` {GEM_DATA[gem_id]['emoji']} **{name}**: {count}")
            
            if gem_list:
                embed.add_field(name=cat_title, value="\n".join(gem_list), inline=True)

        embed.set_footer(text="Use gems with: /use [id]")
        await ctx.send(embed=embed)

    # ================= 🏹 COMBO HUNT COMMAND =================
    @commands.hybrid_command(name="hunt", aliases=["h"], description="🐾 Hunt with Gem Combos")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def hunt(self, ctx):
        uid = str(ctx.author.id)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        buffs = user_data.get("buffs", {})

        # 1. Calculation Logic
        h_bonus = buffs.get("hunting", {}).get("val", 0)
        f_mult = buffs.get("forest", {}).get("val", 1)
        animal_count = 1 + int(h_bonus * f_mult)

        l_mult = buffs.get("lucky", {}).get("val", 1)
        modified_weights = [w * l_mult if i >= 2 else w for i, w in enumerate(BASE_WEIGHTS)]
        lb_chance = 0.05 * l_mult

        # 2. Results
        chosen_rarity = random.choices(RARITIES, weights=modified_weights, k=1)[0]
        caught = Counter([random.choice(ANIMALS[chosen_rarity]) for _ in range(animal_count)])
        lb_drop = 1 if random.random() < lb_chance else 0

        # 3. Durability Tracking
        upd_set, upd_unset, active_buffs = {}, {}, ""
        for b_type, b_data in buffs.items():
            new_dur = b_data["dur"] - 1
            emoji = b_data.get("emoji", "✨")
            if new_dur > 0:
                upd_set[f"buffs.{b_type}.dur"] = new_dur
                active_buffs += f"{emoji} **{b_type.title()}**: `{new_dur}` left\n"
            else:
                upd_unset[f"buffs.{b_type}"] = ""
                active_buffs += f"⚠️ **{b_type.title()} Gem expired!**\n"

        query = {"$set": {"last_hunt": datetime.datetime.now(datetime.timezone.utc).isoformat()}, "$inc": {}}
        if upd_set: query["$set"].update(upd_set)
        if upd_unset: query["$unset"] = upd_unset
        for a, q in caught.items(): query["$inc"][f"zoo.{a}"] = q
        if lb_drop: query["$inc"]["inventory.lootbox"] = lb_drop
        
        col.update_one({"_id": uid}, query, upsert=True)

        animal_text = ", ".join([f"**{a}** x{q}" for a, q in caught.items()])
        embed = discord.Embed(description=f"🌿 Caught **{animal_count}** animals!\n{animal_text}", color=get_theme_color(ctx.guild.id))
        embed.set_author(name=f"{ctx.author.name}'s Hunt", icon_url=ctx.author.display_avatar.url)
        embed.add_field(name="Rarity", value=f"{RANK_EMOJIS[chosen_rarity]} {chosen_rarity}", inline=True)
        if lb_drop: embed.add_field(name="Lucky Drop", value="🎁 Found a Lootbox!", inline=True)
        if active_buffs: embed.add_field(name="🔮 Active Gem Life", value=active_buffs, inline=False)
        await ctx.send(embed=embed)

    # ================= 💎 USE COMMAND =================
    @commands.hybrid_command(name="use", description="🔮 Activate a gem by ID")
    async def use(self, ctx, gem_id: str):
        uid = str(ctx.author.id)
        gem = GEM_DATA.get(gem_id)
        if not gem: return await ctx.send("❌ Invalid Gem ID!")
# ================= 🎲 LOOTBOX CONFIGURATION (FIXED) =================
# We have 12 gems in total (61-64, 71-74, 81-84)
GEM_DROPS = list(GEM_DATA.values())
GEM_NAMES = [gem["name"] for gem in GEM_DROPS]

# Weights must have exactly 12 values to match the 12 gems
# Order: Hunting (4), Forest (4), Lucky (4)
# We keep higher rarity gems at a much lower percentage
DROP_WEIGHTS = [
    30, 15, 5, 1,  # Hunting Gems (C, U, R, L)
    20, 10, 4, 1,  # Forest Gems (C, U, R, L)
    10, 3, 0.5, 0.5 # Lucky Gems (C, U, R, L) - Very Rare!
]

# Update the lootbox command logic to use GEM_NAMES
@commands.hybrid_command(name="lootbox", aliases=["lb", "open"], description="🎁 Open lootboxes")
async def lootbox(self, ctx, amount: str = "1"):
    uid = str(ctx.author.id)
    col = Database.get_collection("inventory")
    data = col.find_one({"_id": uid}) or {}
    
    # Check both potential paths to be safe
    current_lb = data.get("inventory", {}).get("lootbox", 0)
    old_lb = data.get("items", {}).get("Lootbox", 0)
    total_lb = current_lb + old_lb

    if total_lb < 1: 
        return await ctx.send("❌ You don't have any Lootboxes!")

    open_count = total_lb if amount.lower() == "all" else min(int(amount) if amount.isdigit() else 1, total_lb)

    # FIXED LINE: Using GEM_NAMES and DROP_WEIGHTS (Length 12)
    rewards = random.choices(GEM_NAMES, weights=DROP_WEIGHTS, k=open_count)
    counts = Counter(rewards)

    # Database update
    update_query = {"$inc": {}}
    if old_lb > 0:
        if open_count <= old_lb: update_query["$inc"]["items.Lootbox"] = -open_count
        else:
            update_query["$inc"]["items.Lootbox"] = -old_lb
            update_query["$inc"]["inventory.lootbox"] = -(open_count - old_lb)
    else:
        update_query["$inc"]["inventory.lootbox"] = -open_count

    for name, qty in counts.items():
        update_query["$inc"][f"items.{name}"] = qty
    
    col.update_one({"_id": uid}, update_query, upsert=True)

    res = f"🎁 Opened **{open_count}** Lootbox(es):\n" + "\n".join([f"💎 **{g}**: `x{q}`" for g, q in counts.items()])
    await ctx.send(embed=discord.Embed(description=res, color=discord.Color.gold()))

    # ================= 🦁 ZOO & SELL =================
    @commands.hybrid_command(name="zoo", aliases=["z"], description="🦁 View your animals")
    async def zoo(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        uid = str(target.id)
        col = Database.get_collection("inventory")
        data = col.find_one({"_id": uid}) or {}
        zoo = data.get("zoo", {})
        if not zoo or all(v == 0 for v in zoo.values()): return await ctx.send(f"🦁 **{target.name}** has no animals!")
        desc, total = "", 0
        for rarity in RARITIES:
            found = [f"{a} `x{zoo[a]}`" for a in ANIMALS[rarity] if zoo.get(a, 0) > 0]
            if found:
                desc += f"{RANK_EMOJIS[rarity]} **{rarity}**\n" + ", ".join(found) + "\n\n"
                for a in ANIMALS[rarity]: total += zoo.get(a, 0)
        embed = discord.Embed(title=f"🦁 Zoo of {target.name}", description=desc, color=get_theme_color(ctx.guild.id))
        embed.set_footer(text=f"Total Animals: {total}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="sell", description="💰 Sell animals for coins")
    async def sell(self, ctx, query: str):
        uid = str(ctx.author.id)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid})
        if not user_data or "zoo" not in user_data: return await ctx.send("❌ Your zoo is empty!")
        zoo = user_data["zoo"]
        earnings, sold, unset_fields = 0, 0, {}
        q = query.lower().strip()
        if q == "all":
            for r in RARITIES:
                for a in ANIMALS[r]:
                    if zoo.get(a, 0) > 0: earnings += PRICES[r]*zoo[a]; sold += zoo[a]; unset_fields[f"zoo.{a}"] = ""
        else:
            target = next((a for r in ANIMALS for a in ANIMALS[r] if q in a.lower() and zoo.get(a, 0) > 0), None)
            if not target: return await ctx.send("❌ Animal not found!")
            rarity = next(r for r in RARITIES if target in ANIMALS[r])
            earnings, sold, unset_fields = PRICES[rarity]*zoo[target], zoo[target], {f"zoo.{target}": ""}
        if sold == 0: return await ctx.send("❌ Nothing to sell!")
        col.update_one({"_id": uid}, {"$unset": unset_fields})
        Database.update_balance(uid, earnings)
        await ctx.send(f"💰 Sold **{sold}** animal(s) for **{earnings}** coins!")

    @hunt.error
    async def hunt_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Please wait `{error.retry_after:.1f}` seconds.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(HuntSystem(bot))
        
