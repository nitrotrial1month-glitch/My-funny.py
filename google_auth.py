from flask import Blueprint, redirect, url_for, session, request
import requests

# গুগল লগইনের জন্য ব্লুপ্রিন্ট
google_bp = Blueprint('google', __name__)

# আপনার গুগল ক্রেডেনশিয়ালস
CLIENT_ID = "715926390736-718gc5g9vndl35glj5iancfmn3muomvs.apps.googleusercontent.com"
CLIENT_SECRET = "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"
REDIRECT_URI = "https://my-funny-py.onrender.com/google/callback"

@google_bp.route('/login/google')
def login_google():
    # ইউজারকে গুগল লগইন পেজে রিডাইরেক্ট করা
    auth_url = f"https://accounts.google.com/o/oauth2/auth?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=email%20profile"
    return redirect(auth_url)

@google_bp.route('/google/callback')
def google_callback():
    code = request.args.get('code')
    if not code:
        return "Google Login failed!"

    # গুগল থেকে টোকেন নেওয়া
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
        return "Failed to get access token."

    # ইউজারের প্রোফাইল তথ্য আনা
    user_info_r = requests.get(f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}")
    user_info = user_info_r.json()

    # সেশনে ইউজারের তথ্য সেভ করা
    session['user'] = {
        'id': user_info.get('id'),
        'username': user_info.get('name'),
        'email': user_info.get('email'),
        'avatar': user_info.get('picture'),
        'method': 'google' # লগইন মেথড ট্র্যাক করার জন্য
    }

    return redirect(url_for('home'))
    
