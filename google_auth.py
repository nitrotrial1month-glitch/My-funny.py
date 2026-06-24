import os
import random
from flask import Blueprint, redirect, url_for, session, request
import requests
from database import Database

google_bp = Blueprint('google', __name__)

CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")

@google_bp.route('/login/google')
def login_google():
    if not CLIENT_ID or not REDIRECT_URI:
        return "<h3>Server Error:</h3><p>Google Client ID or Redirect URI is missing in environment variables!</p>"
        
    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=email%20profile"
    )
    return redirect(auth_url)

@google_bp.route('/google/callback')
def google_callback():
    try:
        code = request.args.get('code')
        if not code:
            return "Google Login failed! No code provided. <a href='/'>Go Home</a>"

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
            return f"<h3>Authentication Failed:</h3><p>Google Response: {token_json}</p><a href='/'>Go Home</a>"

        user_info_r = requests.get(f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}")
        user_info = user_info_r.json()

        google_id = str(user_info.get('id'))
        email = user_info.get('email', '')
        username = user_info.get('name', 'User')
        avatar = user_info.get('picture', '')

        col = Database.get_collection("users")
        db_user = None
        
        if col is not None:
            if email:
                db_user = col.find_one({"email": email})
            if not db_user:
                db_user = col.find_one({"google_id": google_id})

            if not db_user:
                inwear_id = f"INW-{random.randint(100000, 999999)}"
                initial_role = "owner" if email == "kstomh05@gmail.com" else "user"
                db_user = {
                    "google_id": google_id, 
                    "username": username,
                    "email": email,
                    "inwear_id": inwear_id,
                    "role": initial_role,
                    "avatar": avatar,
                    "is_google": True
                }
                col.insert_one(db_user)
            else:
                if 'inwear_id' not in db_user:
                    inwear_id = f"INW-{random.randint(100000, 999999)}"
                    col.update_one({"_id": db_user["_id"]}, {"$set": {"inwear_id": inwear_id, "google_id": google_id}})
                    db_user['inwear_id'] = inwear_id
                    
                if email == "kstomh05@gmail.com" and db_user.get("role") != "owner":
                    col.update_one({"_id": db_user["_id"]}, {"$set": {"role": "owner"}})
                    db_user["role"] = "owner"

        # 🔴 UPDATE: সেশনে এখন থেকে সবসময় `inwear_id` সেভ হবে
        session['user'] = {
            'id': db_user.get('inwear_id'),
            'username': username,
            'email': email,
            'avatar': avatar,
            'is_google': True,
            'role': db_user.get("role")
        }
        return redirect('/')
        
    except Exception as e:
        return f"<h2>System Error During Login:</h2><p style='color:red;'>{str(e)}</p><br><a href='/'>Go Back</a>"
        
