from flask import Blueprint, render_template, redirect
from database import Database
from routes.auth import get_current_user, role_required
from bson.objectid import ObjectId

# নতুন ব্লুপ্রিন্ট
payouts_bp = Blueprint('payouts', __name__)

@payouts_bp.route('/owner/payouts')
@role_required('owner')
def owner_payouts():
    user = get_current_user()
    db_users = Database.get_collection("users")
    db_withdrawals = Database.get_collection("withdrawals")
    
    # ওনারের মোট আয় (১০% প্ল্যাটফর্ম চার্জ)
    owner_data = db_users.find_one({"email": "kstomh05@gmail.com"}) if db_users is not None else None
    platform_revenue = owner_data.get("platform_revenue", 0) if owner_data else 0
    
    # সেলারদের পেন্ডিং উইথড্রয়াল রিকোয়েস্ট
    pending_payouts = list(db_withdrawals.find({"status": "Pending"})) if db_withdrawals is not None else []
    
    return render_template('owner_payouts.html', current_user=user, platform_revenue=platform_revenue, payouts=pending_payouts)

@payouts_bp.route('/owner/approve-payout/<payout_id>', methods=['POST'])
@role_required('owner')
def approve_payout(payout_id):
    db_withdrawals = Database.get_collection("withdrawals")
    if db_withdrawals is not None:
        # পেমেন্ট ক্লিয়ার করে স্ট্যাটাস Paid করা হচ্ছে
        db_withdrawals.update_one({"_id": ObjectId(payout_id)}, {"$set": {"status": "Paid"}})
    return redirect('/owner/payouts')
  
