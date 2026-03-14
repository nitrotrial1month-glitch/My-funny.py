import os
import pymongo
from pymongo import MongoClient
import certifi
from dotenv import load_dotenv # .env ফাইল রিড করার জন্য যোগ করা হয়েছে

# ১. .env থেকে ভেরিয়েবল লোড করা
load_dotenv()

# ২. Environment থেকে URL নেওয়া
MONGO_URL = os.getenv("MONGO_URL")

# সার্টিফিকেট লোড করা (SSL সংযোগের জন্য বাধ্যতামূলক)
ca = certifi.where()

if not MONGO_URL:
    print("❌ Error: MONGO_URL not found in .env file!")
    cluster = None
    db = None
else:
    try:
        # tlsCAFile=ca অংশটি ডাটাbeস সংযোগ নিশ্চিত করে
        cluster = MongoClient(MONGO_URL, tlsCAFile=ca)
        db = cluster["DiscordBotDB"]
        print("✅ Connected to MongoDB successfully!")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        cluster = None
        db = None

class Database:
    @staticmethod
    def get_collection(name):
        """ডাটাবেস কালেকশন রিটার্ন করে"""
        if db is not None:
            return db[name]
        return None

    # ================= 💰 ECONOMY SYNC =================
    
    @staticmethod
    def update_balance(user_id, amount):
        col = Database.get_collection("inventory")
        if col is None: return 0
        
        uid = str(user_id)
        col.update_one(
            {"_id": uid},
            {"$inc": {"balance": amount}},
            upsert=True
        )
        data = col.find_one({"_id": uid})
        return data.get("balance", 0)

    @staticmethod
    def get_balance(user_id):
        col = Database.get_collection("inventory")
        if col is None: return 0
        uid = str(user_id)
        data = col.find_one({"_id": uid})
        if data:
            return data.get("balance", 0)
        return 0

    # ================= 💎 PREMIUM & CONFIG =================

    @staticmethod
    def add_premium(target_id, p_type, duration_days):
        col = Database.get_collection("premium")
        if col is None: return
        from datetime import datetime, timedelta
        expire_date = datetime.now() + timedelta(days=duration_days)
        category = "users" if p_type.lower() == "user" else "servers"
        col.update_one(
            {"_id": "main_premium"},
            {"$set": {f"{category}.{str(target_id)}": {
                "plan": "premium", 
                "start_at": datetime.now().isoformat(), 
                "expire_at": expire_date.isoformat()
            }}},
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
        
