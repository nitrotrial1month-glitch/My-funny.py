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

# ================= 💎 ADVANCED GEM DATA & IDs =================
# Durability: C=40, U=60, R=80, L=100
GEM_DATA = {
    "61": {"name": "Common Hunting Gem", "type": "hunting", "val": 2, "dur": 40, "emoji": "🏹⚪"},
    "62": {"name": "Uncommon Hunting Gem", "type": "hunting", "val": 4, "dur": 60, "emoji": "🏹🟢"},
    "63": {"name": "Rare Hunting Gem", "type": "hunting", "val": 7, "dur": 80, "emoji": "🏹🔵"},
    "64": {"name": "Legendary Hunting Gem", "type": "hunting", "val": 12, "dur": 100, "emoji": "🏹🟣"},
    
    "71": {"name": "Common Forest Gem", "type": "forest", "val": 1.5, "dur": 40, "emoji": "🌲⚪"},
    "72": {"name": "Uncommon Forest Gem", "type": "forest", "val": 2.0, "dur": 60, "emoji": "🌲🟢"},
    "73": {"name": "Rare Forest Gem", "type": "forest", "val": 3.0, "dur": 80, "emoji": "🌲🔵"},
    "74": {"name": "Legendary Forest Gem", "type": "forest", "val": 5.0, "dur": 100, "emoji": "🌲🟣"},

    "81": {"name": "Common Lucky Gem", "type": "lucky", "val": 1.2, "dur": 40, "emoji": "🍀⚪"},
    "82": {"name": "Uncommon Lucky Gem", "type": "lucky", "val": 1.5, "dur": 60, "emoji": "🍀🟢"},
    "83": {"name": "Rare Lucky Gem", "type": "lucky", "val": 2.5, "dur": 80, "emoji": "🍀🔵"},
    "84": {"name": "Legendary Lucky Gem", "type": "lucky", "val": 5.0, "dur": 100, "emoji": "🍀🟣"},
}

NAME_TO_ID = {v["name"]: k for k, v in GEM_DATA.items()}
GEM_NAMES = [gem["name"] for gem in GEM_DATA.values()]

# FIX: Exactly 12 weights to match 12 gems
DROP_WEIGHTS = [
    30, 15, 5, 1,    # Hunting (61-64)
    20, 10, 4, 1,    # Forest (71-74)
    10, 3, 0.5, 0.5  # Lucky (81-84)
]

class HuntSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= 🎒 CATEGORIZED INVENTORY =================
    @commands.hybrid_command(name="inventory", aliases=["inv"], description="🎒 Categorized Inventory")
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

        cats = {"hunting": "🏹 Hunting Gems", "forest": "🌲 Forest Gems", "lucky": "🍀 Lucky Gems"}
        for k, title in cats.items():
            gem_list = [f"`{NAME_TO_ID[n]}` {GEM_DATA[NAME_TO_ID[n]]['emoji']} **{n}**: {items[n]}" 
                        for n in items if n in NAME_TO_ID and GEM_DATA[NAME_TO_ID[n]]["type"] == k and items[n] > 0]
            if gem_list:
                embed.add_field(name=title, value="\n".join(gem_list), inline=True)

        embed.set_footer(text="Use gems with: /use [id]")
        await ctx.send(embed=embed)

    # ================= 🏹 ADVANCED HUNT COMMAND =================
    @commands.hybrid_command(name="hunt", aliases=["h"], description="🐾 Hunt with Gem Combos")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def hunt(self, ctx):
        uid = str(ctx.author.id)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        buffs = user_data.get("buffs", {})

        # Combo Logic: Hunting Bonus x Forest Multiplier
        h_val = buffs.get("hunting", {}).get("val", 0)
        f_mult = buffs.get("forest", {}).get("val", 1)
        animal_count = 1 + int(h_val * f_mult)

        # Lucky Logic: Multiplies Rare Rarity Weights & Lootbox Chance
        l_mult = buffs.get("lucky", {}).get("val", 1)
        mod_weights = [w * l_mult if i >= 2 else w for i, w in enumerate(BASE_WEIGHTS)]
        lb_chance = 0.05 * l_mult

        chosen_rarity = random.choices(RARITIES, weights=mod_weights, k=1)[0]
        caught = Counter([random.choice(ANIMALS[chosen_rarity]) for _ in range(animal_count)])
        lb_drop = 1 if random.random() < lb_chance else 0

        # Durability Tracking
        upd_set, upd_unset, active_buffs = {}, {}, ""
        for b_type, b_data in buffs.items():
            new_dur = b_data["dur"] - 1
            emoji = b_data.get("emoji", "✨")
            if new_dur > 0:
                upd_set[f"buffs.{b_type}.dur"] = new_dur
                active_buffs += f"{emoji} **{b_type.title()}**: `{new_dur}` hunts left\n"
            else:
                upd_unset[f"buffs.{b_type}"] = ""
                active_buffs += f"⚠️ **{b_type.title()} Gem expired!**\n"

        upd = {"$set": {"last_hunt": datetime.datetime.now(datetime.timezone.utc).isoformat()}, "$inc": {}}
        if upd_set: upd["$set"].update(upd_set)
        if upd_unset: upd["$unset"] = upd_unset
        for a, q in caught.items(): upd["$inc"][f"zoo.{a}"] = q
        if lb_drop: upd["$inc"]["inventory.lootbox"] = lb_drop
        
        col.update_one({"_id": uid}, upd, upsert=True)

        res = f"🌿 Caught **{animal_count}** animals!\n" + ", ".join([f"**{a}** x{q}" for a, q in caught.items()])
        embed = discord.Embed(description=res, color=get_theme_color(ctx.guild.id))
        embed.set_author(name=f"{ctx.author.name}'s Hunt", icon_url=ctx.author.display_avatar.url)
        embed.add_field(name="Rarity", value=f"{RANK_EMOJIS[chosen_rarity]} {chosen_rarity}", inline=True)
        if lb_drop: embed.add_field(name="Lucky Catch", value="🎁 Found a Lootbox!", inline=True)
        if active_buffs: embed.add_field(name="🔮 Active Gem Life", value=active_buffs, inline=False)
        await ctx.send(embed=embed)

    # ================= 🎁 OPEN LOOTBOX COMMAND =================
    @commands.hybrid_command(name="lootbox", aliases=["lb", "open"], description="🎁 Open lootboxes")
    async def lootbox(self, ctx, amount: str = "1"):
        uid = str(ctx.author.id)
        col = Database.get_collection("inventory")
        data = col.find_one({"_id": uid}) or {}
        
        # Checking both paths for compatibility
        current_lb = data.get("inventory", {}).get("lootbox", 0)
        old_lb = data.get("items", {}).get("Lootbox", 0)
        total_lb = current_lb + old_lb

        if total_lb < 1: return await ctx.send("❌ No Lootboxes found!")
        open_count = total_lb if amount.lower() == "all" else min(int(amount) if amount.isdigit() else 1, total_lb)

        # FIXED logic to prevent ValueError
        rewards = random.choices(GEM_NAMES, weights=DROP_WEIGHTS, k=open_count)
        counts = Counter(rewards)

        update_query = {"$inc": {}}
        if old_lb > 0:
            if open_count <= old_lb: update_query["$inc"]["items.Lootbox"] = -open_count
            else:
                update_query["$inc"]["items.Lootbox"] = -old_lb
                update_query["$inc"]["inventory.lootbox"] = -(open_count - old_lb)
        else:
            update_query["$inc"]["inventory.lootbox"] = -open_count

        for gem, qty in counts.items(): update_query["$inc"][f"items.{gem}"] = qty
        
        col.update_one({"_id": uid}, update_query, upsert=True)
        res = f"🎁 Opened **{open_count}** Lootbox(es):\n" + "\n".join([f"💎 **{g}**: `x{q}`" for g, q in counts.items()])
        await ctx.send(embed=discord.Embed(description=res, color=discord.Color.gold()))

    # ================= 💎 USE COMMAND =================
    @commands.hybrid_command(name="use")
    async def use(self, ctx, gem_id: str):
        uid = str(ctx.author.id)
        gem = GEM_DATA.get(gem_id)
        if not gem: return await ctx.send("❌ Invalid Gem ID!")
        
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        if user_data.get("items", {}).get(gem["name"], 0) < 1:
            return await ctx.send(f"❌ You don't have any **{gem['name']}**!")

        col.update_one({"_id": uid}, {"$inc": {f"items.{gem['name']}": -1}, "$set": {f"buffs.{gem['type']}": {"val": gem["val"], "dur": gem["dur"], "emoji": gem["emoji"]}}}, upsert=True)
        await ctx.send(f"🔮 Activated {gem['emoji']} **{gem['name']}**! Durable for `{gem['dur']}` hunts.")

    # ================= 🦁 ZOO & SELL =================
    @commands.hybrid_command(name="zoo", aliases=["z"])
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

    @commands.hybrid_command(name="sell")
    async def sell(self, ctx, query: str):
        uid = str(ctx.author.id)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid})
        if not user_data or "zoo" not in user_data: return await ctx.send("❌ Zoo is empty!")
        zoo = user_data["zoo"]
        earnings, sold, unset_fields = 0, 0, {}
        q = query.lower().strip()
        if q == "all":
            for r in RARITIES:
                for a in ANIMALS[r]:
                    if zoo.get(a, 0) > 0: earnings += PRICES[r]*zoo[a]; sold += zoo[a]; unset_fields[f"zoo.{a}"] = ""
        else:
            target = next((a for r in ANIMALS for a in ANIMALS[r] if q in a.lower() and zoo.get(a, 0) > 0), None)
            if not target: return await ctx.send("❌ No such animal!")
            rarity = next(r for r in RARITIES if target in ANIMALS[r])
            earnings, sold, unset_fields = PRICES[rarity]*zoo[target], zoo[target], {f"zoo.{target}": ""}
        if sold == 0: return await ctx.send("❌ Nothing found!")
        col.update_one({"_id": uid}, {"$unset": unset_fields})
        Database.update_balance(uid, earnings)
        await ctx.send(f"💰 Sold **{sold}** animal(s) for **{earnings}** coins!")

    @hunt.error
    async def hunt_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Please wait `{error.retry_after:.1f}` seconds.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(HuntSystem(bot))
        
