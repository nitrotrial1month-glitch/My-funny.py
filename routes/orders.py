import os
from flask import Blueprint, render_template, request, session, redirect, jsonify
from database import Database
from bson.objectid import ObjectId

orders_bp = Blueprint('orders', __name__)

# ==========================================
# 📋 ১. My Orders Page Route (১০০% ফিক্সড)
# ==========================================
@orders_bp.route('/orders')
def my_orders():
    user = session.get('user')
    if not user: 
        return redirect('/account')
    
    col = Database.get_collection("orders")
    user_orders = []
    
    if col is not None:
        # 🔴 UPDATE: সেশন থেকে WBM_U_ID নেওয়া হচ্ছে
        WBM_U_ID = str(user.get('id')) 
        
        # 🔴 স্মার্ট কোয়েরি: এখন যেহেতু ডাটাবেস ফ্রেশ, তাই সরাসরি WBM_U_ID দিয়ে খুঁজবে
        query = {
            "$or": [
                {"user_id": WBM_U_ID},       # Checkout.py সাধারণত user_id ফিল্ডে সেভ করে
                {"WBM_U_ID": WBM_U_ID}       # সেফটির জন্য ডাইরেক্ট WBM_U_ID ফিল্ডও চেক করা হলো
            ]
        }
        # নতুন অর্ডারগুলো একদম উপরে দেখানোর জন্য sort করা হলো
        user_orders = list(col.find(query).sort("_id", -1))
        
    return render_template('orders.html', orders=user_orders, user=user)


# ==========================================
# ❌ ২. Cancel Order Route
# ==========================================
@orders_bp.route('/cancel_order/<order_id>')
def cancel_order(order_id):
    user = session.get('user')
    if not user: return redirect('/account')
    
    col = Database.get_collection("orders")
    if col is not None:
        try:
            # 🔴 UPDATE: WBM_U_ID ব্যবহার করে সিকিউরিটি চেক
            WBM_U_ID = str(user.get('id'))
            col.update_one(
                {
                    "_id": ObjectId(order_id), 
                    "$or": [{"user_id": WBM_U_ID}, {"WBM_U_ID": WBM_U_ID}]
                }, 
                {"$set": {"status": "Cancelled"}}
            )
        except Exception as e:
            print(f"Cancel Order Database Error: {e}")
            
    return redirect('/orders')


# ==========================================
# ↩️ ৩. Return/Replace Route
# ==========================================
@orders_bp.route('/return_order/<order_id>')
def return_order(order_id):
    user = session.get('user')
    if not user: return redirect('/account')
    
    col = Database.get_collection("orders")
    if col is not None:
        try:
            # 🔴 UPDATE: WBM_U_ID ব্যবহার করে সিকিউরিটি চেক
            WBM_U_ID = str(user.get('id'))
            col.update_one(
                {
                    "_id": ObjectId(order_id), 
                    "$or": [{"user_id": WBM_U_ID}, {"WBM_U_ID": WBM_U_ID}]
                }, 
                {"$set": {"status": "Return Requested"}}
            )
        except Exception as e:
            print(f"Return Order Database Error: {e}")
            
    return redirect('/orders')


# ==========================================
# 🔍 ৪. Order Details Route
# ==========================================
@orders_bp.route('/order_details/<order_id>')
def order_details(order_id):
    user = session.get('user')
    if not user: return redirect('/account')
    
    col = Database.get_collection("orders")
    order = None
    
    if col is not None:
        try:
            # 🔴 UPDATE: WBM_U_ID ব্যবহার করে আইডি দিয়ে অর্ডার ডিটেইলস খুঁজে বের করা
            WBM_U_ID = str(user.get('id'))
            order = col.find_one({
                "_id": ObjectId(order_id), 
                "$or": [{"user_id": WBM_U_ID}, {"WBM_U_ID": WBM_U_ID}]
            })
        except Exception as e:
            print(f"Fetch Details Database Error: {e}")
            
    if not order:
        return "<h1>Order not found or Unauthorized!</h1><br><a href='/orders'>Go Back</a>", 404
        
    return render_template('order_details.html', order=order, user=user)
    
