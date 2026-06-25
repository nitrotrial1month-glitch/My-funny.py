import os
import random
from flask import Blueprint, redirect, request, session
import requests
from database import Database

facebook_bp = Blueprint('facebook', __name__)

APP_ID = os.getenv("FACEBOOK_APP_ID")
APP_SECRET = os.getenv("FACEBOOK_APP_SECRET")
REDIRECT_URI = os.getenv("FACEBOOK_REDIRECT_URI")

@facebook_bp.route('/login/facebook')
def login_facebook():
    auth_url = (
        f"https://www.facebook.com/v12.0/dialog/oauth?"
        f"client_id={APP_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"scope=email,public_profile"
    )
    return redirect(auth_url)

@facebook_bp.route('/facebook/callback')
def facebook_callback():
    code = request.args.get('code')
    if not code:
        return "Facebook Login failed! <a href='/'>Go Home</a>"

    token_url = f"https://graph.facebook.com/v12.0/oauth/access_token?client_id={APP_ID}&redirect_uri={REDIRECT_URI}&client_secret={APP_SECRET}&code={code}"
    token_r = requests.get(token_url)
    token_data = token_r.json()
    access_token = token_data.get('access_token')

    if not access_token:
        return "Failed to get access token from Facebook."

    user_info_r = requests.get(f"https://graph.facebook.com/me?fields=id,name,email,picture&access_token={access_token}")
    user_info = user_info_r.json()

    fb_id = str(user_info.get('id'))
    email = user_info.get('email', '')
    username = user_info.get('name', 'Facebook User')
    avatar = user_info.get('picture', {}).get('data', {}).get('url', '')

    col = Database.get_collection("users")
    db_user = None
    
    if col is not None:
        if email:
            db_user = col.find_one({"email": email})
        if not db_user:
            db_user = col.find_one({"facebook_id": fb_id})
            
        if not db_user:
            # 🔴 NEW: WBM_U_ID জেনারেট লজিক
            new_wbm_id = f"{random.randint(10000, 99999)}WBM{random.randint(100, 999)}"
            initial_role = "owner" if email == "kstomh05@gmail.com" else "user"
            db_user = {
                "facebook_id": fb_id,
                "username": username,
                "email": email,
                "WBM_U_ID": new_wbm_id,
                "role": initial_role,
                "avatar": avatar,
                "is_facebook": True
            }
            col.insert_one(db_user)
        else:
            # 🔴 Update old ID to new WBM_U_ID if missing
            if 'WBM_U_ID' not in db_user:
                new_wbm_id = f"{random.randint(10000, 99999)}WBM{random.randint(100, 999)}"
                col.update_one({"_id": db_user["_id"]}, {"$set": {"WBM_U_ID": new_wbm_id, "facebook_id": fb_id}})
                db_user['WBM_U_ID'] = new_wbm_id
            
            if email == "kstomh05@gmail.com" and db_user.get("role") != "owner":
                col.update_one({"_id": db_user["_id"]}, {"$set": {"role": "owner"}})
                db_user["role"] = "owner"

    session['user'] = {
        'id': db_user.get('WBM_U_ID'), 
        'username': username,
        'email': email,
        'avatar': avatar,
        'is_facebook': True,
        'role': db_user.get("role")
    }

    return redirect('/')
    
