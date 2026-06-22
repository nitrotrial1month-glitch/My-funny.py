import os
import random
from flask import Blueprint, redirect, url_for, session, request
import requests
from database import Database  # 🔴 ডাটাবেস ইমপোর্ট করা হলো

# ব্লুপ্রিন্ট তৈরি করা
google_bp = Blueprint('google', __name__)

# রেন্ডারের এনভায়রনমেন্ট ভেরিয়েবল থেকে তথ্য নেওয়া
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

# গুগল লগইন করার রুট
@google_bp.route('/login/google')
def login_google():
    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=email%20profile"
    )
    return redirect(auth_url)

# গুগল থেকে ফিরে আসার পর (callback)
@google_bp.route('/google/callback')
def google_callback():
    code = request.args.get('code')
    if not code:
        return "Google Login failed! <a href='/'>Go Home</a>"

    # টোকেন এক্সচেঞ্জ
    token_data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI
    }
    
    token_r = requests.post("https://oauth2.googleapis.com/token", data=token_data)
    token_json = token_r.json()
    access_token = token_json.get('access_token')

    if not access_token:
        return "Failed to get access token from Google."

    # ইউজারের প্রোফাইল তথ্য আনা
    user_info_r = requests.get(f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}")
    user_info = user_info_r.json()

    google_id = str(user_info.get('id'))
    email = user_info.get('email', '')
    username = user_info.get('name')
    avatar = user_info.get('picture')

    # ========================================================
    # 🔴 ডাটাবেস আপডেট এবং আপনার 'Owner' রোল সেট করার লজিক
    # ========================================================
    col = Database.get_collection("users")
    db_user = None
    
    if col is not None:
        db_user = col.find_one({"email": email})
        
        # যদি ইউজার ডাটাবেসে না থাকে (নতুন ইউজার)
        if not db_user:
            # আপনার ইমেইল হলে owner, না হলে user
            initial_role = "owner" if email == "kstomh05@gmail.com" else "user"
            
            db_user = {
                "discord_id": google_id, # সিস্টেম চেনার জন্য গুগল আইডিকেই এখানে রাখা হলো
                "username": username,
                "email": email,
                "inwear_id": f"INW-{random.randint(100000, 999999)}",
                "role": initial_role,
                "avatar": avatar,
                "is_google": True
            }
            col.insert_one(db_user)
            
        else:
            # যদি ইউজার আগে থেকেই থাকে কিন্তু owner রোল না থাকে (আপনার ইমেইলের জন্য)
            if email == "kstomh05@gmail.com" and db_user.get("role") != "owner":
                col.update_one({"email": email}, {"$set": {"role": "owner"}})
                db_user["role"] = "owner"

    # 🔴 সেশনে রোল (role) সহ ইউজারের তথ্য সেভ করা
    session['user'] = {
        'id': google_id,
        'username': username,
        'email': email,
        'avatar': avatar,
        'is_google': True,
        'role': db_user.get("role") if db_user else ("owner" if email == "kstomh05@gmail.com" else "user")
    }

    # সফল লগইনের পর ডাইরেক্ট ড্যাশবোর্ড প্যানেলে পাঠিয়ে দেওয়া
    return redirect('/dashboards')
    
