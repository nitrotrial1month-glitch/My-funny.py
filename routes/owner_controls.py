from flask import Blueprint, redirect, request
from database import Database
from routes.auth import get_current_user, role_required
from bson.objectid import ObjectId

# 🔴 নতুন ব্লুপ্রিন্ট
owner_controls_bp = Blueprint('owner_controls', __name__)

# ==========================================
# 📦 PRODUCT CONTROLS
# ==========================================

# ১. প্রোডাক্ট ভেরিফাই করা (Live)
@owner_controls_bp.route('/owner/verify-product/<product_id>', methods=['POST'])
@role_required('owner')
def verify_product(product_id):
    db_products = Database.get_collection("products")
    if db_products is not None:
        db_products.update_one({"_id": ObjectId(product_id)}, {"$set": {"status": "Live"}})
    return redirect('/owner-dashboard')

# ২. প্রোডাক্ট আনভেরিফাই করা (Pending এ পাঠানো)
@owner_controls_bp.route('/owner/unverify-product/<product_id>', methods=['POST'])
@role_required('owner')
def unverify_product(product_id):
    db_products = Database.get_collection("products")
    if db_products is not None:
        db_products.update_one({"_id": ObjectId(product_id)}, {"$set": {"status": "Pending"}})
    return redirect('/owner-dashboard')

# ৩. যেকোনো প্রোডাক্ট সরাসরি ডিলিট করা
@owner_controls_bp.route('/owner/delete-product/<product_id>', methods=['POST'])
@role_required('owner')
def delete_product(product_id):
    db_products = Database.get_collection("products")
    if db_products is not None:
        db_products.delete_one({"_id": ObjectId(product_id)})
    return redirect('/owner-dashboard')


# ==========================================
# 🚫 SELLER CONTROLS
# ==========================================

# ৪. সেলারকে ব্লক/ব্যান করা (রোল কেড়ে নেওয়া)
@owner_controls_bp.route('/owner/block-seller', methods=['POST'])
@role_required('owner')
def block_seller():
    seller_email = request.form.get('seller_email').strip()
    db_users = Database.get_collection("users")
    db_products = Database.get_collection("products")
    
    if db_users is not None:
        user = db_users.find_one({"email": seller_email})
        if user:
            # সেলার থেকে সাধারণ ইউজার বানিয়ে দেওয়া (Role কেড়ে নেওয়া)
            db_users.update_one({"email": seller_email}, {"$set": {"role": "user", "is_banned": True}})
            
            # সেলার ব্যান হওয়ার সাথে সাথে তার সব প্রোডাক্ট অটো-ডিলিট করে দেওয়া
            if db_products is not None:
                db_products.delete_many({"seller_id": str(user.get('discord_id'))})
                
    return redirect('/owner-dashboard')
  
