import json
import os
import datetime
import discord

CONFIG_FILE = 'config.json'

def load_config():
    """ডিফল্ট সেটিংস লোড করে"""
    default_data = {
        "prefixes": {}, # সার্ভার অনুযায়ী প্রেফিক্স সেভ হবে
        "premium_servers": {},
        "premium_users": {},
        "welcome_settings": {"enabled": False, "channel_id": None},
        "ticket_settings": {"support_roles": [], "count": 0}
    }

    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=4)
        return default_data
    
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            # নতুন কোনো কি (key) মিস থাকলে সেটি অ্যাড করবে
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
    """থিম কালার রিটার্ন করে"""
    return discord.Color.blue()
    
