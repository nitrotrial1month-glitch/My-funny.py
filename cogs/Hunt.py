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
HUNT_WEIGHTS = [50, 30, 15, 8, 4, 1, 0.1] 

# ================= 💰 SELL PRICES =================
PRICES = {
    "Common": 5, "Uncommon": 15, "Rare": 50, "Epic": 200, 
    "Mythic": 1000, "Legendary": 5000, "Gem": 20000
}

# ================= 🆔 GEM ID CONFIGURATION =================
# ID is only for Gems. Lootbox is opened via /lb command.
GEM_IDS = {
    "51": "Common Gem",
    "52": "Uncommon Gem",
    "53": "Rare Gem",
    "54": "Epic Gem",
    "55": "Mythic Gem",
    "56": "Legendary Gem",
    "57": "Hunting Gem",
    "58": "Empowering Gem"
}

NAME_TO_ID = {v: k for k, v in GEM_IDS.items()}

GEM_EFFECTS = {
    "Common Gem": {"type": "rarity", "value": "Common"},
    "Rare Gem": {"type": "rarity", "value": "Rare"},
    "Mythic Gem": {"type": "rarity", "value": "Mythic"},
    "Legendary Gem": {"type": "rarity", "value": "Legendary"},
    "Hunting Gem": {"type": "hunting", "value": 2}, 
    "Empowering Gem": {"type": "empower", "value": 2}
}

# ================= 🎲 LOOTBOX DROP RATES =================
GEM_DROPS = list(GEM_IDS.values())
# Very low chance for Legendary and Special Gems (Hunting/Empowering)
DROP_WEIGHTS = [50, 25, 12, 6, 4, 1, 1, 1] 

class HuntSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= 🎒 INVENTORY COMMAND =================
    @commands.hybrid_command(name="inventory", aliases=["inv"], description="🎒 Check your inventory")
    async def inventory(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        uid = str(target.id)
        col = Database.get_collection("inventory")
        data = col.find_one({"_id": uid}) or {}
        
        lootbox_count = data.get("inventory", {}).get("lootbox", 0) 
        items = data.get("items", {})

        if not items and lootbox_count == 0:
            return await ctx.send(f"🎒 **{target.name}**'s inventory is empty!")

        description = ""
        if lootbox_count > 0:
            description += f"🎁 **Lootbox**: {lootbox_count}\n"
        
        gem_text = ""
        for name, count in items.items():
            if count <= 0 or name not in NAME_TO_ID: continue
            gem_id = NAME_TO_ID.get(name)
            gem_text += f"`{gem_id}` **{name}**: {count}\n"
        
        if gem_text: 
            description += "\n**💎 Gems**\n" + gem_text

        embed = discord.Embed(
            title=f"🎒 Inventory of {target.name}", 
            description=description if description else "Empty", 
            color=get_theme_color(ctx.guild.id)
        )
        embed.set_footer(text="Use gems with: /use [id] | Open boxes with: /lb")
        await ctx.send(embed=embed)

    # ================= 🎁 OPEN LOOTBOX COMMAND =================
    @commands.hybrid_command(name="lootbox", aliases=["lb", "open"], description="🎁 Open lootboxes to get gems")
    async def lootbox(self, ctx: commands.Context, amount: str = "1"):
        uid = str(ctx.author.id)
        col = Database.get_collection("inventory")
        data = col.find_one({"_id": uid}) or {}
        
        current_lb = data.get("inventory", {}).get("lootbox", 0)

        if current_lb < 1: 
            return await ctx.send("❌ You don't have any **Lootboxes**!")

        if amount.lower() == "all": 
            open_count = current_lb
        elif amount.isdigit(): 
            open_count = min(int(amount), current_lb)
        else: 
            open_count = 1

        rewards = random.choices(GEM_DROPS, weights=DROP_WEIGHTS, k=open_count)
        counts = Counter(rewards)

        # Update database: decrease lootbox, increase gems
        update = {"$inc": {"inventory.lootbox": -open_count}}
        for gem, qty in counts.items():
            update["$inc"][f"items.{gem}"] = qty
        
        col.update_one({"_id": uid}, update, upsert=True)

        res = f"🎁 You opened **{open_count}** Lootbox(es) and found:\n"
        for gem, qty in counts.items():
            res += f"💎 **{gem}**: `x{qty}`\n"
        
        await ctx.send(embed=discord.Embed(description=res, color=discord.Color.gold()))

    # ================= 🏹 HUNT COMMAND =================
    @commands.hybrid_command(name="hunt", aliases=["h"], description="🐾 Hunt for animals")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def hunt(self, ctx: commands.Context):
        uid = str(ctx.author.id)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        buffs = user_data.get("buffs", {})

        # Apply Gem Buffs
        chosen_rarity = buffs.get("rarity") if buffs.get("rarity") else random.choices(RARITIES, weights=HUNT_WEIGHTS, k=1)[0]
        base_qty = 1 + random.randint(1, 2) if buffs.get("hunting") else 1
        final_qty = base_qty * 2 if buffs.get("empower") else base_qty

        caught = Counter([random.choice(ANIMALS[chosen_rarity]) for _ in range(final_qty)])
        lb_drop = 1 if random.random() < 0.05 else 0 

        # Database update
        upd = {"$unset": {"buffs": ""}, "$set": {"last_hunt": datetime.datetime.now(datetime.timezone.utc).isoformat()}, "$inc": {}}
        for animal, qty in caught.items(): 
            upd["$inc"][f"zoo.{animal}"] = qty
        
        if lb_drop: 
            upd["$inc"]["inventory.lootbox"] = lb_drop
        
        # XP logic
        battle_team = user_data.get("team", [])
        xp = (20 * final_qty) if battle_team else 0
        if xp: upd["$inc"]["xp"] = xp

        col.update_one({"_id": uid}, upd, upsert=True)

        res = f"🌿 You caught **{final_qty}** animals: " + ", ".join([f"**{a}** x{q}" for a, q in caught.items()])
        if lb_drop: res += f"\n🎁 You found a **Lootbox**!"
        
        embed = discord.Embed(description=res, color=get_theme_color(ctx.guild.id))
        embed.set_author(name=f"{ctx.author.name}'s Hunt", icon_url=ctx.author.display_avatar.url)
        embed.add_field(name="Rarity", value=f"{RANK_EMOJIS[chosen_rarity]} {chosen_rarity}")
        if xp: embed.add_field(name="XP", value=f"✨ +{xp} XP")
        await ctx.send(embed=embed)

    # ================= 💎 USE COMMAND =================
    @commands.hybrid_command(name="use", description="🔮 Use a gem for your next hunt")
    async def use(self, ctx: commands.Context, item_id: str):
        uid = str(ctx.author.id)
        
        # Check if ID is valid
        gem_name = GEM_IDS.get(item_id)
        if not gem_name:
            return await ctx.send("❌ Invalid Gem ID! Check your inventory for correct IDs.")
        
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        
        if user_data.get("items", {}).get(gem_name, 0) < 1:
            return await ctx.send(f"❌ You don't have any **{gem_name}**!")
        
        buff = GEM_EFFECTS.get(gem_name)
        if not buff:
            return await ctx.send("❌ This gem cannot be used currently.")

        # Consume gem and apply buff
        col.update_one(
            {"_id": uid}, 
            {"$inc": {f"items.{gem_name}": -1}, "$set": {f"buffs.{buff['type']}": buff['value']}}, 
            upsert=True
        )
        await ctx.send(f"🔮 **{gem_name}** activated! It will take effect on your next hunt.")

    # ================= 💰 SELL & ZOO (Simplified) =================
    @commands.hybrid_command(name="sell", description="💰 Sell animals for coins")
    async def sell(self, ctx: commands.Context, query: str):
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

    @commands.hybrid_command(name="zoo", aliases=["z"], description="🦁 View your animals")
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
        embed = discord.Embed(title=f"🦁 Zoo of {target.name}", description=desc, color=get_theme_color(ctx.guild.id))
        embed.set_footer(text=f"Total Animals: {total}")
        await ctx.send(embed=embed)

    @hunt.error
    async def hunt_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Please wait `{error.retry_after:.1f}` seconds.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(HuntSystem(bot))
        
