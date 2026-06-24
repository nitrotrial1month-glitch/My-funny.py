from flask import Blueprint, redirect, request, flash, session
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
        flash("✅ Product successfully verified and is now Live.")
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
        flash("🗑️ Product deleted successfully.")
    return redirect('/owner-dashboard')

# 🔴 NEW: ৪. ইনসিওর (Insure) ব্যাজ অ্যাপ্রুভ করা
@owner_controls_bp.route('/owner/verify-insure/<product_id>', methods=['POST'])
@role_required('owner')
def verify_insure_badge(product_id):
    db_products = Database.get_collection("products")
    if db_products is not None:
        # স্ট্যাটাস 'Verified' করে দিলে HTML-এ ব্যাজ শো করবে
        db_products.update_one({"_id": ObjectId(product_id)}, {"$set": {"inwear_insure": "Verified"}})
        flash("🏅 Insure Badge successfully added to the product.")
    return redirect('/owner-dashboard')


# ==========================================
# 🚫 SELLER CONTROLS
# ==========================================

# ৫. সেলারকে ব্লক/ব্যান করা (রোল কেড়ে নেওয়া)
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
            # 'discord_id' এর বদলে 'inwear_id' বা যে আইডি দিয়ে সেলার সেভ হয় সেটি ইউজ করা ভালো
            seller_identifier = user.get('inwear_id') or user.get('discord_id')
            if db_products is not None and seller_identifier:
                db_products.delete_many({"seller_id": str(seller_identifier)})
            
            flash(f"🚫 Seller {seller_email} has been blocked and their products removed.")
        else:
            flash(f"❌ Seller with email {seller_email} not found.", "error")
                
    return redirect('/owner-dashboard')
  
# ==========================================
# 🗑️ GLOBAL PRODUCT DELETE (By ID or Name)
# ==========================================
@owner_controls_bp.route('/owner/delete-product-global', methods=['POST'])
@role_required('owner')
def delete_product_global():
    query = request.form.get('product_query', '').strip()
    db_products = Database.get_collection("products")
    
    if db_products is not None and query:
        try:
            # যদি ইনপুটটি ২৪ ক্যারেক্টারের হয় (মানে এটি একটি MongoDB Object ID)
            if len(query) == 24 and all(c in '0123456789abcdefABCDEF' for c in query):
                result = db_products.delete_one({"_id": ObjectId(query)})
                if result.deleted_count > 0:
                    flash(f"🗑️ Product with ID {query} deleted.")
                else:
                    flash("❌ Product ID not found.", "error")
            else:
                # যদি ইনপুটটি নাম হয়, তবে নামের সাথে মিলিয়ে ডিলিট করবে (Case Insensitive)
                result = db_products.delete_many({"name": {"$regex": f"^{query}$", "$options": "i"}})
                if result.deleted_count > 0:
                    flash(f"🗑️ {result.deleted_count} product(s) named '{query}' deleted.")
                else:
                    flash(f"❌ No products found with name '{query}'.", "error")
        except Exception as e:
            flash(f"❌ Error deleting product: {str(e)}", "error")
            
    return redirect('/owner-dashboard')
            
