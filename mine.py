import json
import os
import datetime
import discord

CONFIG_FILE = 'config.json'

def load_config():
    """সব ফিচারের ডিফল্ট সেটিংস লোড করে"""
    default_data = {
        "premium_servers": {},
        "premium_users": {},
        "welcome_settings": {
            "enabled": False,
            "channel_id": None,
            "message": "Welcome {member} to {server}!",
            "image_url": "https://img.freepik.com/free-vector/abstract-blue-geometric-shapes-background_1035-17545.jpg",
            "accent_color": 0xFFFFFF,
            "ping_delete": False
        },
        "daily_settings": {
            "image_url": None,
            "message": "Here is your daily reward!"
        },
        "poll_settings": {
            "title": "📊 COMMUNITY POLL",
            "emoji": "🗳️",
            "image_url": None,
            "color": 0x3498db
        }
    }

    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=4)
        return default_data
    
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            for key, value in default_data.items():
                if key not in data:
                    data[key] = value
            return data
        except:
            return default_data

def save_config(data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def get_theme_color(guild_id):
    """Premium (Gold) বা Free (Blue) কালার রিটার্ন করে"""
    if not guild_id: return discord.Color.blue()
    
    config = load_config()
    now = datetime.datetime.now()
    
    if str(guild_id) in config.get("premium_servers", {}):
        expiry_str = config["premium_servers"][str(guild_id)]["expiry"]
        try:
            expiry = datetime.datetime.fromisoformat(expiry_str)
            if now < expiry:
                return discord.Color.gold()
        except:
            pass 

    return discord.Color.blue()
            
