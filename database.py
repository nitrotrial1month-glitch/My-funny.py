import os
import pymongo
from pymongo import MongoClient
import certifi
from datetime import datetime, timedelta

MONGO_URL = os.getenv("MONGO_URL")
ca = certifi.where()

if not MONGO_URL:
    print("Error: MONGO_URL not found!")
    cluster = None
    db = None
else:
    try:
        cluster = MongoClient(MONGO_URL, tlsCAFile=ca)
        db = cluster["DiscordBotDB"]
        print("Connected to MongoDB successfully!")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        cluster = None
        db = None

class Database:
    @staticmethod
    def get_collection(name):
        if db is not None:
            return db[name]
        return None

    # ================= E-COMMERCE ROLES SYNC =================
    @staticmethod
    def update_website_roles(user_id: str, username: str, is_seller: bool, is_owner: bool):
        col = Database.get_collection("users")
        if col is None: return
        col.update_one(
            {"discord_id": str(user_id)},
            {"$set": {
                "username": username, 
                "seller_access": is_seller,
                "owner_access": is_owner
            }},
            upsert=True
        )

    @staticmethod
    def get_all_users():
        try:
            col = Database.get_collection("users")
            return list(col.find({}))
        except:
            return []

    @staticmethod
    def toggle_user_seller_access(discord_id):
        try:
            col = Database.get_collection("users")
            user = col.find_one({"discord_id": str(discord_id)})
            if user:
                new_status = not user.get("seller_access", False)
                col.update_one({"discord_id": str(discord_id)}, {"$set": {"seller_access": new_status}})
        except Exception as e:
            print(f"Error toggling seller: {e}")

    # ================= ECONOMY SYNC =================
    @staticmethod
    def update_balance(user_id, amount):
        col = Database.get_collection("inventory")
        if col is None: return 0
        uid = str(user_id)
        col.update_one({"_id": uid}, {"$inc": {"balance": amount}}, upsert=True)
        return col.find_one({"_id": uid}).get("balance", 0)

    @staticmethod
    def get_balance(user_id):
        col = Database.get_collection("inventory")
        if col is None: return 0
        data = col.find_one({"_id": str(user_id)})
        return data.get("balance", 0) if data else 0

    # ================= PREMIUM & CONFIG =================
    @staticmethod
    def add_premium(target_id, p_type, duration_days):
        col = Database.get_collection("premium")
        if col is None: return
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
    def get_config():
        col = Database.get_collection("config")
        if col is None: return {"prefix": "Nova", "status": "Online"}
        data = col.find_one({"_id": "main_config"})
        return data if data else {"prefix": "Nova", "status": "Online"}

    @staticmethod
    def save_config(data):
        col = Database.get_collection("config")
        if col is None: return
        # ডাটা সেভ করার সময় id ঠিক রেখে আপডেট করা
        data["_id"] = "main_config"
        col.replace_one({"_id": "main_config"}, data, upsert=True)
           
    # ================= 👕 E-COMMERCE PRODUCTS SYNC =================
    @staticmethod
    def get_all_products():
        col = Database.get_collection("products")
        return list(col.find({})) if col is not None else []

    @staticmethod
    def add_product(name, desc, price, image):
        col = Database.get_collection("products")
        if col is None: return
        product_data = {
            "name": name,
            "description": desc,
            "price": int(price) if price else 0,
            "image": image
        }
        col.insert_one(product_data)
        print(f"🛍️ Product added: {name}")

    @staticmethod
    def add_dummy_products():
        col = Database.get_collection("products")
        if col is None: return
        if col.count_documents({}) == 0:
            dummy_products = [
                {"name": "Classic Red Essential", "description": "100% Cotton", "price": 450, "image": "..."}
            ]
            col.insert_many(dummy_products)
            
