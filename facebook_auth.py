import os
from flask import Blueprint, redirect, url_for, session, request
import requests

facebook_bp = Blueprint('facebook', __name__)

APP_ID = os.getenv("FACEBOOK_APP_ID")
APP_SECRET = os.getenv("FACEBOOK_APP_SECRET")
REDIRECT_URI = os.getenv("FACEBOOK_REDIRECT_URI")

@facebook_bp.route('/login/facebook')
def login_facebook():
    # ফেসবুক অথরাইজেশন ইউআরএল
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

    # টোকেন এক্সচেঞ্জ করা
    token_url = f"https://graph.facebook.com/v12.0/oauth/access_token?client_id={APP_ID}&redirect_uri={REDIRECT_URI}&client_secret={APP_SECRET}&code={code}"
    token_r = requests.get(token_url)
    token_data = token_r.json()
    access_token = token_data.get('access_token')

    if not access_token:
        return "Failed to get access token from Facebook."

    # ইউজারের প্রোফাইল তথ্য আনা
    user_info_r = requests.get(f"https://graph.facebook.com/me?fields=id,name,email,picture&access_token={access_token}")
    user_info = user_info_r.json()

    # সেশনে সেভ করা
    session['user'] = {
        'id': user_info.get('id'),
        'username': user_info.get('name'),
        'email': user_info.get('email'),
        'avatar': user_info.get('picture', {}).get('data', {}).get('url'),
        'is_facebook': True
    }

    return redirect(url_for('home'))
    
