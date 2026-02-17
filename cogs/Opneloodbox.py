import discord
from discord.ext import commands
from discord import app_commands
import random
from collections import Counter
from database import Database
from utils import get_theme_color

# ================= 🆔 ITEM ID LIST =================
# OwO স্টাইল আইডি ম্যাপিং (আপনার Hunt ফাইলে যা আছে তার সাথে মিল রাখবেন)
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

# উল্টো ম্যাপিং (নাম থেকে আইডি বের করার জন্য)
NAME_TO_ID = {v: k for k, v in ITEM_IDS.items()}

# ================= 🎲 LOOTBOX DROP RATES =================
# লুটবক্স খুললে কোন জেম পাওয়ার সম্ভাবনা কতটুকু
GEM_DROPS = [
    "Common Gem", "Uncommon Gem", "Rare Gem", 
    "Epic Gem", "Mythic Gem", "Legendary Gem",
    "Hunting Gem", "Empowering Gem"
]

# ওজন (Weight) - কমন পাওয়ার চান্স বেশি, লিজেন্ডারি কম
DROP_WEIGHTS = [40, 25, 15, 10, 4, 1, 3, 2]

class InventorySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= 🎒 INVENTORY COMMAND =================
    @commands.hybrid_command(name="inventory", aliases=["inv", "bag"], description="🎒 Check your items and gems")
    async def inventory(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        uid = str(target.id)
        
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid})
        
        if not user_data or "items" not in user_data or not user_data["items"]:
            return await ctx.send(f"🎒 **{target.name}**'s inventory is empty!")

        items = user_data["items"]
        description = ""
        total_items = 0
        
        # আইটেমগুলো সাজানো
        # 1. Lootboxes
        if items.get("Lootbox", 0) > 0:
            description += f"`50` 🎁 **Lootbox**: {items['Lootbox']}\n"
            total_items += items['Lootbox']
        
        # 2. Gems
        description += "\n**💎 Gems**\n"
        for name, count in items.items():
            if name == "Lootbox": continue # লুটবক্স আগেই দেখিয়েছি
            if count > 0:
                iid = NAME_TO_ID.get(name, "??") # আইডি খুঁজে বের করা
                description += f"`{iid}` **{name}**: {count}\n"
                total_items += count

        embed = discord.Embed(
            title=f"🎒 Inventory of {target.name}",
            description=description,
            color=get_theme_color(ctx.guild.id)
        )
        embed.set_footer(text=f"Total Items: {total_items} • Use items with /use [id]")
        embed.set_thumbnail(url=target.display_avatar.url)
        
        await ctx.send(embed=embed)

    # ================= 🎁 OPEN LOOTBOX COMMAND =================
    @commands.hybrid_command(name="lootbox", aliases=["lb", "open"], description="🎁 Open lootboxes to get Gems!")
    @app_commands.describe(amount="How many to open? (number or 'all')")
    async def lootbox(self, ctx: commands.Context, amount: str = "1"):
        user = ctx.author
        uid = str(user.id)
        amount_str = amount.lower()
        
        col = Database.get_collection("inventory")
        user_data = col.find_one({"_id": uid})
        
        # ১. ব্যালেন্স চেক (Lootbox আছে কি না)
        current_boxes = user_data.get("items", {}).get("Lootbox", 0)
        
        if current_boxes < 1:
            return await ctx.send("❌ You don't have any **Lootboxes**! Use `/daily` or `/hunt` to find some.")

        # ২. কতগুলো খুলবে?
        if amount_str == "all":
            open_count = current_boxes
        elif amount_str.isdigit():
            open_count = int(amount_str)
            if open_count > current_boxes:
                return await ctx.send(f"❌ You only have **{current_boxes}** lootboxes!")
            if open_count < 1:
                return await ctx.send("❌ Minimum 1 lootbox required.")
        else:
            return await ctx.send("❌ Invalid amount! Use a number or 'all'.")

        # ৩. ওপেনিং লজিক (Simulate Opening)
        # একসাথে সবগুলোর রেজাল্ট বের করা (লুপ না চালিয়ে random.choices ব্যবহার করা ফাস্ট)
        rewards = random.choices(GEM_DROPS, weights=DROP_WEIGHTS, k=open_count)
        reward_counts = Counter(rewards) # কোনটা কয়টা পেয়েছে গুনে নেওয়া

        # ৪. ডাটাবেস আপডেট (Batch Update)
        update_query = {
            "$inc": {"items.Lootbox": -open_count} # লুটবক্স কমবে
        }
        
        # জেমগুলো যোগ করা
        for gem_name, qty in reward_counts.items():
            update_query["$inc"][f"items.{gem_name}"] = qty

        col.update_one({"_id": uid}, update_query)

        # ৫. রেজাল্ট এম্বেড
        # যদি ১টা খোলে
        if open_count == 1:
            gem_name = rewards[0]
            embed = discord.Embed(
                description=f"🎁 You opened a Lootbox and found:\n# 💎 **{gem_name}**",
                color=discord
      
