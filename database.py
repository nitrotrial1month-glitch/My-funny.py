import os
import pymongo
from pymongo import MongoClient
import certifi  # <--- এটি ইমপোর্ট করতে হবে

# Render এর Environment থেকে URL নেওয়া
MONGO_URL = os.getenv("MONGO_URL")

# সার্টিফিকেট লোড করা
ca = certifi.where()

if not MONGO_URL:
    print("❌ Error: MONGO_URL not found!")
    cluster = None
    db = None
else:
    try:
        # 👇 tlsCAFile=ca এই অংশটি যোগ করা বাধ্যতামূলক
        cluster = MongoClient(MONGO_URL, tlsCAFile=ca)
        db = cluster["DiscordBotDB"]
        print("✅ Connected to MongoDB successfully!")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        cluster = None
        db = None

# ... বাকি কোড (Class Database) আগের মতোই থাকবে ...
# ... (নিচে আপনার আগের update_balance বা অন্যান্য ফাংশনগুলো থাকবে)
class Database:
    @staticmethod
    def get_collection(name):
        if db is not None:
            return db[name]
        return None

    @staticmethod
    def update_balance(user_id, amount):
        col = Database.get_collection("economy")
        if col is None: return 0
        
        uid = str(user_id)
        col.update_one(
            {"_id": "main_economy"},
            {"$inc": {f"users.{uid}": amount}},
            upsert=True
        )
        data = col.find_one({"_id": "main_economy"})
        return data["users"].get(uid, 0)
    
    # ... অন্যান্য ফাংশন (get_balance, add_premium, etc.)
    @staticmethod
    def get_balance(user_id):
        col = Database.get_collection("economy")
        if col is None: return 0
        data = col.find_one({"_id": "main_economy"})
        if data and "users" in data:
            return data["users"].get(str(user_id), 0)
        return 0

    @staticmethod
    def add_premium(target_id, p_type, duration_days):
        col = Database.get_collection("premium")
        if col is None: return
        from datetime import datetime, timedelta
        expire_date = datetime.now() + timedelta(days=duration_days)
        category = "users" if p_type == "User" else "servers"
        col.update_one(
            {"_id": "main_premium"},
            {"$set": {f"{category}.{target_id}": {"plan": "premium", "start_at": datetime.now().isoformat(), "expire_at": expire_date.isoformat()}}},
            upsert=True
        )

    @staticmethod
    def get_premium_data():
        col = Database.get_collection("premium")
        if col is None: return {"users": {}, "servers": {}}
        data = col.find_one({"_id": "main_premium"})
        return data if data else {"users": {}, "servers": {}}

    @staticmethod
    def get_config():
        col = Database.get_collection("config")
        if col is None: return {}
        data = col.find_one({"_id": "main_config"})
        return data if data else {}

    @staticmethod
    def save_config(data):
        col = Database.get_collection("config")
        if col is None: return
        col.replace_one({"_id": "main_config"}, data, upsert=True)
        
