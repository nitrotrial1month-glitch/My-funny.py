import os
import requests
import random
from flask import Blueprint, redirect, session, request, render_template, abort
from functools import wraps
from database import Database

# 🔴 ১. Blueprint তৈরি করা হলো
auth_bp = Blueprint('auth', __name__)

# ⚠️ Discord OAuth2 Credentials
DISCORD_CLIENT_ID = "1431675966807343388"
DISCORD_CLIENT_SECRET = "AtCC606CiJo5BZwRdqHM-Qj6GQGAELo9"
DISCORD_REDIRECT_URI = "https://my-funny-py.onrender.com/discord/callback"

DISCORD_API_BASE_URL = "https://discord.com/api"
AUTHORIZATION_BASE_URL = f"{DISCORD_API_BASE_URL}/oauth2/authorize"
TOKEN_URL = f"{DISCORD_API_BASE_URL}/oauth2/token"

# ==========================================
# 🆕 Security Decorators for Route Protection
# ==========================================
def get_current_user():
    """Fetches user details from session and database."""
    user_session = session.get('user')
    if not user_session:
        return None
    
    col = Database.get_collection("users")
    if col is not None:
        db_user = col.find_one({"discord_id": user_session.get('id')})
        if db_user:
            return db_user
    return user_session

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user'):
            return redirect('/account') 
        return f(*args, **kwargs)
    return decorated_function

# 👑 Master Key: Owner (Super Admin) সব ড্যাশবোর্ডে যেতে পারবে!
def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            
            if not user:
                abort(403, description="Access Denied: You must be logged in.")
            
            user_role = user.get("role")
            
            # Owner হলে যেকোনো ড্যাশবোর্ডে অ্যাক্সেস পাবে
            if user_role == "owner":
                return f(*args, **kwargs)
                
            # অন্য ইউজারদের নির্দিষ্ট পারমিশন চেক করা
            if user_role not in allowed_roles:
                abort(403, description="Access Denied: You do not have permission to view this page.")
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# 🔴 ২. ডিসকর্ড লগইন রুট
@auth_bp.route('/login/discord')
def login_discord():
    auth_url = f"{AUTHORIZATION_BASE_URL}?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify%20email"
    return redirect(auth_url)


# 🔴 ৩. ডিসকর্ড কলব্যাক রুট
@auth_bp.route('/discord/callback')
def discord_callback():
    code = request.args.get('code')
    if not code: return "Login failed! <a href='/'>Go Home</a>"

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
    
    if "access_token" not in token_json: return "Failed to get access token from Discord."

    access_token = token_json['access_token']
    user_response = requests.get(f"{DISCORD_API_BASE_URL}/users/@me", headers={'Authorization': f'Bearer {access_token}'})
    user_info = user_response.json()

    discord_id = str(user_info.get('id'))
    email = user_info.get('email', '')
    
    col = Database.get_collection("users")
    db_user = None
    
    if col is not None:
        db_user = col.find_one({"discord_id": discord_id})
        
        if not db_user:
            random_id = f"INW-{random.randint(100000, 999999)}"
            initial_role = "owner" if email == "kstomh05@gmail.com" else "user"
            
            new_user = {
                "discord_id": discord_id,
                "username": user_info.get('username'),
                "email": email,
                "inwear_id": random_id,
                "role": initial_role,
                "avatar": f"https://cdn.discordapp.com/avatars/{discord_id}/{user_info.get('avatar')}.png" if user_info.get('avatar') else "https://via.placeholder.com/100"
            }
            col.insert_one(new_user)
            db_user = new_user
        else:
            if email == "kstomh05@gmail.com" and db_user.get("role") != "owner":
                col.update_one({"discord_id": discord_id}, {"$set": {"role": "owner"}})
                db_user["role"] = "owner"

    session['user'] = {
        'id': discord_id,
        'role': db_user.get("role") if db_user else "user"
    }

    return redirect('/')


# 🔴 ৪. ইউজার অ্যাকাউন্ট পেজ রুট
@auth_bp.route('/account')
def account_page():
    user_data = get_current_user()
    if not user_data: 
        return render_template('login.html') 
        
    return render_template('account.html', current_user=user_data)


# 🔴 ৫. লগআউট রুট
@auth_bp.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')


# ==========================================
# 🆕 Panel Routing & Dashboard Routes
# ==========================================

@auth_bp.route('/dashboards')
@login_required
def smart_dashboard_redirect():
    """Redirects user to their specific dashboard based on role."""
    user = get_current_user()
    role = user.get("role")
    
    if role == "owner":
        return redirect('/owner-dashboard')
    elif role == "seller":
        return redirect('/seller-dashboard')
    elif role == "delivery":
        return redirect('/delivery-dashboard')
    else:
        return redirect('/account')


# 👑 ওনার (Owner) ড্যাশবোর্ড (রিয়েল-টাইম লাইভ ডেটা সহ)
@auth_bp.route('/owner-dashboard')
@role_required('owner')
def owner_dashboard():
    user = get_current_user()
    
    db_users = Database.get_collection("users")
    db_orders = Database.get_collection("orders")
    db_products = Database.get_collection("products")
    
    total_users = db_users.count_documents({}) if db_users is not None else 0
    total_orders = db_orders.count_documents({}) if db_orders is not None else 0
    total_products = db_products.count_documents({}) if db_products is not None else 0
    
    pending_products = list(db_products.find({"status": "Pending"})) if db_products is not None else []
    latest_orders = list(db_orders.find({}).sort("_id", -1).limit(20)) if db_orders is not None else []

    # 🔴 FIXED: owner_dashboard.html (আপনার রিকোয়েস্ট অনুযায়ী আন্ডারস্কোর)
    return render_template('owner_dashboard.html', 
                           current_user=user,
                           total_users=total_users, 
                           total_orders=total_orders,
                           total_products=total_products,
                           pending_products=pending_products,
                           orders=latest_orders)


# 🏪 সেলার (Seller) ড্যাশবোর্ড (লাইভ প্রোডাক্ট সহ)
@auth_bp.route('/seller-dashboard')
@role_required('seller', 'owner')
def seller_dashboard():
    user = get_current_user()
    
    col = Database.get_collection("products")
    seller_products = list(col.find({"seller_id": str(user['id'])})) if col is not None else []
    
    # 🔴 FIXED: seller_dashboard.html (আপনার রিকোয়েস্ট অনুযায়ী আন্ডারস্কোর)
    return render_template('seller_dashboard.html', current_user=user, products=seller_products)


# Forms
@auth_bp.route('/apply-seller')
@login_required
def apply_seller():
    return render_template('apply-seller.html')

@auth_bp.route('/apply-delivery')
@login_required
def apply_delivery():
    return render_template('apply-delivery.html')
    
# ==========================================
# 🚀 Form Submission Handlers (Auto-Approve for now)
# ==========================================

@auth_bp.route('/submit-seller-application', methods=['POST'])
@login_required
def submit_seller_application():
    user = session.get('user')
    col = Database.get_collection("users")
    
    # ইউজারকে ডেটাবেসে 'seller' হিসেবে আপডেট করা হচ্ছে
    if col is not None:
        col.update_one({"discord_id": user['id']}, {"$set": {"role": "seller"}})
    
    # সেশন আপডেট করে সেলার ড্যাশবোর্ডে পাঠানো হচ্ছে
    session['user']['role'] = 'seller'
    session.modified = True
    return redirect('/seller-dashboard')


@auth_bp.route('/submit-delivery-application', methods=['POST'])
@login_required
def submit_delivery_application():
    user = session.get('user')
    col = Database.get_collection("users")
    
    # ইউজারকে ডেটাবেসে 'delivery' বয় হিসেবে আপডেট করা হচ্ছে
    if col is not None:
        col.update_one({"discord_id": user['id']}, {"$set": {"role": "delivery"}})
    
    # সেশন আপডেট করে ডেলিভারি ড্যাশবোর্ডে পাঠানো হচ্ছে
    session['user']['role'] = 'delivery'
    session.modified = True
    return redirect('/delivery/dashboard')
    
