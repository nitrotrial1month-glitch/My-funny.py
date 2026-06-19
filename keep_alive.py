import os
import traceback
from flask import Flask, render_template, redirect, url_for, session, request
from werkzeug.utils import secure_filename
from threading import Thread
import requests
from bson import ObjectId
from database import Database  
from dashboard import dashboard_bp 
from google_auth import google_bp
from facebook_auth import facebook_bp
from apple_auth import apple_bp

app = Flask(__name__)
app.secret_key = "inwear_super_secret_key_2026"

# আলাদা ফাইলগুলোকে ওয়েবসাইটের সাথে কানেক্ট করা হলো
app.register_blueprint(google_bp)
app.register_blueprint(facebook_bp)
app.register_blueprint(apple_bp)
app.register_blueprint(dashboard_bp)

# ⚠️ Discord OAuth2 Credentials
DISCORD_CLIENT_ID = "1431675966807343388"
DISCORD_CLIENT_SECRET = "AtCC606CiJo5BZwRdqHM-Qj6GQGAELo9"
DISCORD_REDIRECT_URI = "https://my-funny-py.onrender.com/discord/callback"

DISCORD_API_BASE_URL = "https://discord.com/api"
AUTHORIZATION_BASE_URL = f"{DISCORD_API_BASE_URL}/oauth2/authorize"
TOKEN_URL = f"{DISCORD_API_BASE_URL}/oauth2/token"

# --- Home Route ---
@app.route('/')
def home():
    products = Database.get_all_products()
    user_data = session.get('user')
    return render_template('index.html', products=products, user=user_data)

# --- Discord Login Routes ---
@app.route('/login/discord')
def login_discord():
    auth_url = f"{AUTHORIZATION_BASE_URL}?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify%20guilds"
    return redirect(auth_url)

@app.route('/discord/callback')
def discord_callback():
    code = request.args.get('code')
    if not code:
        return "Login failed! <a href='/'>Go Home</a>"

    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': DISCORD_REDIRECT_URI
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    token_response = requests.post(TOKEN_URL, data=data, headers=headers)
    token_json = token_response.json()
    
    if "access_token" not in token_json:
        return "Failed to get access token from Discord."

    access_token = token_json['access_token']
    user_response = requests.get(f"{DISCORD_API_BASE_URL}/users/@me", headers={'Authorization': f'Bearer {access_token}'})
    user_info = user_response.json()

    col = Database.get_collection("users")
    db_user = col.find_one({"discord_id": str(user_info.get('id'))}) if col is not None else None
    
    is_seller = db_user.get("seller_access", False) if db_user else False
    is_owner = db_user.get("owner_access", False) if db_user else False

    session['user'] = {
        'id': user_info.get('id'),
        'username': user_info.get('username'),
        'avatar': f"https://cdn.discordapp.com/avatars/{user_info.get('id')}/{user_info.get('avatar')}.png",
        'is_seller': is_seller,
        'is_owner': is_owner
    }

    return redirect(url_for('home'))

# --- Account & Logout Routes ---
@app.route('/account')
def account_page():
    try:
        user_data = session.get('user')
        if not user_data:
            return render_template('login.html')
        return render_template('account.html', user=user_data)
    except Exception as e:
        return f"<div style='padding:20px;'><h2 style='color:#cc0000;'>⚠️ Error</h2><p>{str(e)}</p></div>"

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

# --- Cart Routes ---
@app.route('/cart')
def cart():
    user = session.get('user')
    if not user:
        return redirect('/account')
    cart_items = Database.get_user_cart(user['id']) 
    total = sum(float(item['price']) for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total_price=total)

@app.route('/add_to_cart/<product_id>')
def add_to_cart(product_id):
    user = session.get('user')
    if user:
        Database.add_to_cart(user['id'], product_id)
    return redirect('/cart')

@app.route('/remove_from_cart/<product_id>')
def remove_from_cart(product_id):
    user = session.get('user')
    if user:
        Database.remove_from_cart(user['id'], product_id)
    return redirect('/cart')

# --- Order Routes ---
@app.route('/orders')
def orders():
    user = session.get('user')
    if not user:
        return redirect('/account')
    orders = Database.get_user_orders(user['id'])
    return render_template('orders.html', orders=orders)

@app.route('/checkout')
def checkout():
    user = session.get('user')
    if not user: return redirect('/account')
    cart_items = Database.get_user_cart(user['id'])
    total = sum(float(item['price']) for item in cart_items)
    Database.place_order(user['id'], cart_items, total)
    return redirect('/orders')

# --- Product Detail Route ---
@app.route('/product/<product_id>')
def product_details(product_id):
    col = Database.get_collection("products")
    product = col.find_one({"_id": ObjectId(product_id)})
    if not product:
        return "Product not found!", 404
        
    seller_products = []
    if 'seller_id' in product:
        seller_products = Database.get_products_by_seller(product['seller_id'])
        
    return render_template('product.html', product=product, seller_products=seller_products)
    
# --- Product Upload Route ---
@app.route('/seller/upload', methods=['POST'])
def upload_product():
    user = session.get('user')
    if not user: return redirect('/account')
    
    raw_orig = request.form.get('original_price', '0')
    raw_final = request.form.get('final_price', '0')
    
    original = float(raw_orig) if raw_orig and raw_orig.strip() != "" else 0.0
    final = float(raw_final) if raw_final and raw_final.strip() != "" else 0.0
    
    discount_percent = 0
    if original > 0 and final < original:
        discount_percent = ((original - final) / original) * 100
    
    file = request.files.get('image')
    image_path = ""
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join('static/uploads', filename))
        image_path = 'static/uploads/' + filename
    
    product_data = {
        "name": request.form.get('name'),
        "description": request.form.get('short_desc'),
        "full_details": request.form.get('full_details'),
        "sizes": [s.strip() for s in request.form.get('sizes', '').split(',')],
        "original_price": original,
        "price": final,
        "discount_percent": round(discount_percent),
        "image": image_path,
        "status": "Pending",
        "seller_id": str(user.get('id'))
    }
    
    Database.add_product_from_dict(product_data)
    return redirect('/seller')
    
# --- Server Setup ---
def run():
    port = int(os.environ.get("PORT", 8080))
    print("--- Registered Routes ---")
    for rule in app.url_map.iter_rules():
        print(f"Route: {rule.rule} -> Endpoint: {rule.endpoint}")
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    server = Thread(target=run)
    server.start()
    
