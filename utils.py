import json
import os
import datetime
import discord

# --- কনফিগারেশন ফাইল ও আইডি ---
CONFIG_FILE = 'config.json'
PREMIUM_FILE = 'premium.json'  # প্রিমিয়াম ডাটা ফাইল

# আপনার দেওয়া তথ্য
OWNER_ID = 1311355680640208926
UPI_ID = "kstomh05@okicici"

# --- ১. কনফিগারেশন লোড ও সেভ (আপনার আগের কোড) ---

def load_config():
    """সব ফিচারের সেটিংস লোড করে এবং নতুন কি (key) যোগ করে"""
    default_data = {
        "prefixes": {}, # সার্ভার অনুযায়ী প্রেফিক্স
        "premium_servers": {},
        "premium_users": {},
        "welcome_settings": {"enabled": False, "channel_id": None},
        "ticket_settings": {"support_roles": [], "count": 0},
        
        # --- Live Notifications ---
        "live_settings": {
            "channel_id": None,
            "ping_role": None,
            "yt_channels": [],
            "twitch_users": [],
            "last_notified": {}
        },
        
        # --- Invite Tracker ---
        "invite_settings": {
            "enabled": False,
            "log_channel": None,
            "template": {
                "title": "📥 New Member Joined",
                "description": "{member} has joined **{server}**, invited by {inviter}, who now has **{invites}** invites.",
                "image": None,
                "footer": "Join time: {join_time}"
            },
            "milestones": {} # ইনভাইট রোলের জন্য
        },
        "invite_data": {} # প্রতি ইউজারের ইনভাইট সংখ্যা সেভ রাখার জন্য
    }

    # ফাইল না থাকলে তৈরি করবে
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=4)
        return default_data
    
    # ফাইল থাকলে সেটি পড়বে
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            # লজিক যাতে না ভাঙে: নতুন কোনো অপশন default_data-তে থাকলে তা মেইন ফাইলে যুক্ত করবে
            for key, value in default_data.items():
                if key not in data:
                    data[key] = value
                # নেস্টেড ডিকশনারি চেক (যেমন invite_settings এর ভিতর template)
                elif isinstance(value, dict) and isinstance(data[key], dict):
                    for sub_key, sub_value in value.items():
                        if sub_key not in data[key]:
                            data[key][sub_key] = sub_value
            return data
        except:
            return default_data

def save_config(data):
    """ডাটা config.json ফাইলে রাইট করবে"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_theme_color(guild_id):
    """বটের জন্য ডিফল্ট নীল কালার রিটার্ন করে"""
    return discord.Color.blue()


# --- ২. নতুন যুক্ত করা হলো: প্রিমিয়াম চেকার ফাংশন ---

def check_premium(target_id, p_type="user"):
    """
    target_id: User ID or Server ID
    p_type: "user" or "server"
    Return: True (যদি প্রিমিয়াম থাকে), False (না থাকলে)
    """
    # ফাইল না থাকলে প্রিমিয়াম নেই
    if not os.path.exists(PREMIUM_FILE):
        return False

    try:
        with open(PREMIUM_FILE, "r") as f:
            data = json.load(f)

        category = "users" if p_type == "user" else "servers"
        sid = str(target_id)

        # চেক করা আইডি লিস্টে আছে কিনা
        if sid in data.get(category, {}):
            expire_str = data[category][sid]["expire_at"]
            
            # তারিখ কনভার্ট করা
            expire_date = datetime.datetime.fromisoformat(expire_str)

            # বর্তমান সময়ের সাথে মেয়াদ চেক
            if datetime.datetime.now() < expire_date:
                return True # মেয়াদ আছে
            else:
                return False # মেয়াদ শেষ (Expried)
                
        return False # লিস্টেই নেই

    except Exception as e:
        print(f"Error checking premium: {e}")
        return False
        
