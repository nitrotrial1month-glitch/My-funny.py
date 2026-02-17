import discord
import datetime
# 👇 ডাটাবেস ইমপোর্ট
from database import Database

# আপনার আইডি
OWNER_ID = 1311355680640208926
UPI_ID = "kstomh05@okicici"

# --- ১. কনফিগারেশন লোড (ডাটাবেস থেকে) ---
def load_config():
    """ডাটাবেস থেকে কনফিগ লোড করে, না থাকলে ডিফল্ট রিটার্ন করে"""
    
    # ডিফল্ট স্ট্রাকচার (যদি নতুন কোনো অপশন লাগে এখানে এড করবেন)
    default_data = {
        "prefixes": {},
        "welcome_settings": {"enabled": False, "channel_id": None},
        "ticket_settings": {"support_roles": [], "count": 0},
        "live_settings": {
            "channel_id": None, "ping_role": None, 
            "yt_channels": [], "twitch_users": [], "last_notified": {}
        },
        "invite_settings": {
            "enabled": False, "log_channel": None,
            "template": {
                "title": "📥 New Member Joined",
                "description": "{member} has joined **{server}**, invited by {inviter}, who now has **{invites}** invites.",
                "image": None, "footer": "Join time: {join_time}"
            },
            "milestones": {}
        },
        "invite_data": {}
    }

    # ডাটাবেস থেকে আনা
    db_data = Database.get_config()
    
    # মার্জ করা (যাতে নতুন ফিচার যোগ করলে এরর না দেয়)
    # যদি ডাটাবেস খালি থাকে, ডিফল্ট রিটার্ন করো
    if not db_data:
        return default_data

    # ডাটাবেসের ডাটার সাথে ডিফল্ট ডাটা মার্জ করা
    for key, value in default_data.items():
        if key not in db_data:
            db_data[key] = value
        elif isinstance(value, dict) and isinstance(db_data[key], dict):
            for sub_key, sub_value in value.items():
                if sub_key not in db_data[key]:
                    db_data[key][sub_key] = sub_value
    
    return db_data

def save_config(data):
    """ডাটাবেসে কনফিগ সেভ করে"""
    Database.save_config(data)

def get_theme_color(guild_id):
    return discord.Color.blue()

# --- ২. প্রিমিয়াম চেকার (ডাটাবেস থেকে) ---
def check_premium(target_id, p_type="user"):
    """
    target_id: User ID or Server ID
    p_type: "user" or "server"
    Return: True (যদি প্রিমিয়াম থাকে), False (না থাকলে)
    """
    try:
        # ডাটাবেস থেকে প্রিমিয়াম লিস্ট আনা
        data = Database.get_premium_data()
        
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
                return False # মেয়াদ শেষ (Expired)
                
        return False # লিস্টেই নেই

    except Exception as e:
        print(f"Error checking premium: {e}")
        return False
