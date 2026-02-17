import pymongo
from pymongo import MongoClient
import os

# 👇 সরাসরি লিংক না দিয়ে আমরা রেন্ডার থেকে ভেরিয়েবল নিচ্ছি
MONGO_URL = os.getenv("MONGO_URL")

# যদি লিংক না পায়, তবে এরর দিবে (ডিবাগিং এর জন্য)
if not MONGO_URL:
    print("❌ Error: MONGO_URL not found in Environment Variables!")
else:
    print("✅ Connected to MongoDB!")

# ডাটাবেস কানেকশন
cluster = MongoClient(MONGO_URL)
db = cluster["DiscordBotDB"]

# কালেকশন
economy_col = db["economy"]
premium_col = db["premium"]
config_col = db["config"]

class Database:
    # ... বাকি কোড যেমন ছিল তেমনই থাকবে (get_economy, update_balance ইত্যাদি) ...
    # (আগের দেওয়া কোডটিই এখানে থাকবে)
    
    @staticmethod
    def get_economy():
        data = economy_col.find_one({"_id": "main_economy"})
        if not data:
            new_data = {"_id": "main_economy", "users": {}}
            economy_col.insert_one(new_data)
            return {}
        return data.get("users", {})

    @staticmethod
    def update_balance(user_id, amount):
        uid = str(user_id)
        economy_col.update_one(
            {"_id": "main_economy"},
            {"$inc": {f"users.{uid}": amount}},
            upsert=True
        )
        data = economy_col.find_one({"_id": "main_economy"})
        return data["users"].get(uid, 0)

    @staticmethod
    def get_balance(user_id):
        data = economy_col.find_one({"_id": "main_economy"})
        if data and "users" in data:
            return data["users"].get(str(user_id), 0)
        return 0

    @staticmethod
    def get_premium_data():
        data = premium_col.find_one({"_id": "main_premium"})
        if not data:
            return {"users": {}, "servers": {}}
        return data

    @staticmethod
    def save_premium_data(data):
        premium_col.replace_one({"_id": "main_premium"}, data, upsert=True)

    @staticmethod
    def get_config():
        data = config_col.find_one({"_id": "main_config"})
        if not data:
            return {}
        return data

    @staticmethod
    def save_config(data):
        config_col.replace_one({"_id": "main_config"}, data, upsert=True)
      
