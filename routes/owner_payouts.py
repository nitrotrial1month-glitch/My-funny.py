from flask import Blueprint, render_template, redirect, flash, request
from database import Database
from bson.objectid import ObjectId
from routes.auth import role_required

owner_payouts_bp = Blueprint('owner_payouts', __name__)

# ১. Payout ড্যাশবোর্ড দেখানো
@owner_payouts_bp.route('/owner/payouts')
@role_required('owner')
def owner_payouts():
    col = Database.get_collection("withdrawals")
    
    # পেন্ডিং এবং কমপ্লিট হওয়া রিকোয়েস্টগুলো আলাদা করে ডেটাবেস থেকে টানা হচ্ছে
    pending_requests = list(col.find({"status": "Pending"}).sort("_id", -1))
    payout_history = list(col.find({"status": {"$in": ["Paid", "Rejected"]}}).sort("_id", -1).limit(30))
    
    return render_template('owner_payouts.html', pending=pending_requests, history=payout_history)


# ২. Payout অ্যাপ্রুভ করা (Paid)
@owner_payouts_bp.route('/owner/payouts/approve/<req_id>', methods=['POST'])
@role_required('owner')
def approve_payout(req_id):
    col = Database.get_collection("withdrawals")
    
    # স্ট্যাটাস 'Paid' করে দেওয়া হলো
    col.update_one({"_id": ObjectId(req_id)}, {"$set": {"status": "Paid"}})
    flash("✅ Payout marked as Paid successfully!")
    
    return redirect('/owner/payouts')


# ৩. Payout রিজেক্ট করা (Refund)
@owner_payouts_bp.route('/owner/payouts/reject/<req_id>', methods=['POST'])
@role_required('owner')
def reject_payout(req_id):
    col_withdraw = Database.get_collection("withdrawals")
    col_users = Database.get_collection("users")
    
    req = col_withdraw.find_one({"_id": ObjectId(req_id)})
    if req and req.get('status') == 'Pending':
        # 🔴 UPDATE: WBM_U_ID ব্যবহার করে রিফান্ড করা হচ্ছে
        col_users.update_one(
            {"WBM_U_ID": req['seller_id']}, 
            {"$inc": {"wallet_balance": float(req['amount'])}}
        )
        # স্ট্যাটাস 'Rejected' করে দেওয়া হলো
        col_withdraw.update_one({"_id": ObjectId(req_id)}, {"$set": {"status": "Rejected"}})
        flash("❌ Payout rejected. Amount refunded to seller's wallet.")
        
    return redirect('/owner/payouts')
    
