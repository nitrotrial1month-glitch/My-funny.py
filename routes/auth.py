import os
import requests
import random
from flask import Blueprint, redirect, session, request, render_template, abort
from functools import wraps
from database import Database

# 🔴 ১. এই ফাইলের জন্য Blueprint তৈরি করা হলো
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
            return redirect(url_for('auth.account_page')) # Redirect to login view
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user or user.get("role") not in allowed_roles:
                abort(403, description="Access Denied: You do not have permission to view this page.")
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# 🔴 ২. ডিসকর্ড লগইন রুট
@auth_bp.route('/login/discord')
def login_discord():
    # Only requesting basic identify scope. Email is not provided by default unless requested.
    auth_url = f"{AUTHORIZATION_BASE_URL}?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify%20email"
    return redirect(auth_url)


# 🔴 ৩. ডিসকর্ড কলব্যাক রুট (Updated with Role Logic)
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
    email = user_info.get('email', '') # Might be empty if Discord user hasn't verified email or denied access
    
    col = Database.get_collection("users")
    db_user = None
    
    if col is not None:
        db_user = col.find_one({"discord_id": discord_id})
        
        # If user doesn't exist in DB, create a new profile
        if not db_user:
            # Generate a random INW ID
            random_id = f"INW-{random.randint(100000, 999999)}"
            
            # Determine initial role. Check for Super Admin.
            initial_role = "user"
            if email == "kstomh05@gmail.com":
                initial_role = "owner"
            
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
            
            # Since it's a new user, you might want to redirect them to complete profile
            is_new_user = True
        else:
            is_new_user = False
            
            # Failsafe: Check if email matches super admin but role isn't owner yet
            if email == "kstomh05@gmail.com" and db_user.get("role") != "owner":
                col.update_one({"discord_id": discord_id}, {"$set": {"role": "owner"}})
                db_user["role"] = "owner"

    # Save to session (Keep it lightweight)
    session['user'] = {
        'id': discord_id,
        'role': db_user.get("role") if db_user else "user"
    }
    
    if is_new_user:
         # Optionally redirect to complete-profile if you want to gather more data
         # return redirect('/complete-profile')
         pass

    return redirect('/')


# 🔴 ৪. ইউজার অ্যাকাউন্ট পেজ রুট (Updated)
@auth_bp.route('/account')
def account_page():
    user_data = get_current_user()
    if not user_data: 
        return render_template('login.html') # Assuming you have a login.html template
        
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

@auth_bp.route('/owner-dashboard')
@role_required('owner')
def owner_dashboard():
    user = get_current_user()
    return render_template('owner-dashboard.html', current_user=user)

@auth_bp.route('/seller-dashboard')
@role_required('seller')
def seller_dashboard():
    user = get_current_user()
    return render_template('seller-dashboard.html', current_user=user)

@auth_bp.route('/delivery-dashboard')
@role_required('delivery')
def delivery_dashboard():
    user = get_current_user()
    return render_template('delivery-dashboard.html', current_user=user)
    
# Forms
@auth_bp.route('/apply-seller')
@login_required
def apply_seller():
    return render_template('apply-seller.html')

@auth_bp.route('/apply-delivery')
@login_required
def apply_delivery():
    return render_template('apply-delivery.html')
