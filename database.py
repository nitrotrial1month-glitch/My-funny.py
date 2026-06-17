import os
import pymongo
from pymongo import MongoClient
import certifi

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
        """Grants Seller or Owner access on the website based on Discord roles"""
        col = Database.get_collection("users")
        if col is None: 
            return
        
        col.update_one(
            {"discord_id": str(user_id)},
            {"$set": {
                "username": username, 
                "seller_access": is_seller,
                "owner_access": is_owner
            }},
            upsert=True
        )

    # ================= ECONOMY SYNC =================
    
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

    # ================= PREMIUM & CONFIG =================

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
           
    # ================= 👕 E-COMMERCE PRODUCTS SYNC =================
    
    @staticmethod
    def get_all_products():
        col = Database.get_collection("products")
        if col is None: 
            return []
        return list(col.find({}))
        
        @staticmethod
    def add_product(name, desc, price, image):
        """ডাটাবেসে নতুন প্রোডাক্ট যোগ করার জন্য"""
        col = Database.get_collection("products")
        if col is None: 
            return
        
        product_data = {
            "name": name,
            "description": desc,
            "price": int(price) if price else 0, # price কে সংখ্যায় রূপান্তর করছে
            "image": image
        }
        col.insert_one(product_data)
        print(f"🛍️ Product added: {name}")
        
    @staticmethod
    def add_dummy_products():
        col = Database.get_collection("products")
        if col is None: 
            return
            
        if col.count_documents({}) == 0:
            dummy_products = [
                {
                    "name": "Classic Red Essential", 
                    "description": "100% Cotton, Comfort Fit", 
                    "price": 450, 
                    "image": "https://via.placeholder.com/260x300/cc0000/ffffff?text=Inwear+T-Shirt"
                },
                {
                    "name": "White Graphic Tee", 
                    "description": "Premium Print, Oversized", 
                    "price": 550, 
                    "image": "https://via.placeholder.com/260x300/ffffff/cc0000?text=White+Graphic+Tee"
                },
                {
                    "name": "Black Anime Edition", 
                    "description": "Limited Edition, Glow in dark", 
                    "price": 600, 
                    "image": "https://via.placeholder.com/260x300/1a1a1a/ffffff?text=Black+Anime+Print"
                }
            ]
            col.insert_many(dummy_products)
            print("🛍️ Dummy products added to the database!")
            
