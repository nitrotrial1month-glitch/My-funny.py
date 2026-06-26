import random
from flask import Blueprint, render_template, session, redirect, abort, url_for, request, flash
from database import Database
from bson import ObjectId
from functools import wraps

delivery_bp = Blueprint('delivery', __name__)

# অথেন্টিকেশন চেক
def delivery_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user.get('role') not in ['delivery', 'owner']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# 🚚 ১. Delivery Dashboard (Main Page)
# ==========================================
@delivery_bp.route('/delivery-dashboard')
@delivery_required
def delivery_dashboard():
    user = session.get('user')
    WBM_U_ID = str(user.get('id'))
    
    col_orders = Database.get_collection("orders")
    col_users = Database.get_collection("users")
    
    current_user = col_users.find_one({"WBM_U_ID": WBM_U_ID})
    
    # ওপেন পুল: যে অর্ডারগুলোর স্ট্যাটাস 'Ready for Pickup' এবং এখনো কাউকে অ্যাসাইন করা হয়নি
    available_orders = list(col_orders.find({
        "status": "Ready for Pickup",
        "$or": [{"delivery_partner_id": {"$exists": False}}, {"delivery_partner_id": ""}, {"delivery_partner_id": None}]
    }).sort("_id", -1))
    
    # মাই টাস্ক: এই ডেলিভারি পার্টনারের নিজের অর্ডার
    my_orders = list(col_orders.find({
        "delivery_partner_id": WBM_U_ID,
        "status": {"$in": ["Assigned", "Out for Delivery", "Delivered (Pending Handover)"]}
    }).sort("_id", -1))
    
    return render_template('delivery_dashboard.html', 
                           available_orders=available_orders, 
                           my_orders=my_orders, 
                           current_user=current_user)

# ==========================================
# 🤝 ২. Confirm/Grab Job
# ==========================================
@delivery_bp.route('/delivery/confirm_job/<order_id>', methods=['POST'])
@delivery_required
def confirm_job(order_id):
    WBM_U_ID = str(session.get('user').get('id'))
    col_orders = Database.get_collection("orders")
    
    # আইডি ম্যাচিং
    query = {"_id": ObjectId(order_id)} if len(order_id) == 24 else {"WBM_O_ID": order_id}
    
    col_orders.update_one(query, {"$set": {"status": "Assigned", "delivery_partner_id": WBM_U_ID}})
    flash("✅ Task Assigned! Go to the shop.")
    return redirect(url_for('delivery.delivery_dashboard'))

# ==========================================
# 📷 ৩. Scan & Pickup
# ==========================================
@delivery_bp.route('/delivery/scan_pickup/<order_id>', methods=['POST'])
@delivery_required
def scan_pickup(order_id):
    col_orders = Database.get_collection("orders")
    otp = str(random.randint(1000, 9999))
    
    query = {"_id": ObjectId(order_id)} if len(order_id) == 24 else {"WBM_O_ID": order_id}
    col_orders.update_one(query, {"$set": {"status": "Out for Delivery", "delivery_otp": otp}})
    
    flash(f"📷 Scan Successful! Customer OTP: {otp}")
    return redirect(url_for('delivery.delivery_dashboard'))

# ==========================================
# 🔑 ৪. Verify OTP & Complete
# ==========================================
@delivery_bp.route('/delivery/verify_otp/<order_id>', methods=['POST'])
@delivery_required
def verify_otp(order_id):
    entered_otp = request.form.get('otp')
    col_orders = Database.get_collection("orders")
    col_users = Database.get_collection("users")
    
    query = {"_id": ObjectId(order_id)} if len(order_id) == 24 else {"WBM_O_ID": order_id}
    order = col_orders.find_one(query)
    
    if order and order.get('delivery_otp') == entered_otp:
        is_online = order.get('payment_method') == 'Online'
        new_status = 'Completed' if is_online else 'Delivered (Pending Handover)'
        
        col_orders.update_one(query, {"$set": {"status": new_status}})
        
        if is_online:
            col_users.update_one({"WBM_U_ID": str(session.get('user').get('id'))}, {"$inc": {"wallet_balance": 40.0}})
            flash("✅ Order Completed! ₹40 added to wallet.")
        else:
            flash("✅ OTP Verified! Please complete cash settlement.")
    else:
        flash("❌ Invalid OTP!", "error")
        
    return redirect(url_for('delivery.delivery_dashboard'))

# ==========================================
# 💸 ৫. Handover Cash (COD)
# ==========================================
@delivery_bp.route('/delivery/handover/<order_id>', methods=['POST'])
@delivery_required
def cash_handover(order_id):
    col_orders = Database.get_collection("orders")
    col_users = Database.get_collection("users")
    
    query = {"_id": ObjectId(order_id)} if len(order_id) == 24 else {"WBM_O_ID": order_id}
    order = col_orders.find_one(query)
    
    if order:
        order_price = float(order.get('total_price', 0))
        col_users.update_one(
            {"WBM_U_ID": str(session.get('user').get('id'))},
            {"$inc": {"wallet_balance": 40.0, "cash_in_hand": order_price}}
        )
        col_orders.update_one(query, {"$set": {"status": "Completed (Cash Settled)"}})
        flash("🤝 Cash Handover Confirmed!")
        
    return redirect(url_for('delivery.delivery_dashboard'))

# ==========================================
# ⚠️ ৬. Report Failed Delivery
# ==========================================
@delivery_bp.route('/delivery/report_failed/<order_id>', methods=['POST'])
@delivery_required
def report_failed_delivery(order_id):
    reason = request.form.get('fail_reason')
    query = {"_id": ObjectId(order_id)} if len(order_id) == 24 else {"WBM_O_ID": order_id}
    
    Database.get_collection("orders").update_one(query, {"$set": {"status": "Returned", "return_reason": reason}})
    flash(f"⚠️ Report Filed. Reason: {reason}")
    return redirect(url_for('delivery.delivery_dashboard'))
    
