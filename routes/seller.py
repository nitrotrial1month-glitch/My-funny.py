import os
from flask import Blueprint, render_template, request, redirect, session, flash, url_for, abort
from database import Database
from datetime import datetime
from bson import ObjectId
from functools import wraps
from werkzeug.utils import secure_filename
from routes.auth import role_required

seller_bp = Blueprint('seller', __name__)

# ==========================================
# 📂 Image & Video Upload Configuration
# ==========================================
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS_IMG = {'png', 'jpg', 'jpeg', 'webp'}
ALLOWED_EXTENSIONS_VID = {'mp4', 'mkv', 'mov'}

def allowed_file(filename, is_video=False):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if is_video:
        return ext in ALLOWED_EXTENSIONS_VID
    return ext in ALLOWED_EXTENSIONS_IMG

# ==========================================
# 🔐 সেলার অথেন্টিকেশন সিকিউরিটি
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
# 📊 ১. Seller Dashboard (কাস্টমারের ডিটেইলস ও সেলস)
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
    
    # সেলারের আপলোড করা সব প্রোডাক্ট
    my_products = list(col_products.find({"seller_id": discord_id}).sort("_id", -1))
    
    # কাস্টমারদের করা নতুন অর্ডার (যেগুলো এখনও ডেলিভারি হয়নি)
    active_orders = list(col_orders.find({
        "seller_id": discord_id,
        "status": {"$in": ["Confirmed", "Ready for Pickup", "Assigned", "Out for Delivery"]}
    }).sort("_id", -1))
    
    return render_template('seller-dashboard.html', 
                           orders=active_orders, 
                           products=my_products, 
                           current_user=current_user)

# ==========================================
# 💰 ২. সেলারের ওয়ালেট পেজ
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
# 🏦 ৩. নতুন UPI ID অ্যাড করা
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
# ⭐ ৪. ডিফল্ট UPI সেট করা
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
# 💸 ৫. উইথড্র রিকোয়েস্ট পাঠানো
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
# 📦 ৬. অর্ডার প্যাক করে ডেলিভারির জন্য রেডি করা
# ==========================================
@seller_bp.route('/seller/mark_ready/<order_id>', methods=['POST'])
@seller_required
def mark_order_ready(order_id):
    col_orders = Database.get_collection("orders")
    
    if col_orders is not None:
        col_orders.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"status": "Ready for Pickup"}}
        )
        flash("📦 Order packed and marked ready! Local delivery boys have been notified.")
        
    return redirect('/seller-dashboard')

# ==========================================
# 👕 ৭. ADD NEW PRODUCT (Premium Upload Logic)
# ==========================================
@seller_bp.route('/add-product', methods=['GET', 'POST'])
@seller_required
def add_product():
    if request.method == 'POST':
        user = session.get('user')
        col_products = Database.get_collection("products")
        col_users = Database.get_collection("users")
        
        # সেলারের প্রোফাইল থেকে স্টোরের নাম বের করা
        seller_profile = col_users.find_one({"discord_id": str(user['id'])})
        store_name = seller_profile.get('application_data', {}).get('store_name', 'My Store') if seller_profile else 'My Store'

        # টেক্সট ফিল্ডগুলো রিসিভ করা
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
        insure_status = request.form.get('apply_insure', 'No') # Flipkart Assured style badge

        # 📸 ৩টি ছবি আপলোড লজিক
        image_urls = []
        if 'product_images' in request.files:
            files = request.files.getlist('product_images')
            for file in files[:3]: # সর্বোচ্চ ৩টি ছবি
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    if not os.path.exists(UPLOAD_FOLDER):
                        os.makedirs(UPLOAD_FOLDER)
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(filepath)
                    image_urls.append(f"static/uploads/{filename}")

        # 🎥 ভিডিও আপলোড লজিক
        video_url = ""
        if 'product_video' in request.files:
            file = request.files['product_video']
            if file and allowed_file(file.filename, is_video=True):
                filename = secure_filename(file.filename)
                if not os.path.exists(UPLOAD_FOLDER):
                    os.makedirs(UPLOAD_FOLDER)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                video_url = f"static/uploads/{filename}"

        # ডেটাবেস ডকুমেন্ট তৈরি
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
            "image": image_urls[0] if image_urls else "", # Main thumbnail
            "video": video_url,
            "status": "Approved",          
            "inwear_insure": insure_status,
            "created_at": datetime.now()
        }
        
        col_products.insert_one(new_product)
        
        if insure_status == "Pending Approval":
            flash("✅ Product published! Verification request sent to Owner Dashboard.", "success")
        else:
            flash("✅ Product successfully published!", "success")
            
        return redirect('/seller-dashboard')
        
    return render_template('add_product.html')
    
# ==========================================
# 👕 ১০. সেলারের ডেডিকেটেড প্রোডাক্টস পেজ (Manage Products)
# ==========================================
@seller_bp.route('/seller/products')
@seller_required
def seller_products_page():
    user = session.get('user')
    discord_id = str(user.get('id'))
    
    col_products = Database.get_collection("products")
    col_users = Database.get_collection("users")
    
    current_user = col_users.find_one({"discord_id": discord_id})
    
    # সেলারের আপলোড করা সব প্রোডাক্ট (নতুন থেকে পুরনো ক্রমে)
    my_products = list(col_products.find({"seller_id": discord_id}).sort("_id", -1))
    
    return render_template('seller_products.html', 
                           products=my_products, 
                           current_user=current_user)
    
