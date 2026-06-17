import os
import pymongo
from pymongo import MongoClient
import certifi

# Fetch URL from Render Environment Variables
MONGO_URL = os.getenv("MONGO_URL")

# Load certificate for secure SSL connection
ca = certifi.where()

if not MONGO_URL:
    print("Error: MONGO_URL not found!")
    cluster = None
    db = None
else:
    try:
        # tlsCAFile=ca ensures a secure connection to MongoDB Atlas
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
        """Returns the specified database collection"""
        if db is not None:
            return db[name]
        return None

    # ================= E-COMMERCE SELLER SYNC =================
    
    @staticmethod
    def set_seller_access(user_id: str, username: str, status: bool):
        """Grants or revokes seller access on the website based on Discord roles"""
        col = Database.get_collection("users")
        if col is None: 
            return
        
        # Updates the user's status in the database
        col.update_one(
            {"discord_id": str(user_id)},
            {"$set": {
                "username": username, 
                "seller_access": status
            }},
            upsert=True
        )

    # ================= ECONOMY SYNC =================
    
    @staticmethod
    def update_balance(user_id, amount):
        """Updates user balance for all economy commands"""
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
        """Reads the exact balance from the database"""
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
        """Adds a user or server to the premium list"""
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
        """Returns all premium data"""
        col = Database.get_collection("premium")
        if col is None: return {"users": {}, "servers": {}}
        data = col.find_one({"_id": "main_premium"})
        return data if data else {"users": {}, "servers": {}}

    @staticmethod
    def get_config():
        """Loads global configuration for the bot"""
        col = Database.get_collection("config")
        if col is None: return {}
        data = col.find_one({"_id": "main_config"})
        return data if data else {}

    @staticmethod
    def save_config(data):
        """Saves global configuration for the bot"""
        col = Database.get_collection("config")
        if col is None: return
        col.replace_one({"_id": "main_config"}, data, upsert=True)
           
    # ================= 👕 E-COMMERCE PRODUCTS SYNC =================
    
    @staticmethod
    def get_all_products():
        """Fetches all products from the MongoDB database"""
        col = Database.get_collection("products")
        if col is None: 
            return []
        return list(col.find({}))

    @staticmethod
    def add_dummy_products():
        """Temporary function to insert sample t-shirts for testing"""
        col = Database.get_collection("products")
        if col is None: 
            return
            
        # If there are no products, add these sample inwear t-shirts
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
            
