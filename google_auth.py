import os
from flask import Blueprint, redirect, url_for, session, request
import requests

# ব্লুপ্রিন্ট তৈরি করা
google_bp = Blueprint('google', __name__)

# রেন্ডারের এনভায়রনমেন্ট ভেরিয়েবল থেকে তথ্য নেওয়া হচ্ছে (কোনো কোড এখানে বসাতে হবে না)
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

# গুগল লগইন করার রুট
@google_bp.route('/login/google')
def login_google():
    # গুগল অথরাইজেশন ইউআরএল
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

    # টোকেন এক্সচেঞ্জ করার ডেটা
    token_data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI
    }
    
    # গুগল থেকে এক্সেস টোকেন নেওয়া
    token_r = requests.post("https://oauth2.googleapis.com/token", data=token_data)
    token_json = token_r.json()
    access_token = token_json.get('access_token')

    if not access_token:
        return "Failed to get access token from Google."

    # ইউজারের প্রোফাইল তথ্য আনা
    user_info_r = requests.get(f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}")
    user_info = user_info_r.json()

    # সেশনে ইউজারের তথ্য সেভ করা
    session['user'] = {
        'id': user_info.get('id'),
        'username': user_info.get('name'),
        'email': user_info.get('email'),
        'avatar': user_info.get('picture'),
        'is_google': True
    }

    # সফল লগইনের পর হোমপেজে পাঠিয়ে দেওয়া
    return redirect(url_for('home'))
    
