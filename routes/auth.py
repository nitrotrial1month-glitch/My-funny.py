import os
import requests
import random
from flask import Blueprint, redirect, session, request, render_template, abort, flash
from functools import wraps
from werkzeug.utils import secure_filename
from database import Database

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

auth_bp = Blueprint('auth', __name__)

DISCORD_CLIENT_ID = "1431675966807343388"
DISCORD_CLIENT_SECRET = "AtCC606CiJo5BZwRdqHM-Qj6GQGAELo9"
DISCORD_REDIRECT_URI = "https://my-funny-py.onrender.com/discord/callback"

DISCORD_API_BASE_URL = "https://discord.com/api"
AUTHORIZATION_BASE_URL = f"{DISCORD_API_BASE_URL}/oauth2/authorize"
TOKEN_URL = f"{DISCORD_API_BASE_URL}/oauth2/token"

# ==========================================
# 🆕 Security Decorators
# ==========================================
def get_current_user():
    user_session = session.get('user')
    if not user_session:
        return None
    
    col = Database.get_collection("users")
    if col is not None:
        db_user = col.find_one({"WBM_U_ID": user_session.get('id')})
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

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                abort(403, description="Access Denied: You must be logged in.")
            
            user_role = user.get("role")
            if user_role == "owner":
                return f(*args, **kwargs)
                
            if user_role not in allowed_roles:
                abort(403, description="Access Denied: You do not have permission.")
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ==========================================
# 🔴 লগইন এবং কলব্যাক রুট
# ==========================================
@auth_bp.route('/login/discord')
def login_discord():
    auth_url = f"{AUTHORIZATION_BASE_URL}?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify%20email"
    return redirect(auth_url)

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
        if email:
            db_user = col.find_one({"email": email})
        if not db_user:
            db_user = col.find_one({"discord_id": discord_id})
        
        if not db_user:
            random_id = f"{random.randint(10000, 99999)}WBM{random.randint(100, 999)}"
            initial_role = "owner" if email == "kstomh05@gmail.com" else "user"
            
            new_user = {
                "discord_id": discord_id,
                "username": user_info.get('username'),
                "email": email,
                "WBM_U_ID": random_id,
                "role": initial_role,
                "avatar": f"https://cdn.discordapp.com/avatars/{discord_id}/{user_info.get('avatar')}.png" if user_info.get('avatar') else "https://via.placeholder.com/100"
            }
            col.insert_one(new_user)
            db_user = new_user
        else:
            if 'WBM_U_ID' not in db_user:
                WBM_U_ID = f"{random.randint(10000, 99999)}WBM{random.randint(100, 999)}"
                col.update_one({"_id": db_user["_id"]}, {"$set": {"WBM_U_ID": WBM_U_ID, "discord_id": discord_id}})
                db_user['WBM_U_ID'] = WBM_U_ID
                
            if email == "kstomh05@gmail.com" and db_user.get("role") != "owner":
                col.update_one({"_id": db_user["_id"]}, {"$set": {"role": "owner"}})
                db_user["role"] = "owner"

    session['user'] = {
        'id': db_user.get('WBM_U_ID'),
        'username': user_info.get('username'),
        'email': email,
        'role': db_user.get("role")
    }

    return redirect('/')

@auth_bp.route('/account')
def account_page():
    user_data = get_current_user()
    if not user_data: 
        return render_template('login.html') 
    return render_template('account.html', current_user=user_data)

@auth_bp.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

@auth_bp.route('/dashboards')
@login_required
def smart_dashboard_redirect():
    user = get_current_user()
    role = user.get("role")
    if role == "owner": return redirect('/owner-dashboard')
    elif role == "seller": return redirect('/seller-dashboard')
    elif role == "delivery": return redirect('/delivery-dashboard')
    else: return redirect('/account')

# ==========================================
# 🚚 Delivery Routes (Kept in Auth for now)
# ==========================================
@auth_bp.route('/delivery-dashboard')
@role_required('delivery', 'owner')
def delivery_dashboard():
    user = get_current_user()
    col = Database.get_collection("orders")
    active_orders = list(col.find({"status": "Confirmed"}).sort("_id", -1)) if col is not None else []
    return render_template('delivery_dashboard.html', current_user=user, orders=active_orders)

@auth_bp.route('/apply-delivery')
@login_required
def apply_delivery():
    return render_template('apply-delivery.html')

@auth_bp.route('/submit-delivery-application', methods=['POST'])
@login_required
def submit_delivery_application():
    try:
        user = session.get('user')
        col = Database.get_collection("users")
        
        full_name = request.form.get('full_name')
        phone = request.form.get('phone_number')
        delivery_area = request.form.get('delivery_area')
        vehicle_type = request.form.get('vehicle_type')
        upi_id = request.form.get('upi_id')
        bank_account = request.form.get('bank_account', '')
        id_type = request.form.get('id_type')
        id_number = request.form.get('id_number')
        
        kyc_file = request.files.get('id_document')
        profile_file = request.files.get('user_profile_photo')
        dl_file = request.files.get('driving_license')
        
        kyc_filename = secure_filename(kyc_file.filename) if kyc_file and kyc_file.filename else ""
        profile_filename = secure_filename(profile_file.filename) if profile_file and profile_file.filename else ""
        dl_filename = secure_filename(dl_file.filename) if dl_file and dl_file.filename else ""
        
        if kyc_file and kyc_file.filename: kyc_file.save(os.path.join(UPLOAD_FOLDER, kyc_filename))
        if profile_file and profile_file.filename: profile_file.save(os.path.join(UPLOAD_FOLDER, profile_filename))
        if dl_file and dl_file.filename: dl_file.save(os.path.join(UPLOAD_FOLDER, dl_filename))
        
        if col is not None:
            col.update_one({"WBM_U_ID": user['id']}, {"$set": {
                "role": "pending_delivery",
                "application_data": {
                    "full_name": full_name, "phone": phone, "area": delivery_area,
                    "vehicle": vehicle_type, "upi_id": upi_id, "bank_account": bank_account,
                    "id_type": id_type, "id_number": id_number, "kyc_image": kyc_filename,
                    "profile_image": profile_filename, "dl_image": dl_filename
                }
            }})
        
        session['user']['role'] = 'pending_delivery'
        session.modified = True
        flash("Your Delivery application is submitted and waiting for Admin approval.")
        return redirect('/account')
    except Exception as e:
        return f"Submission Error: {str(e)}", 500
        
