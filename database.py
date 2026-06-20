import os
import pymongo
from pymongo import MongoClient
import certifi
from datetime import datetime, timedelta
import requests
from bson import ObjectId

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
    def get_premium_data():
        col = Database.get_collection("premium")
        if col is None: return {"users": {}, "servers": {}}
        data = col.find_one({"_id": "main_premium"})
        return data if data else {"users": {}, "servers": {}}

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
        data["_id"] = "main_config"
        col.replace_one({"_id": "main_config"}, data, upsert=True)
           
    # ================= 👕 E-COMMERCE PRODUCTS SYNC =================
    @staticmethod
    def get_all_products():
        col = Database.get_collection("products")
        return list(col.find({})) if col is not None else []

    @staticmethod
    def add_product(name, desc, price, image, is_owner=False, seller_id=None):
        col = Database.get_collection("products")
        if col is None: return
        
        status = "Approved" if is_owner else "Pending"
        
        product_data = {
            "name": name,
            "description": desc,
            "price": int(price) if price else 0,
            "image": image,
            "status": status
        }
        
        result = col.insert_one(product_data)
        product_id = str(result.inserted_id)
        
        if is_owner:
            print(f"🛍️ Owner uploaded a product. Auto-approved: {name}")
            return
            
        webhook_url = "https://discord.com/api/webhooks/1517038233559633980/ynh7QyKkWQXbiey9js7iWs27v0k2lW4En7Sna2TKwz4ZkXwED_aBKSPSp_e7CMPtYu-a"
        
        if webhook_url:
            embed = {
                "title": "🟡 New Product Pending Verification",
                "description": f"**Product:** {name}\n**Price:** {price}₹\n\n*Seller: Please **REPLY** to this message with a short video of the product.*\n*Owner: React with ✅ or ❌ on this message to verify.*",
                "color": 16753920,
                "footer": {"text": f"ID: {product_id}"}
            }
            
            payload = {"embeds": [embed]}
            if seller_id:
                payload["content"] = f"🔔 <@{seller_id}> Your product is waiting for verification!"

            try:
                import requests
                requests.post(webhook_url, json=payload)
            except Exception as e:
                print(f"Webhook Exception Error: {e}")

    @staticmethod
    def approve_product(product_id):
        try:
            col = Database.get_collection("products")
            if col is not None:
                col.update_one({"_id": ObjectId(product_id)}, {"$set": {"status": "Approved"}})
        except Exception as e:
            print(f"Error approving product: {e}")

    @staticmethod
    def delete_product(product_id):
        try:
            col = Database.get_collection("products")
            if col is not None:
                col.delete_one({"_id": ObjectId(product_id)})
        except Exception as e:
            print(f"Error deleting product: {e}")

    @staticmethod
    def add_dummy_products():
        col = Database.get_collection("products")
        if col is None: return
        if col.count_documents({}) == 0:
            dummy_products = [
                {"name": "Classic Red Essential", "description": "100% Cotton", "price": 450, "image": "...", "status": "Approved"}
            ]
            col.insert_many(dummy_products)
            
    # ================= 🛒 CART SYSTEM =================
    @staticmethod
    def get_user_cart(user_id):
        col = Database.get_collection("cart")
        if col is None: return []
        cart = col.find_one({"user_id": str(user_id)})
        if cart:
            product_ids = [ObjectId(pid) for pid in cart.get("items", [])]
            products_col = Database.get_collection("products")
            return list(products_col.find({"_id": {"$in": product_ids}}))
        return []

    @staticmethod
    def add_to_cart(user_id, product_id):
        col = Database.get_collection("cart")
        if col is None: return
        col.update_one(
            {"user_id": str(user_id)},
            {"$addToSet": {"items": str(product_id)}},
            upsert=True
        )

    @staticmethod
    def remove_from_cart(user_id, product_id):
        col = Database.get_collection("cart")
        if col is None: return
        col.update_one(
            {"user_id": str(user_id)},
            {"$pull": {"items": str(product_id)}}
        )

    @staticmethod
    def get_user_orders(user_id):
        col = Database.get_collection("orders")
        return list(col.find({"user_id": str(user_id)}).sort("date", -1))
        
    @staticmethod
    def get_products_by_seller(seller_id):
        col = Database.get_collection("products")
        return list(col.find({"seller_id": seller_id}))
    
    @staticmethod
    def update_product(product_id, updated_data):
        col = Database.get_collection("products")
        if col is not None:
            col.update_one({"_id": ObjectId(product_id)}, {"$set": updated_data})
            
        @staticmethod
    def add_product_from_dict(data):
        col = Database.get_collection("products")
        if col is not None:
            result = col.insert_one(data)
            return result.inserted_id  # 🔴 এই লাইনটি যোগ করা হলো
        return None
          
    # ================= 📦 ORDER SYSTEM UPDATE =================
    @staticmethod
    def place_order(user_id, items, total_price, name, address, phone, payment_method, clear_cart=False, status="Pending"):
        col = Database.get_collection("orders")
        
        serialized_items = []
        for item in items:
            item_copy = item.copy()
            if '_id' in item_copy:
                item_copy['_id'] = str(item_copy['_id'])
            serialized_items.append(item_copy)
            
        # অর্ডার প্লেস করার দিন থেকে ৫ দিন পরের তারিখ হিসাব করা
        expected_date = (datetime.now() + timedelta(days=5)).strftime("%d %B, %Y")
        
        order_data = {
            "user_id": str(user_id),
            "items": serialized_items,
            "total": total_price,
            "name": name,
            "address": address,
            "phone": phone,
            "payment_method": payment_method,
            "status": status,
            "order_date": datetime.now().strftime("%d %B, %Y"),
            "expected_delivery": expected_date
        }
        result = col.insert_one(order_data)
        
        if clear_cart:
            Database.get_collection("cart").delete_one({"user_id": str(user_id)})
            
        return str(result.inserted_id), expected_date

    @staticmethod
    def get_order_by_id(order_id):
        col = Database.get_collection("orders")
        return col.find_one({"_id": ObjectId(order_id)}) if col is not None else None

    @staticmethod
    def update_order_status(order_id, new_status):
        col = Database.get_collection("orders")
        if col is not None:
            col.update_one({"_id": ObjectId(order_id)}, {"$set": {"status": new_status}})

    @staticmethod
    def get_user_addresses(user_id):
        col = Database.get_collection("saved_addresses")
        if col is None: return []
        return list(col.find({"user_id": str(user_id)}))
        
    @staticmethod
    def save_user_address(user_id, name, phone, address):
        col = Database.get_collection("saved_addresses")
        if col is not None:
            # চেক করবে একই অ্যাড্রেস আগে থেকে সেভ করা আছে কি না
            existing = col.find_one({"user_id": str(user_id), "address": address})
            if not existing:
                col.insert_one({
                    "user_id": str(user_id),
                    "name": name,
                    "phone": phone,
                    "address": address
                })
                
