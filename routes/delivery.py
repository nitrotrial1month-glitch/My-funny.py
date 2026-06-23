import random
from datetime import datetime, timedelta
from flask import Blueprint, render_template, session, redirect, abort, url_for, request, flash
from database import Database
from bson import ObjectId
from functools import wraps

delivery_bp = Blueprint('delivery', __name__)

# Security: ডেলিভারি পার্টনার (বা Owner) ছাড়া কেউ এই পেজ দেখতে পারবে না
def delivery_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user.get('role') not in ['delivery', 'owner']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# ==========================================
# 🚚 ১. Delivery Dashboard (With Auto-Refresh Logic)
# ==========================================
@delivery_bp.route('/delivery-dashboard')
@delivery_required
def delivery_dashboard():
    user = session.get('user')
    discord_id = user.get('id')
    
    col_users = Database.get_collection("users")
    col_orders = Database.get_collection("orders")
    
    # বর্তমান ডেলিভারি বয়ের ডিটেইলস নেওয়া (Wallet ও Cash এর হিসাব দেখানোর জন্য)
    current_user = col_users.find_one({"discord_id": discord_id})
    
    # 🔴 Auto-Refresh Logic: শুধুমাত্র Confirmed এবং Out for Delivery অর্ডারগুলো দেখাবে।
    # ডেলিভারি হয়ে গেলে বা ক্যানসেল হলে অটোমেটিক পেজ থেকে সরে যাবে।
    active_orders = list(col_orders.find({
        "status": {"$in": ["Confirmed", "Out for Delivery"]}
    }).sort("_id", -1))
    
    return render_template('delivery-dashboard.html', orders=active_orders, current_user=current_user)


# ==========================================
# 📲 ২. Accept Order & Send OTP
# ==========================================
@delivery_bp.route('/delivery/send_otp/<order_id>', methods=['POST'])
@delivery_required
def send_otp(order_id):
    # ৪-ডিজিটের একটি র‍্যান্ডম OTP জেনারেট করা
    otp = str(random.randint(1000, 9999))
    
    col = Database.get_collection("orders")
    col.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {
            "status": "Out for Delivery",
            "delivery_otp": otp,  # ডেটাবেসে OTP সেভ করে রাখা
            "delivery_partner_id": session.get('user').get('id') # পার্টনারের নাম যুক্ত করা
        }}
    )
    
    # বাস্তবে এটি SMS হিসেবে কাস্টমারের কাছে যাবে। 
    # আপাতত টেস্ট করার জন্য আপনার স্ক্রিনেই OTP দেখিয়ে দিচ্ছি:
    flash(f"Order Accepted! ⚠️ Customer OTP is: {otp}")
    return redirect(url_for('delivery.delivery_dashboard'))


# ==========================================
# ✅ ৩. Verify OTP & Mark Delivered (Wallet Update)
# ==========================================
@delivery_bp.route('/delivery/verify_otp/<order_id>', methods=['POST'])
@delivery_required
def verify_otp(order_id):
    entered_otp = request.form.get('otp')
    
    col_orders = Database.get_collection("orders")
    col_users = Database.get_collection("users")
    
    order = col_orders.find_one({"_id": ObjectId(order_id)})
    
    if order and order.get('delivery_otp') == entered_otp:
        # OTP মিলে গেলে স্ট্যাটাস Delivered হবে
        col_orders.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"status": "Delivered"}}
        )
        
        # 💰 Wallet & Cash in Hand আপডেট করা 
        order_price = float(order.get('total_price', 0))
        delivery_earning = 40.0 # ধরে নিচ্ছি প্রতি ডেলিভারিতে সে 40 টাকা পাবে (আপনি চাইলে বদলাতে পারেন)
        
        col_users.update_one(
            {"discord_id": session.get('user').get('id')},
            {"$inc": {
                "wallet_balance": delivery_earning, # ডেলিভারি বয়ের ইনকাম
                "cash_in_hand": order_price # কাস্টমারের কাছ থেকে নেওয়া টাকা (COD)
            }}
        )
        
        flash("OTP Verified! Parcel marked as Delivered. ✅")
    else:
        # OTP ভুল দিলে এরর মেসেজ
        flash("❌ Invalid OTP! Please check and enter again.")
        
    return redirect(url_for('delivery.delivery_dashboard'))


# ==========================================
# ⚠️ ৪. Report Failed / Cancel Delivery
# ==========================================
@delivery_bp.route('/delivery/report_failed/<order_id>', methods=['POST'])
@delivery_required
def report_failed_delivery(order_id):
    reason = request.form.get('fail_reason')
    col = Database.get_collection("orders")
    
    if col is not None:
        # ডেলিভারি ফেইল হলে স্ট্যাটাস Returned হবে
        col.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {
                "status": "Returned",
                "return_reason": reason
            }}
        )
        
    flash(f"Order Cancelled/Returned. Reason: {reason}")
    return redirect(url_for('delivery.delivery_dashboard'))
    
