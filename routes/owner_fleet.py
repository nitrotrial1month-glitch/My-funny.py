from flask import Blueprint, render_template, redirect, request
from database import Database
from routes.auth import get_current_user, role_required

# নতুন ব্লুপ্রিন্ট
fleet_bp = Blueprint('fleet', __name__)

@fleet_bp.route('/owner/fleet')
@role_required('owner')
def owner_fleet():
    user = get_current_user()
    db_users = Database.get_collection("users")
    
    # ডেটাবেস থেকে সব ডেলিভারি বয়দের খুঁজে আনা হচ্ছে
    delivery_boys = list(db_users.find({"role": "delivery"})) if db_users is not None else []
    
    return render_template('owner_fleet.html', current_user=user, fleet=delivery_boys)

@fleet_bp.route('/owner/remove-delivery/<user_id>', methods=['POST'])
@role_required('owner')
def remove_delivery(user_id):
    db_users = Database.get_collection("users")
    if db_users is not None:
        # ডেলিভারি বয়কে সরিয়ে সাধারণ ইউজার বানানো হচ্ছে
        db_users.update_one({"discord_id": user_id}, {"$set": {"role": "user"}})
    return redirect('/owner/fleet')
  
