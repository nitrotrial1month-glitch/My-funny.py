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
HUNT_WEIGHTS = [50, 30, 15, 8, 4, 1, 0.1] # হান্টে প্রাণী পাওয়ার চান্স

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

# জেমের কার্যকারিতা (হান্টে এই বাফগুলো ইউজ হবে)
GEM_TYPES = {
    "Common Gem": {"type": "rarity", "value": "Common"},
    "Rare Gem": {"type": "rarity", "value": "Rare"},
    "Mythic Gem": {"type": "rarity", "value": "Mythic"},
    "Legendary Gem": {"type": "rarity", "value": "Legendary"},
    "Hunting Gem": {"type": "hunting", "value": 2}, 
    "Empowering Gem": {"type": "empower", "value": 2}
}

# ================= 🎲 LOOTBOX DROP RATES =================
# শুধুমাত্র জেমস পাওয়া যাবে। রেয়ার আইটেমের চান্স খুব কম রাখা হয়েছে।
GEM_DROPS = [
    "Common Gem", "Uncommon Gem", "Rare Gem", 
    "Epic Gem", "Mythic Gem", "Legendary Gem",
    "Hunting Gem", "Empowering Gem"
]
# ওজন (Weights): Common ও Uncommon বেশি, Legendary ও Special খুব কম।
DROP_WEIGHTS = [55, 25, 10, 5, 3, 1, 0.5, 0.5] 

class HuntSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= 🎒 INVENTORY COMMAND =================
    @commands.hybrid_command(name="inventory", aliases=["inv"], description="🎒 আপনার ব্যাগ এবং আইটেম চেক করুন")
    async def inventory(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        uid = str(target.id)
        col = Database.get_collection("inventory")
        data = col.find_one({"_id": uid}) or {}
        
        lootbox_count = data.get("inventory", {}).get("lootbox", 0) # inventory.lootbox পাথ
        items = data.get("items", {})

        if not items and lootbox_count == 0:
            return await ctx.send(f"🎒 **{target.name}**-এর ইনভেন্টরি খালি!")

        desc = ""
        if lootbox_count > 0:
            desc += f"`50` 🎁 **Lootbox**: {lootbox_count}\n"
        
        gem_text = ""
        for name, count in items.items():
            if count <= 0: continue
            iid = NAME_TO_ID.get(name, "??")
            gem_text += f"`{iid}` **{name}**: {count}\n"
        
        if gem_text: desc += "\n**💎 Gems**\n" + gem_text

        embed = discord.Embed(title=f"🎒 {target.name}-এর ব্যাগ", description=desc if desc else "খালি", color=get_theme_color(ctx.guild.id))
        embed.set_footer(text="আইটেম ব্যবহার করতে লিখুন: /use [id]")
        await ctx.send(embed=embed)

    # ================= 🎁 OPEN LOOTBOX COMMAND =================
    @commands.hybrid_command(name="lootbox", aliases=["lb", "open"], description="🎁 লুডবক্স খুলে জেমস পান")
    async def lootbox(self, ctx: commands.Context, amount: str = "1"):
        uid = str(ctx.author.id)
        col = Database.get_collection("inventory")
        data = col.find_one({"_id": uid}) or {}
        
        current_lb = data.get("inventory", {}).get("lootbox", 0) # inventory.lootbox পাথ

        if current_lb < 1: 
            return await ctx.send("❌ আপনার কাছে কোনো **Lootbox** নেই!")

        if amount.lower() == "all": 
            open_count = current_lb
        elif amount.isdigit(): 
            open_count = min(int(amount), current_lb)
        else: 
            open_count = 1

        rewards = random.choices(GEM_DROPS, weights=DROP_WEIGHTS, k=open_count)
        counts = Counter(rewards)

        # ডাটাবেস আপডেট (inventory.lootbox থেকে কমবে)
        update = {"$inc": {"inventory.lootbox": -open_count}}
        for gem, qty in counts.items():
            update["$inc"][f"items.{gem}"] = qty
        
        col.update_one({"_id": uid}, update, upsert=True)

        res = f"🎁 আপনি **{open_count}**টি লুডবক্স খুলেছেন এবং পেয়েছেন:\n"
        for gem, qty in counts.items():
            res += f"💎 **{gem}**: `x{qty}`\n"
        
        await ctx.send(embed=discord.Embed(description=res, color=discord.Color.gold()))

    # ================= 🏹 HUNT COMMAND =================
    @commands.hybrid_command(name="hunt", aliases=["h"], description="🐾 প্রাণী শিকার করুন")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def hunt(self, ctx: commands.Context):
        uid = str(ctx.author.id)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        buffs = user_data.get("buffs", {})

        # জেম বাফ লজিক (র‍্যারিটি, হান্টিং ও এমপাওয়ার জেম হান্টে কাজ করবে)
        chosen_rarity = buffs.get("rarity") if buffs.get("rarity") else random.choices(RARITIES, weights=HUNT_WEIGHTS, k=1)[0]
        base_qty = 1 + random.randint(1, 2) if buffs.get("hunting") else 1
        final_qty = base_qty * 2 if buffs.get("empower") else base_qty

        caught = Counter([random.choice(ANIMALS[chosen_rarity]) for _ in range(final_qty)])
        lb_drop = 1 if random.random() < 0.05 else 0 # ৫% চান্সে লুডবক্স ড্রপ

        # ডাটাবেস আপডেট (বাফ রিসেট হবে এবং লুডবক্স inventory.lootbox-এ যাবে)
        upd = {"$unset": {"buffs": ""}, "$set": {"last_hunt": datetime.datetime.now(datetime.timezone.utc).isoformat()}, "$inc": {}}
        for a, q in caught.items(): 
            upd["$inc"][f"zoo.{a}"] = q
        
        if lb_drop: 
            upd["$inc"]["inventory.lootbox"] = lb_drop
        
        battle_team = user_data.get("team", [])
        xp = (20 * final_qty) if battle_team else 0
        if xp: upd["$inc"]["xp"] = xp

        col.update_one({"_id": uid}, upd, upsert=True)

        res = f"🌿 আপনি **{final_qty}**টি প্রাণী ধরেছেন: " + ", ".join([f"**{a}** x{q}" for a, q in caught.items()])
        if lb_drop: res += f"\n🎁 আপনি একটি **Lootbox** পেয়েছেন!"
        
        embed = discord.Embed(description=res, color=get_theme_color(ctx.guild.id))
        embed.set_author(name=f"{ctx.author.name}-এর শিকার", icon_url=ctx.author.display_avatar.url)
        embed.add_field(name="Rarity", value=f"{RANK_EMOJIS[chosen_rarity]} {chosen_rarity}")
        if xp: embed.add_field(name="XP", value=f"✨ +{xp} XP")
        await ctx.send(embed=embed)

    # ================= 💰 SELL COMMAND =================
    @commands.hybrid_command(name="sell", description="💰 প্রাণী বিক্রি করে কয়েন আয় করুন")
    async def sell(self, ctx: commands.Context, query: str):
        uid = str(ctx.author.id)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid})
        if not user_data or "zoo" not in user_data: return await ctx.send("❌ আপনার চিড়িয়াখানা খালি!")
        
        zoo = user_data["zoo"]
        earnings, sold, unset_fields = 0, 0, {}
        q = query.lower().strip()
        
        if q == "all":
            for r in RARITIES:
                for a in ANIMALS[r]:
                    if zoo.get(a, 0) > 0: earnings += PRICES[r]*zoo[a]; sold += zoo[a]; unset_fields[f"zoo.{a}"] = ""
        else:
            target = next((a for r in ANIMALS for a in ANIMALS[r] if q in a.lower() and zoo.get(a, 0) > 0), None)
            if not target: return await ctx.send("❌ প্রাণীটি খুঁজে পাওয়া যায়নি!")
            rarity = next(r for r in RARITIES if target in ANIMALS[r])
            earnings, sold, unset_fields = PRICES[rarity]*zoo[target], zoo[target], {f"zoo.{target}": ""}
            
        if sold == 0: return await ctx.send("❌ বিক্রি করার মতো কিছু নেই!")
        col.update_one({"_id": uid}, {"$unset": unset_fields})
        Database.update_balance(uid, earnings)
        await ctx.send(f"💰 আপনি **{sold}**টি প্রাণী বিক্রি করে **{earnings}** কয়েন পেয়েছেন!")

    # ================= 🦁 ZOO COMMAND =================
    @commands.hybrid_command(name="zoo", aliases=["z"], description="🦁 আপনার শিকার করা সব প্রাণী দেখুন")
    async def zoo(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        uid = str(target.id)
        col = Database.get_collection("inventory")
        data = col.find_one({"_id": uid}) or {}
        zoo = data.get("zoo", {})
        if not zoo or all(v == 0 for v in zoo.values()): return await ctx.send(f"🦁 **{target.name}**-এর কাছে কোনো প্রাণী নেই!")
        desc, total = "", 0
        for rarity in RARITIES:
            found = [f"{a} `x{zoo[a]}`" for a in ANIMALS[rarity] if zoo.get(a, 0) > 0]
            if found:
                desc += f"{RANK_EMOJIS[rarity]} **{rarity}**\n" + ", ".join(found) + "\n\n"
                for a in ANIMALS[rarity]: total += zoo.get(a, 0)
        embed = discord.Embed(title=f"🦁 {target.name}-এর চিড়িয়াখানা", description=desc, color=get_theme_color(ctx.guild.id))
        embed.set_footer(text=f"সর্বমোট প্রাণী: {total}")
        await ctx.send(embed=embed)

    # ================= 💎 USE COMMAND =================
    @commands.hybrid_command(name="use", description="🔮 হান্টে বাফ পাওয়ার জন্য জেম ব্যবহার করুন")
    async def use(self, ctx: commands.Context, item: str):
        uid = str(ctx.author.id)
        if item.isdigit(): item_name = ITEM_IDS.get(item)
        else: item_name = item.title() if "Gem" in item.title() else f"{item.title()} Gem"
        
        if item_name not in GEM_TYPES: return await ctx.send("❌ ভুল আইটেম!")
        
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        if user_data.get("items", {}).get(item_name, 0) < 1: return await ctx.send(f"❌ আপনার কাছে কোনো **{item_name}** নেই!")
        
        buff = GEM_TYPES[item_name]
        # জেম ব্যবহার করলে হান্টে ওই র‍্যারিটি বা সুবিধা পাওয়া যাবে
        col.update_one({"_id": uid}, {"$inc": {f"items.{item_name}": -1}, "$set": {f"buffs.{buff['type']}": buff['value']}}, upsert=True)
        await ctx.send(f"🔮 **{item_name}** অ্যাক্টিভেট করা হয়েছে! পরবর্তী হান্টে এটি কাজ করবে।")

    @hunt.error
    async def hunt_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ অনুগ্রহ করে `{error.retry_after:.1f}` সেকেন্ড অপেক্ষা করুন।", ephemeral=True)

async def setup(bot):
    await bot.add_cog(HuntSystem(bot))
        
