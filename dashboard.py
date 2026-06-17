from flask import Blueprint, render_template, request, redirect, url_for, session
from database import Database

dashboard_bp = Blueprint('dashboard', __name__)

# --- Seller Dashboard ---
@dashboard_bp.route('/seller', methods=['GET', 'POST'])
def seller_dashboard():
    user = session.get('user')
    # নিরাপত্তা চেক: যদি ইউজার লগইন না থাকে বা সেলার/ওনার না হয়
    if not user or not (user.get('is_seller') or user.get('is_owner')):
        return redirect(url_for('home'))

    if request.method == 'POST':
        # প্রোডাক্ট যোগ করার লজিক
        Database.add_product(
            name=request.form.get('name'),
            desc=request.form.get('desc'),
            price=request.form.get('price'),
            image=request.form.get('image')
        )
        return redirect(url_for('dashboard.seller_dashboard'))

    products = Database.get_all_products()
    return render_template('seller_dashboard.html', products=products)


# --- Owner Dashboard (Master Control) ---
@dashboard_bp.route('/owner', methods=['GET', 'POST'])
def owner_dashboard():
    user = session.get('user')
    # কড়া নিরাপত্তা চেক: শুধু ওনারই এই পেজে ঢুকতে পারবে
    if not user or not user.get('is_owner'):
        return redirect(url_for('home'))

    # ওনার সেটিংস আপডেট
    if request.method == 'POST':
        new_config = {
            "prefix": request.form.get('prefix'),
            "status": request.form.get('status')
        }
        Database.save_config(new_config)
    
    current_config = Database.get_config()
    # ওনার প্যানেলের জন্য সব ইউজারের লিস্ট (যাদের সেলার বানানো বা রিমুভ করা যায়)
    all_users = Database.get_all_users() 
    
    return render_template('owner_dashboard.html', config=current_config, all_users=all_users)


# --- User Management (Only for Owner) ---
@dashboard_bp.route('/toggle_seller/<discord_id>', methods=['POST'])
def toggle_seller(discord_id):
    user = session.get('user')
    # নিরাপত্তা: চেক করা হচ্ছে ইউজার ওনার কিনা
    if not user or not user.get('is_owner'):
        return "Access Denied!", 403

    # ডাটাবেসে সেলার রোল টগল করা (সেলার থাকলে সরিয়ে দেওয়া, না থাকলে দেওয়া)
    Database.toggle_user_seller_access(discord_id)
    
    return redirect(url_for('dashboard.owner_dashboard'))
    
