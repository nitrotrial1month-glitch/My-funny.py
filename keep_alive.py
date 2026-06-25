import os
import importlib
from flask import Flask, render_template, session, Blueprint
from threading import Thread
from database import Database

# 🔴 ১. সিকিউরিটি ফাংশনগুলো ইমপোর্ট করা হলো
from security import init_request_filter, init_security_headers

# আপনার আগের ফাইলগুলো (এগুলো যেমন আছে থাক)
from dashboard import dashboard_bp 
from google_auth import google_bp
from facebook_auth import facebook_bp
from apple_auth import apple_bp

app = Flask(__name__)
# 🔴 UPDATE: নতুন ব্র্যান্ডের নাম অনুযায়ী secret_key 
app.secret_key = "wearbyme_super_secret_key_2026"

# 🔴 ২. অ্যাপ তৈরি হওয়ার সাথে সাথেই সিকিউরিটি শিল্ড (বর্ম) অন করে দেওয়া হলো
init_request_filter(app)
init_security_headers(app)

# আগের ব্লুপ্রিন্টগুলো রেজিস্টার করা হলো
app.register_blueprint(google_bp)
app.register_blueprint(facebook_bp)
app.register_blueprint(apple_bp)
app.register_blueprint(dashboard_bp)

# ========================================================
# 🔴 MAGIC AUTO-LOADER (ডায়নামিক রুট লোডিং) 🔴
# ========================================================
ROUTES_FOLDER = "routes"

# এটি চেক করবে routes ফোল্ডার আছে কি না
if os.path.exists(ROUTES_FOLDER):
    # ফোল্ডারের ভেতরের সব ফাইল খুঁজবে
    for filename in os.listdir(ROUTES_FOLDER):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = filename[:-3]
            try:
                # ফাইলটিকে ডায়নামিকভাবে ইমপোর্ট করবে
                module = importlib.import_module(f"{ROUTES_FOLDER}.{module_name}")
                
                # ফাইলের ভেতর কোনো Blueprint থাকলে সেটিকে অটোমেটিক রেজিস্টার করে নেবে
                for item_name in dir(module):
                    item = getattr(module, item_name)
                    if isinstance(item, Blueprint):
                        app.register_blueprint(item)
                        print(f"✅ Auto-Loaded Route: {filename}")
            except Exception as e:
                print(f"❌ Error loading {filename}: {e}")
# ========================================================

# 🏠 মেইন হোমপেজ
@app.route('/')
def home():
    products = Database.get_all_products()
    user_data = session.get('user')
    return render_template('index.html', products=products, user=user_data)

def run():
    port = int(os.environ.get("PORT", 8080))
    # 🔴 UPDATE: প্রিন্ট স্টেটমেন্টে ব্র্যান্ডের নাম পরিবর্তন করা হলো
    print("--- 🚀 Wear By Me Server is Running ---")
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    server = Thread(target=run)
    server.start()
    
