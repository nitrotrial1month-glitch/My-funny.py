from flask import Blueprint, render_template, request, redirect, session, flash, url_for, abort
from database import Database
from datetime import datetime
from bson import ObjectId
from functools import wraps

# 🔴 FIX: রাউট ফোল্ডারের ভেতর থেকে সিকিউরিটি ফাংশন ইমপোর্ট করা
from routes.auth import role_required

seller_bp = Blueprint('seller', __name__)

# সেলার অথেন্টিকেশন সিকিউরিটি
def seller_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user.get('role') not in ['seller', 'owner']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# ১. সেলারের ওয়ালেট পেজ
@seller_bp.route('/seller/wallet')
@seller_required
def seller_wallet():
    user = session.get('user')
    col = Database.get_collection("users")
    seller_data = col.find_one({"discord_id": str(user['id'])})
    
    withdraw_col = Database.get_collection("withdrawals")
    history = list(withdraw_col.find({"seller_id": str(user['id'])}).sort("_id", -1))

    return render_template('seller_wallet.html', seller=seller_data, withdrawals=history)

# ২. নতুন UPI ID অ্যাড করা
@seller_bp.route('/seller/add_upi', methods=['POST'])
@seller_required
def add_upi():
    user = session.get('user')
    new_upi = request.form.get('new_upi')
    if new_upi:
        col = Database.get_collection("users")
        seller = col.find_one({"discord_id": str(user['id'])})
        upi_list = seller.get('upi_list', [])
        is_first = len(upi_list) == 0
        upi_list.append({"upi_id": new_upi, "is_default": is_first})
        col.update_one({"discord_id": str(user['id'])}, {"$set": {"upi_list": upi_list}})
        flash("UPI ID Added Successfully!")
    return redirect(url_for('seller.seller_wallet'))

# ৩. ডিফল্ট UPI সেট করা
@seller_bp.route('/seller/set_default_upi/<int:index>', methods=['POST'])
@seller_required
def set_default_upi(index):
    user = session.get('user')
    col = Database.get_collection("users")
    seller = col.find_one({"discord_id": str(user['id'])})
    upi_list = seller.get('upi_list', [])
    if 0 <= index < len(upi_list):
        for i, upi in enumerate(upi_list):
            upi['is_default'] = (i == index)
        col.update_one({"discord_id": str(user['id'])}, {"$set": {"upi_list": upi_list}})
    return redirect(url_for('seller.seller_wallet'))

# ৪. উইথড্র রিকোয়েস্ট পাঠানো
@seller_bp.route('/seller/withdraw', methods=['POST'])
@seller_required
def request_withdrawal():
    user = session.get('user')
    amount = float(request.form.get('amount', 0))
    upi_id = request.form.get('upi_id')
    col = Database.get_collection("users")
    seller = col.find_one({"discord_id": str(user['id'])})
    current_balance = float(seller.get('wallet_balance', 0.0))

    if amount >= 100 and amount <= current_balance:
        col.update_one({"discord_id": str(user['id'])}, {"$inc": {"wallet_balance": -amount}})
        Database.get_collection("withdrawals").insert_one({
            "seller_id": str(user['id']),
            "seller_name": seller.get("username", "Unknown"),
            "amount": amount,
            "upi_id": upi_id,
            "status": "Pending",
            "date": datetime.now().strftime("%Y-%m-%d %I:%M %p")
        })
        flash(f"Withdrawal request of ₹{amount} submitted!")
    else:
        flash("Invalid amount or insufficient balance.")
    return redirect(url_for('seller.seller_wallet'))
    
