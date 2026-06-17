import os
from flask import Flask, render_template, redirect, url_for, session, request
from threading import Thread
import requests
from database import Database  

app = Flask(__name__)
# Session-এর জন্য একটি সিক্রেট কি (এটি যেকোনো কিছু হতে পারে)
app.secret_key = "inwear_super_secret_key_2026"

# ⚠️ Discord OAuth2 Credentials (এখানে আপনার তথ্য দিন)
DISCORD_CLIENT_ID = "1431675966807343388"
DISCORD_CLIENT_SECRET = "AtCC606CiJo5BZwRdqHM-Qj6GQGAELo9"

# Redirect URI (এটি আপনার লোকাল বা লাইভ ওয়েবসাইটের লিংক হবে)
DISCORD_REDIRECT_URI = "http://127.0.0.1:8080/discord/callback" 
# রেন্ডারে লাইভ করার সময় এটি "https://your-render-url.com/discord/callback" করে দেবেন

DISCORD_API_BASE_URL = "https://discord.com/api"
AUTHORIZATION_BASE_URL = f"{DISCORD_API_BASE_URL}/oauth2/authorize"
TOKEN_URL = f"{DISCORD_API_BASE_URL}/oauth2/token"


# --- Home Route ---
@app.route('/')
def home():
    products = Database.get_all_products()
    # ইউজারের সেশন থেকে নাম নেওয়া (লগইন করা থাকলে নাম দেখাবে)
    user_data = session.get('user')
    return render_template('index.html', products=products, user=user_data)


# --- Discord Login Routes ---
@app.route('/login/discord')
def login_discord():
    """ইউজারকে ডিসকর্ডের লগইন পেজে পাঠাবে"""
    auth_url = f"{AUTHORIZATION_BASE_URL}?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify%20guilds"
    return redirect(auth_url)

@app.route('/discord/callback')
def discord_callback():
    """ডিসকর্ড থেকে লগইন করার পর ইউজার এই পেজে ফিরে আসবে"""
    code = request.args.get('code')
    if not code:
        return "Login failed! <a href='/'>Go Home</a>"

    # কোড এক্সচেঞ্জ করে টোকেন নেওয়া
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

    # ইউজারের ডিসকর্ড প্রোফাইলের তথ্য আনা
    user_response = requests.get(f"{DISCORD_API_BASE_URL}/users/@me", headers={'Authorization': f'Bearer {access_token}'})
    user_info = user_response.json()

    # সেশনে ইউজারের তথ্য সেভ করা
    session['user'] = {
        'id': user_info.get('id'),
        'username': user_info.get('username'),
        'avatar': f"https://cdn.discordapp.com/avatars/{user_info.get('id')}/{user_info.get('avatar')}.png"
    }

    # সফল লগইনের পর হোমপেজে পাঠিয়ে দেওয়া
    return redirect(url_for('home'))


@app.route('/logout')
def logout():
    """ইউজারকে লগআউট করার সিস্টেম"""
    session.pop('user', None)
    return redirect(url_for('home'))


# --- Server Setup ---
def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    server = Thread(target=run)
    server.start()
    
