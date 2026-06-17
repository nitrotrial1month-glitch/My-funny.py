import os
from flask import Blueprint, render_template, request, redirect, url_for, session
from database import Database
from werkzeug.utils import secure_filename

# ছবি সেভ করার জন্য ফোল্ডার (আপনার প্রজেক্টে 'static/uploads' ফোল্ডারটি অবশ্যই তৈরি করবেন)
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

dashboard_bp = Blueprint('dashboard', __name__)

# --- Seller Dashboard ---
@dashboard_bp.route('/seller', methods=['GET', 'POST'])
def seller_dashboard():
    user = session.get('user')
    if not user or not (user.get('is_seller') or user.get('is_owner')):
        return redirect(url_for('home'))

    if request.method == 'POST':
        # ফাইল হ্যান্ডেলিং
        image_path = ""
        file = request.files.get('image')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            image_path = f"/static/uploads/{filename}"

        # ডাটাবেসে প্রোডাক্ট সেভ করা
        Database.add_product(
            name=request.form.get('name'),
            desc=request.form.get('desc'),
            price=request.form.get('price'),
            image=image_path
        )
        return redirect(url_for('dashboard.seller_dashboard'))

    products = Database.get_all_products()
    return render_template('seller_dashboard.html', products=products)


# --- Owner Dashboard ---
@dashboard_bp.route('/owner', methods=['GET', 'POST'])
def owner_dashboard():
    user = session.get('user')
    if not user or not user.get('is_owner'):
        return redirect(url_for('home'))

    if request.method == 'POST':
        Database.save_config({
            "prefix": request.form.get('prefix'),
            "status": request.form.get('status')
        })
    
    return render_template('owner_dashboard.html', 
                           config=Database.get_config(), 
                           all_users=Database.get_all_users())


# --- Toggle Role ---
@dashboard_bp.route('/toggle_seller/<discord_id>', methods=['POST'])
def toggle_seller(discord_id):
    user = session.get('user')
    if not user or not user.get('is_owner'):
        return "Access Denied!", 403
    Database.toggle_user_seller_access(discord_id)
    return redirect(url_for('dashboard.owner_dashboard'))
    
