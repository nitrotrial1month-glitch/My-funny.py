import discord
from discord.ext import commands
from discord import app_commands
import random
from database import Database
from utils import get_theme_color

# ================= 🐾 CONFIGURATION =================
ANIMALS = {
    "Common": ["🐛 Worm", "🐜 Ant", "🪳 Roach", "🦟 Fly"],
    "Uncommon": ["🐭 Mouse", "🐸 Frog", "🐍 Snake", "🦇 Bat"],
    "Rare": ["🐺 Wolf", "🦊 Fox", "🐻 Bear", "🐼 Panda"],
    "Epic": ["🦁 Lion", "🐯 Tiger", "🦈 Shark", "🐊 Croc"],
    "Mythic": ["🐉 Dragon", "🦄 Unicorn", "🦅 Griffin", "🦕 Dino"],
    "Legendary": ["👹 Demon", "👼 Angel", "👽 Alien", "👾 Glitch"],
    "Special": ["💎 Gem-A", "🔮 Star-A"]
}

PRICES = {
    "Common": 10, "Uncommon": 25, "Rare": 75, 
    "Epic": 250, "Mythic": 1200, "Legendary": 6000, "Special": 25000
}

RARITIES = list(ANIMALS.keys())
WEIGHTS = [50, 25, 12, 7, 4, 1.5, 0.5]

GEMS_CONFIG = {
    "50": {"name": "Common Gem", "type": "luck", "boost": "Common", "dura": 5},
    "51": {"name": "Uncommon Gem", "type": "luck", "boost": "Uncommon", "dura": 5},
    "52": {"name": "Rare Gem", "type": "luck", "boost": "Rare", "dura": 5},
    "53": {"name": "Hunting Gem", "type": "qty", "boost": 2, "dura": 3},
    "54": {"name": "Lucky Gem", "type": "luck_all", "boost": 2.2, "dura": 5}
}

class OwOFinalSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= 🏹 HUNT (h) =================
    @commands.hybrid_command(name="hunt", aliases=["h"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def hunt(self, ctx):
        uid = str(ctx.author.id)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        
        active_buffs = user_data.get("active_buffs", {})
        final_weights = WEIGHTS.copy()
        count = 1
        buff_status = []

        if active_buffs:
            for gid, info in list(active_buffs.items()):
                if info['type'] == "luck_all":
                    final_weights = [w * info['boost'] for w in final_weights]
                elif info['type'] == "luck":
                    idx = RARITIES.index(info['boost'])
                    final_weights[idx] *= 4 
                elif info['type'] == "qty":
                    count += random.randint(1, info['boost'])
                
                info['dura'] -= 1
                if info['dura'] <= 0:
                    del active_buffs[gid]
                    buff_status.append(f"🚫 **{info['name']}** broke!")
                else:
                    buff_status.append(f"✨ **{info['name']}** ({info['dura']} left)")

        caught = [random.choice(ANIMALS[random.choices(RARITIES, weights=final_weights, k=1)[0]]) for _ in range(count)]
        
        inc_dict = {f"zoo.{a}": 1 for a in caught}
        col.update_one({"_id": uid}, {"$inc": inc_dict, "$set": {"active_buffs": active_buffs}}, upsert=True)

        res = " ".join([f"**{a}**" for a in caught])
        embed = discord.Embed(
            description=f"🌿 **{ctx.author.display_name}** | Found: {res}\n{chr(10).join(buff_status)}",
            color=get_theme_color(ctx.guild.id)
        )
        await ctx.send(embed=embed)

    # ================= 🦁 ZOO (z) =================
    @commands.hybrid_command(name="zoo", aliases=["z"])
    async def zoo(self, ctx, member: discord.Member = None):
        user = member or ctx.author
        uid = str(user.id)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        zoo = user_data.get("zoo", {})

        if not zoo: return await ctx.send(f"❌ **{user.display_name}** has no animals!")

        embed = discord.Embed(title=f"🐾 {user.display_name}'s Zoo", color=get_theme_color(ctx.guild.id))
        for rarity in RARITIES:
            owned = [f"{a} x{zoo[a]}" for a in ANIMALS[rarity] if a in zoo]
            if owned: embed.add_field(name=f"--- {rarity} ---", value=" | ".join(owned), inline=False)
        await ctx.send(embed=embed)

    # ================= 💰 SELL (s) =================
    @commands.hybrid_command(name="sell", aliases=["s"])
    async def sell(self, ctx, query: str):
        uid = str(ctx.author.id)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        zoo = user_data.get("zoo", {})
        
        total_gain, unset_list, q = 0, {}, query.lower()
        for rarity in RARITIES:
            if q == "all" or q == rarity.lower():
                for animal in ANIMALS[rarity]:
                    if animal in zoo:
                        total_gain += PRICES[rarity] * zoo[animal]
                        unset_list[f"zoo.{animal}"] = ""

        if total_gain == 0: return await ctx.send("❌ Nothing to sell!")
        col.update_one({"_id": uid}, {"$unset": unset_list})
        Database.update_balance(uid, total_gain)
        await ctx.send(f"💰 **{ctx.author.display_name}** | Sold for **{total_gain}** coins!")

    # ================= 🎒 INVENTORY (inv) =================
    @commands.hybrid_command(name="inventory", aliases=["inv"])
    async def inventory(self, ctx):
        uid = str(ctx.author.id)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        items = user_data.get("items", {})

        content = f"📦 **Lootbox**: {items.get('Lootbox', 0)}\n\n"
        for gid, info in GEMS_CONFIG.items():
            count = items.get(info['name'], 0)
            if count > 0: content += f"💎 **{info['name']}** (ID: `{gid}`): {count}\n"
        
        embed = discord.Embed(title=f"🎒 {ctx.author.display_name}'s Inventory", description=content or "*Empty*", color=discord.Color.blue())
        await ctx.send(embed=embed)

    # ================= 💎 USE =================
    @commands.hybrid_command(name="use")
    async def use(self, ctx, gem_id: str):
        uid = str(ctx.author.id)
        gem = GEMS_CONFIG.get(gem_id)
        if not gem: return await ctx.send("❌ Use ID 50-54")

        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        if user_data.get("items", {}).get(gem['name'], 0) < 1:
            return await ctx.send(f"❌ No **{gem['name']}**!")

        active = user_data.get("active_buffs", {})
        active[gem_id] = gem.copy()
        col.update_one({"_id": uid}, {"$inc": {f"items.{gem['name']}": -1}, "$set": {"active_buffs": active}})
        await ctx.send(f"💎 **{ctx.author.display_name}** | Used **{gem['name']}**!")

    # ================= 📦 OPEN (op lb) =================
    @commands.hybrid_command(name="open", aliases=["op", "lb"])
    async def open_box(self, ctx, sub: str = None, amount: str = "1"):
        if sub and sub.lower() != "lb": amount = sub # handle 'op 10'
        
        uid = str(ctx.author.id)
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid}) or {}
        total_lb = user_data.get("items", {}).get("Lootbox", 0)

        if total_lb < 1: return await ctx.send("❌ No Lootboxes!")

        # Amount নির্ধারণ
        if amount.lower() == "all": amt = total_lb
        else: amt = min(int(amount), total_lb) if amount.isdigit() else 1

        rewards = {"animals": {}, "gems": {}}
        for _ in range(amt):
            if random.random() < 0.7:
                a = random.choice(ANIMALS[random.choices(RARITIES, weights=WEIGHTS, k=1)[0]])
                rewards["animals"][a] = rewards["animals"].get(a, 0) + 1
            else:
                g = random.choice(list(GEMS_CONFIG.keys()))
                rewards["gems"][g] = rewards["gems"].get(g, 0) + 1

        # DB Update
        upd = {"$inc": {"items.Lootbox": -amt}}
        for a, c in rewards["animals"].items(): upd["$inc"][f"zoo.{a}"] = c
        for g, c in rewards["gems"].items(): upd["$inc"][f"items.{GEMS_CONFIG[g]['name']}"] = c
        col.update_one({"_id": uid}, upd)

        # Result String
        res_list = [f"{a} x{c}" for a in rewards["animals"].items()] + [f"{GEMS_CONFIG[g]['name']} x{c}" for g, c in rewards["gems"].items()]
        embed = discord.Embed(description=f"🎁 **{ctx.author.display_name}** opened {amt} boxes:\n" + ", ".join(res_list), color=discord.Color.gold())
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(OwOFinalSystem(bot))
        
