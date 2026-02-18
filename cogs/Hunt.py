import discord
from discord.ext import commands
from discord import app_commands
import random
import datetime
from collections import Counter
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

# ================= 💰 SELL PRICES =================
PRICES = {
    "Common": 5, "Uncommon": 15, "Rare": 50, "Epic": 200, 
    "Mythic": 1000, "Legendary": 5000, "Gem": 20000
}

# ================= 🆔 ITEM CONFIGURATION =================
ITEM_IDS = {
    "50": "Lootbox",
    "51": "Common Gem",
    "52": "Uncommon Gem",
    "53": "Rare Gem",
    "54": "Epic Gem",
    "55": "Mythic Gem",
    "56": "Legendary Gem",
    "57": "Hunting Gem",
    "58": "Empowering Gem"
}

NAME_TO_ID = {v: k for k, v in ITEM_IDS.items()}

GEM_TYPES = {
    "Common Gem": {"type": "rarity", "value": "Common"},
    "Mythic Gem": {"type": "rarity", "value": "Mythic"},
    "Legendary Gem": {"type": "rarity", "value": "Legendary"},
    "Hunting Gem": {"type": "hunting", "value": 2}, 
    "Empowering Gem": {"type": "empower", "value": 2}
}

GEM_DROPS = ["Common Gem", "Uncommon Gem", "Rare Gem", "Epic Gem", "Mythic Gem", "Legendary Gem", "Hunting Gem", "Empowering Gem"]
DROP_WEIGHTS = [40, 25, 15, 10, 4, 1, 3, 2]

class HuntSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= 🎒 INVENTORY COMMAND =================
    @commands.hybrid_command(name="inventory", aliases=["inv"], description="🎒 Check your items and gems")
    async def inventory(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        uid = str(target.id)
        col = Database.get_collection("inventory")
        data = col.find_one({"_id": uid}) or {}
        
        items = data.get("items", {})
        # আপনার ডেইলি কমান্ডের সাথে মিল রেখে inventory.lootbox থেকে চেক করবে
        lootbox_count = data.get("inventory", {}).get("lootbox", 0)

        if not items and lootbox_count == 0:
            return await ctx.send(f"🎒 **{target.name}**'s inventory is empty!")

        desc = ""
        # ১. লুটবক্স ডিসপ্লে
        if lootbox_count > 0:
            desc += f"`50` 🎁 **Lootbox**: {lootbox_count}\n"
        
        # ২. জেম ডিসপ্লে (Gems are still in 'items' field)
        gem_text = ""
        for name, count in items.items():
            if count <= 0: continue
            iid = NAME_TO_ID.get(name, "??")
            gem_text += f"`{iid}` **{name}**: {count}\n"
        
        if gem_text: desc += "\n**💎 Gems**\n" + gem_text

        embed = discord.Embed(title=f"🎒 {target.name}'s Bag", description=desc if desc else "Empty", color=get_theme_color(ctx.guild.id))
        embed.set_footer(text="Use items with /use [id]")
        await ctx.send(embed=embed)

    # ================= 🎁 OPEN LOOTBOX COMMAND =================
    @commands.hybrid_command(name="lootbox", aliases=["lb", "open"], description="🎁 Open lootboxes for gems")
    async def lootbox(self, ctx: commands.Context, amount: str = "1"):
        uid = str(ctx.author.id)
        col = Database.get_collection("inventory")
        data = col.find_one({"_id": uid}) or {}
        
        # inventory.lootbox থেকে বক্স সংখ্যা নেওয়া
        current_lb = data.get("inventory", {}).get("lootbox", 0)

        if current_lb < 1: return await ctx.send("❌ You don't have any lootboxes!")

        if amount.lower() == "all": open_count = current_lb
        elif amount.isdigit(): open_count = min(int(amount), current_lb)
        else: open_count = 1

        rewards = random.choices(GEM_DROPS, weights=DROP_WEIGHTS, k=open_count)
        counts = Counter(rewards)

        # inventory.lootbox কমানো এবং items ফিল্ডে জেম যোগ করা
        update = {"$inc": {"inventory.lootbox": -open_count}}
        for gem, qty in counts.items():
            update["$inc"][f"items.{gem}"] = qty
        
        col.update_one({"_id": uid}, update, upsert=True)

        res = f"🎁 Opened **{open_count}** Lootboxes:\n"
        for gem, qty in counts.items():
            res += f"💎 **{gem}**: `x{qty}`\n"
        
        await ctx.send(embed=discord.Embed(description=res, color=discord.Color.gold()))

    # ================= 🏹 HUNT COMMAND =================
    @commands.hybrid_command(name="hunt", aliases=["h"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def hunt(self, ctx: commands.Context):
        uid = str(ctx.author.id)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        buffs = user_data.get("buffs", {})

        chosen_rarity = buffs.get("rarity") if buffs.get("rarity") else random.choices(RARITIES, weights=WEIGHTS, k=1)[0]
        base_qty = 1 + random.randint(1, 2) if buffs.get("hunting") else 1
        final_qty = base_qty * 2 if buffs.get("empower") else base_qty

        caught = Counter([random.choice(ANIMALS[chosen_rarity]) for _ in range(final_qty)])
        lb_drop = 1 if random.random() < 0.05 else 0

        upd = {"$unset": {"buffs": ""}, "$set": {"last_hunt": datetime.datetime.now(datetime.timezone.utc).isoformat()}, "$inc": {}}
        for a, q in caught.items(): upd["$inc"][f"zoo.{a}"] = q
        
        # হান্টে পাওয়া বক্স inventory.lootbox পাথে জমা হবে
        if lb_drop: upd["$inc"]["inventory.lootbox"] = lb_drop
        
        # XP লজিক
        battle_team = user_data.get("team", [])
        xp = (20 * final_qty) if battle_team else 0
        if xp: upd["$inc"]["xp"] = xp

        col.update_one({"_id": uid}, upd, upsert=True)

        res = f"🌿 Caught **{final_qty}** animals: " + ", ".join([f"**{a}** x{q}" for a, q in caught.items()])
        if lb_drop: res += f"\n🎁 Found **{lb_drop}** Lootbox!"
        
        embed = discord.Embed(description=res, color=get_theme_color(ctx.guild.id))
        embed.set_author(name=f"{ctx.author.name}'s Hunt", icon_url=ctx.author.display_avatar.url)
        embed.add_field(name="Rarity", value=f"{RANK_EMOJIS[chosen_rarity]} {chosen_rarity}")
        if xp: embed.add_field(name="XP", value=f"✨ +{xp}")
        await ctx.send(embed=embed)

    # ================= 🦁 ZOO COMMAND =================
    @commands.hybrid_command(name="zoo", aliases=["z"])
    async def zoo(self, ctx: commands.Context, member: discord.Member = None):
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
        embed = discord.Embed(title=f"🦁 {target.name}'s Zoo", description=desc, color=get_theme_color(ctx.guild.id))
        embed.set_footer(text=f"Total Animals: {total}")
        await ctx.send(embed=embed)

    # ================= 💰 SELL COMMAND =================
    @commands.hybrid_command(name="sell")
    async def sell(self, ctx: commands.Context, query: str):
        uid = str(ctx.author.id)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid})
        if not user_data or "zoo" not in user_data: return await ctx.send("❌ Empty zoo!")
        zoo = user_data["zoo"]
        earnings, sold, unset_fields = 0, 0, {}
        q = query.lower().strip()
        if q == "all":
            for r in RARITIES:
                for a in ANIMALS[r]:
                    if zoo.get(a, 0) > 0: earnings += PRICES[r]*zoo[a]; sold += zoo[a]; unset_fields[f"zoo.{a}"] = ""
        elif q.title() in RARITIES:
            r = q.title()
            for a in ANIMALS[r]:
                if zoo.get(a, 0) > 0: earnings += PRICES[r]*zoo[a]; sold += zoo[a]; unset_fields[f"zoo.{a}"] = ""
        else:
            target = next((a for r in ANIMALS for a in ANIMALS[r] if q in a.lower() and zoo.get(a, 0) > 0), None)
            if not target: return await ctx.send("❌ No such animal!")
            rarity = next(r for r in RARITIES if target in ANIMALS[r])
            earnings, sold, unset_fields = PRICES[rarity]*zoo[target], zoo[target], {f"zoo.{target}": ""}
        if sold == 0: return await ctx.send("❌ Nothing to sell!")
        col.update_one({"_id": uid}, {"$unset": unset_fields})
        Database.update_balance(uid, earnings)
        await ctx.send(f"💰 Sold **{sold}** animals for **{earnings}** coins!")

    # ================= 💎 USE COMMAND =================
    @commands.hybrid_command(name="use")
    async def use(self, ctx: commands.Context, item: str):
        uid = str(ctx.author.id)
        if item.isdigit(): item_name = ITEM_IDS.get(item)
        else: item_name = item.title() if "Gem" in item.title() else f"{item.title()} Gem"
        if item_name not in GEM_TYPES: return await ctx.send("❌ Invalid Item!")
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        if user_data.get("items", {}).get(item_name, 0) < 1: return await ctx.send(f"❌ No {item_name} found!")
        buff = GEM_TYPES[item_name]
        col.update_one({"_id": uid}, {"$inc": {f"items.{item_name}": -1}, "$set": {f"buffs.{buff['type']}": buff['value']}}, upsert=True)
        await ctx.send(f"🔮 Activated **{item_name}**!")

    @hunt.error
    async def hunt_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Wait `{error.retry_after:.1f}s`.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(HuntSystem(bot))
        
