import os
from flask import Blueprint, render_template, request, redirect, url_for, session
from database import Database
from werkzeug.utils import secure_filename

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
        image_path = ""
        file = request.files.get('image')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            image_path = f"/static/uploads/{filename}"

        Database.add_product(
            name=request.form.get('name'),
            desc=request.form.get('desc'),
            price=request.form.get('price'),
            image=image_path
        )
        return redirect(url_for('dashboard.seller_dashboard'))

    products = Database.get_all_products()
    return render_template('seller_dashboard.html', products=products)


# --- Owner Master Control ---
@dashboard_bp.route('/owner')
def owner_dashboard():
    user = session.get('user')
    if not user or not user.get('is_owner'):
        return redirect(url_for('home'))

    products = Database.get_all_products()
    all_users = Database.get_all_users()
    
    return render_template('owner_dashboard.html', products=products, all_users=all_users)


# --- Approve Product (Owner Only) ---
@dashboard_bp.route('/approve_product/<product_id>', methods=['POST'])
def approve_product(product_id):
    user = session.get('user')
    if not user or not user.get('is_owner'):
        return "Access Denied", 403
    Database.approve_product(product_id)
    return redirect(url_for('dashboard.owner_dashboard'))


# --- Delete Product ---
@dashboard_bp.route('/delete_product/<product_id>', methods=['POST'])
def delete_product(product_id):
    user = session.get('user')
    if not user or not (user.get('is_seller') or user.get('is_owner')):
        return "Access Denied", 403
    Database.delete_product(product_id)
    # যে পেজ থেকে ডিলিট করেছে, সেখানেই ফেরত পাঠাবে
    return redirect(request.referrer)


# --- Toggle User Role ---
@dashboard_bp.route('/toggle_seller/<discord_id>', methods=['POST'])
def toggle_seller(discord_id):
    user = session.get('user')
    if not user or not user.get('is_owner'):
        return "Access Denied", 403
    Database.toggle_user_seller_access(discord_id)
    return redirect(url_for('dashboard.owner_dashboard'))
    
