import os
import uuid
import cloudinary
import cloudinary.uploader
import cloudinary.api
from flask import Blueprint, render_template, request, redirect, session, flash, url_for, abort
from database import Database
from datetime import datetime
from bson import ObjectId
from functools import wraps
from werkzeug.utils import secure_filename

seller_bp = Blueprint('seller', __name__)

# ==========================================
# Cloudinary Configuration
# ==========================================
cloudinary.config(
    cloud_name="dsr2twtwd",
    api_key="783482566841957",
    api_secret="pb_LkF6p4FQBD2fwv4Yp8j-qIUI"
)

# ==========================================
# File Upload Configuration & Logic
# ==========================================
ALLOWED_EXTENSIONS_IMG = {'png', 'jpg', 'jpeg', 'webp'}
ALLOWED_EXTENSIONS_VID = {'mp4', 'mkv', 'mov'}

def allowed_file(filename, is_video=False):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if is_video:
        return ext in ALLOWED_EXTENSIONS_VID
    return ext in ALLOWED_EXTENSIONS_IMG

def upload_to_cloudinary(file_obj, folder_name="inwear_products"):
    """Uploads file to Cloudinary and returns the secure live URL."""
    response = cloudinary.uploader.upload(
        file_obj,
        folder=folder_name,
        resource_type="auto" # Automatically detects if it's an image or video
    )
    return response.get('secure_url')

# ==========================================
# Seller Authentication Security
# ==========================================
def seller_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user.get('role') not in ['seller', 'owner']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# 1. Seller Dashboard
# ==========================================
@seller_bp.route('/seller-dashboard')
@seller_required
def seller_dashboard():
    user = session.get('user')
    discord_id = str(user.get('id'))
    
    col_orders = Database.get_collection("orders")
    col_products = Database.get_collection("products")
    col_users = Database.get_collection("users")
    
    current_user = col_users.find_one({"discord_id": discord_id})
    my_products = list(col_products.find({"seller_id": discord_id}).sort("_id", -1))
    
    active_orders = list(col_orders.find({
        "seller_id": discord_id,
        "status": {"$in": ["Confirmed", "Ready for Pickup", "Assigned", "Out for Delivery"]}
    }).sort("_id", -1))
    
    return render_template('seller-dashboard.html', 
                           orders=active_orders, 
                           products=my_products, 
                           current_user=current_user)

# ==========================================
# 2. Seller Wallet Page
# ==========================================
@seller_bp.route('/seller/wallet')
@seller_required
def seller_wallet():
    user = session.get('user')
    col = Database.get_collection("users")
    seller_data = col.find_one({"discord_id": str(user['id'])})
    
    withdraw_col = Database.get_collection("withdrawals")
    history = list(withdraw_col.find({"seller_id": str(user['id'])}).sort("_id", -1))

    return render_template('seller_wallet.html', seller=seller_data, withdrawals=history)

# ==========================================
# 3. Add New UPI ID
# ==========================================
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

# ==========================================
# 4. Set Default UPI
# ==========================================
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

# ==========================================
# 5. Send Withdrawal Request
# ==========================================
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

# ==========================================
# 6. Mark Order Ready for Delivery
# ==========================================
@seller_bp.route('/seller/mark_ready/<order_id>', methods=['POST'])
@seller_required
def mark_order_ready(order_id):
    col_orders = Database.get_collection("orders")
    if col_orders is not None:
        col_orders.update_one({"_id": ObjectId(order_id)}, {"$set": {"status": "Ready for Pickup"}})
        flash("📦 Order packed and marked ready! Local delivery boys have been notified.")
    return redirect('/seller-dashboard')

# ==========================================
# 7. ADD NEW PRODUCT (Cloudinary Upload Logic)
# ==========================================
@seller_bp.route('/add-product', methods=['GET', 'POST'])
@seller_required
def add_product():
    if request.method == 'POST':
        user = session.get('user')
        col_products = Database.get_collection("products")
        col_users = Database.get_collection("users")
        
        seller_profile = col_users.find_one({"discord_id": str(user['id'])})
        store_name = seller_profile.get('application_data', {}).get('store_name', 'My Store') if seller_profile else 'My Store'

        name = request.form.get('product_name')
        price = float(request.form.get('product_price', 0))
        mrp = float(request.form.get('product_mrp', price))
        stock = int(request.form.get('product_stock', 1))
        category = request.form.get('product_category')
        sizes = request.form.getlist('sizes')
        details = request.form.get('product_details')
        description = request.form.get('product_description')
        tags = [t.strip() for t in request.form.get('product_tags', '').split(',')]
        return_policy = request.form.get('return_policy')
        insure_status = request.form.get('apply_insure', 'No')

        # Upload Images to Cloudinary
        image_urls = []
        if 'product_images' in request.files:
            files = request.files.getlist('product_images')
            for file in files[:3]:
                if file and allowed_file(file.filename):
                    live_url = upload_to_cloudinary(file, folder_name="inwear_product_images")
                    image_urls.append(live_url)

        # Upload Video to Cloudinary
        video_url = ""
        if 'product_video' in request.files:
            file = request.files['product_video']
            if file and allowed_file(file.filename, is_video=True):
                video_url = upload_to_cloudinary(file, folder_name="inwear_product_videos")

        new_product = {
            "seller_id": str(user['id']),
            "store_name": store_name,
            "name": name,
            "price": price,
            "mrp": mrp,
            "stock": stock,
            "sizes": sizes,
            "category": category,
            "details": details,
            "description": description,
            "tags": tags,
            "return_policy": return_policy,
            "images": image_urls,          
            "image": image_urls[0] if image_urls else "", 
            "video": video_url,
            "status": "Approved",          
            "inwear_insure": insure_status,
            "created_at": datetime.now()
        }
        
        col_products.insert_one(new_product)
        
        if insure_status == "Pending Approval":
            flash("✅ Product published! Verification request sent.", "success")
        else:
            flash("✅ Product successfully published!", "success")
            
        return redirect('/seller-dashboard')
        
    return render_template('add_product.html')

# ==========================================
# 8. Delete Seller Product
# ==========================================
@seller_bp.route('/seller/delete-product/<product_id>', methods=['POST'])
@seller_required
def delete_seller_product(product_id):
    user = session.get('user')
    col_products = Database.get_collection("products")
    if col_products is not None:
        result = col_products.delete_one({"_id": ObjectId(product_id), "seller_id": str(user['id'])})
        if result.deleted_count > 0:
            flash("🗑️ Product deleted successfully!")
        else:
            flash("❌ Product not found or permission denied.")
    return redirect('/seller/products')

# ==========================================
# 9. Edit Seller Product
# ==========================================
@seller_bp.route('/seller/edit-product/<product_id>', methods=['GET', 'POST'])
@seller_required
def edit_seller_product(product_id):
    user = session.get('user')
    col_products = Database.get_collection("products")
    
    product = col_products.find_one({"_id": ObjectId(product_id), "seller_id": str(user['id'])})
    if not product:
        flash("❌ Product not found.")
        return redirect('/seller/products')
        
    if request.method == 'POST':
        updated_data = {
            "name": request.form.get('product_name'),
            "price": float(request.form.get('product_price', 0)),
            "mrp": float(request.form.get('product_mrp', 0)),
            "stock": int(request.form.get('product_stock', 1)),
            "details": request.form.get('product_details'),
            "description": request.form.get('product_description')
        }
        col_products.update_one({"_id": ObjectId(product_id)}, {"$set": updated_data})
        flash("✅ Product updated successfully!")
        return redirect('/seller/products')
        
    return render_template('edit_product.html', product=product)

# ==========================================
# 10. Dedicated Seller Products Page
# ==========================================
@seller_bp.route('/seller/products')
@seller_required
def seller_products_page():
    user = session.get('user')
    discord_id = str(user.get('id'))
    
    col_products = Database.get_collection("products")
    col_users = Database.get_collection("users")
    
    current_user = col_users.find_one({"discord_id": discord_id})
    my_products = list(col_products.find({"seller_id": discord_id}).sort("_id", -1))
    
    return render_template('seller_products.html', products=my_products, current_user=current_user)

# ==========================================
# 11. Print Invoice / Bill
# ==========================================
@seller_bp.route('/seller/print-bill/<order_id>')
@seller_required
def print_bill(order_id):
    col_orders = Database.get_collection("orders")
    order_data = col_orders.find_one({"_id": ObjectId(order_id)})
    if not order_data:
        return "Order not found", 404
    return render_template('invoice.html', order=order_data)
        
