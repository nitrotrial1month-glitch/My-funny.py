import random
from flask import Blueprint, render_template, session, redirect, abort, url_for, request, flash
from database import Database
from bson import ObjectId
from functools import wraps

delivery_bp = Blueprint('delivery', __name__)

def delivery_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user.get('role') not in ['delivery', 'owner']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# 🚚 ১. Delivery Dashboard (Area-Based Open Pool)
# ==========================================
@delivery_bp.route('/delivery-dashboard')
@delivery_required
def delivery_dashboard():
    user = session.get('user')
    discord_id = str(user.get('id'))
    
    col_users = Database.get_collection("users")
    col_orders = Database.get_collection("orders")
    
    current_user = col_users.find_one({"discord_id": discord_id})
    
    # 📍 ডেলিভারি বয়ের নিজের এলাকা (Area বা Pincode) বের করা
    delivery_boy_area = ""
    if current_user and current_user.get("application_data"):
        delivery_boy_area = current_user["application_data"].get("area", "")

    # 🟢 OPEN POOL LOGIC (FIXED)
    # ১. কাস্টমারের "Confirmed" অর্ডার দেখাবে না, শুধু সেলারের "Ready for Pickup" দেখাবে।
    # ২. এখনও কোনো রাইডার অ্যাসাইন হয়নি এমন অর্ডার খুঁজবে।
    open_pool_query = {
        "status": "Ready for Pickup",
        "$or": [
            {"delivery_partner_id": {"$exists": False}},
            {"delivery_partner_id": ""},
            {"delivery_partner_id": None}
        ]
    }
    
    # ৩. লোকেশন ফিল্টার (১-৬ কিমি লজিক): 
    # ডেলিভারি বয়ের এলাকার নাম দিয়ে সেলারের অ্যাড্রেস বা এরিয়া ম্যাচ করা হচ্ছে
    if delivery_boy_area:
        open_pool_query["$or"].append({"seller_address": {"$regex": delivery_boy_area, "$options": "i"}})
        open_pool_query["$or"].append({"pickup_address": {"$regex": delivery_boy_area, "$options": "i"}})

    available_orders = list(col_orders.find(open_pool_query).sort("_id", -1))
    
    # 📦 MY TASKS: যে অর্ডারগুলো এই ডেলিভারি বয় নিজে Grab করেছে
    my_orders = list(col_orders.find({
        "status": {"$in": ["Assigned", "Out for Delivery", "Delivered (Pending Handover)"]},
        "delivery_partner_id": discord_id
    }).sort("_id", -1))
    
    return render_template('delivery-dashboard.html', 
                           available_orders=available_orders, 
                           my_orders=my_orders, 
                           current_user=current_user)
    

# ==========================================
# 🤝 ২. Self-Assign (Grab Product)
# ==========================================
@delivery_bp.route('/delivery/confirm_job/<order_id>', methods=['POST'])
@delivery_required
def confirm_job(order_id):
    discord_id = str(session.get('user').get('id'))
    col_orders = Database.get_collection("orders")
    
    order = col_orders.find_one({"_id": ObjectId(order_id)})
    
    # যদি প্রোডাক্টটি এখনও পুলে থাকে, তবে নিজের নামে অ্যাসাইন করে নেওয়া
    if order and order.get('status') == 'Ready for Pickup':
        col_orders.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {
                "status": "Assigned",
                "delivery_partner_id": discord_id
            }}
        )
        flash("✅ Task Assigned! Go to the seller shop and scan the parcel.")
    else:
        flash("❌ Order already taken by another delivery boy.", "error")
        
    return redirect(url_for('delivery.delivery_dashboard'))

# ==========================================
# 📷 ৩. Scan Package at Seller Shop
# ==========================================
@delivery_bp.route('/delivery/scan_pickup/<order_id>', methods=['POST'])
@delivery_required
def scan_pickup(order_id):
    col_orders = Database.get_collection("orders")
    otp = str(random.randint(1000, 9999))
    
    # স্ক্যান করার পর স্ট্যাটাস Out for Delivery হবে এবং কাস্টমার OTP জেনারেট হবে
    col_orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {
            "status": "Out for Delivery",
            "delivery_otp": otp
        }}
    )
    flash(f"📷 Scan Successful! Customer OTP is: {otp}")
    return redirect(url_for('delivery.delivery_dashboard'))

# ==========================================
# 🔑 ৪. Verify OTP at Customer's Door
# ==========================================
@delivery_bp.route('/delivery/verify_otp/<order_id>', methods=['POST'])
@delivery_required
def verify_otp(order_id):
    entered_otp = request.form.get('otp')
    col_orders = Database.get_collection("orders")
    
    order = col_orders.find_one({"_id": ObjectId(order_id)})
    
    if order and order.get('delivery_otp') == entered_otp:
        is_online = order.get('payment_method') == 'online'
        new_status = 'Completed' if is_online else 'Delivered (Pending Handover)'
        
        col_orders.update_one({"_id": ObjectId(order_id)}, {"$set": {"status": new_status}})
        
        # অনলাইন পেমেন্ট হলে সরাসরি রাইডারের অ্যাকাউন্টে টাকা ঢুকে যাবে
        if is_online:
            col_users = Database.get_collection("users")
            col_users.update_one(
                {"discord_id": str(session.get('user').get('id'))},
                {"$inc": {"wallet_balance": 40.0}}
            )
            flash("OTP Verified! Order Completed and ₹40 added to your wallet. ✅")
        else:
            flash("OTP Verified! Parcel Delivered. Please complete the Cash Settlement. 💰")
    else:
        flash("❌ Invalid Confirmation Code! Please try again.", "error")
        
    return redirect(url_for('delivery.delivery_dashboard'))

# ==========================================
# 💸 ৫. Handover COD Cash to Seller
# ==========================================
@delivery_bp.route('/delivery/handover/<order_id>', methods=['POST'])
@delivery_required
def cash_handover(order_id):
    col_orders = Database.get_collection("orders")
    col_users = Database.get_collection("users")
    
    order = col_orders.find_one({"_id": ObjectId(order_id)})
    
    if order:
        order_price = float(order.get('total_price', 0))
        # ক্যাশ সেলারকে দেওয়ার পর রাইডারের ওয়ালেট ও ক্যাশ ব্যালেন্স আপডেট
        col_users.update_one(
            {"discord_id": str(session.get('user').get('id'))},
            {"$inc": {
                "wallet_balance": 40.0,
                "cash_in_hand": order_price
            }}
        )
        col_orders.update_one({"_id": ObjectId(order_id)}, {"$set": {"status": "Completed (Cash Settled)"}})
        flash("Cash Handover Confirmed! Task Closed. ✅")
        
    return redirect(url_for('delivery.delivery_dashboard'))

# ==========================================
# ⚠️ ৬. Report Failed Delivery
# ==========================================
@delivery_bp.route('/delivery/report_failed/<order_id>', methods=['POST'])
@delivery_required
def report_failed_delivery(order_id):
    reason = request.form.get('fail_reason')
    col = Database.get_collection("orders")
    if col:
        col.update_one({"_id": ObjectId(order_id)}, {"$set": {"status": "Returned", "return_reason": reason}})
    flash(f"Order Cancelled/Returned. Reason: {reason}")
    return redirect(url_for('delivery.delivery_dashboard'))
    
