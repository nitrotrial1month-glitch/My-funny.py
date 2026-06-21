import os
from flask import Blueprint, render_template, request, session, redirect, jsonify
from database import Database
from bson.objectid import ObjectId

# 🔴 এই লাইনটি মিসিং থাকার কারণেই আপনার সার্ভার ক্র্যাশ করেছিল!
orders_bp = Blueprint('orders', __name__)

# ==========================================
# 📋 ১. My Orders Page Route
# ==========================================
@orders_bp.route('/orders')
def my_orders():
    user = session.get('user')
    if not user: 
        return redirect('/account')
    
    col = Database.get_collection("orders")
    user_orders = []
    
    if col is not None:
        query = {"username": user.get('username')}
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
            col.update_one(
                {"_id": ObjectId(order_id), "username": user.get('username')}, 
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
            col.update_one(
                {"_id": ObjectId(order_id), "username": user.get('username')}, 
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
            order = col.find_one({"_id": ObjectId(order_id), "username": user.get('username')})
        except Exception as e:
            print(f"Fetch Details Database Error: {e}")
            
    if not order:
        return "<h1>Order not found!</h1><br><a href='/orders'>Go Back</a>", 404
        
    return render_template('order_details.html', order=order, user=user)
    
