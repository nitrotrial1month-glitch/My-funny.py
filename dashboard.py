import os
import traceback
from flask import Blueprint, render_template, request, redirect, session
from database import Database
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

dashboard_bp = Blueprint('dashboard', __name__)

# ================= SELLER DASHBOARD =================
@dashboard_bp.route('/seller', methods=['GET', 'POST'])
def seller_dashboard():
    try:
        user = session.get('user')
        if not user or not isinstance(user, dict) or not (user.get('is_seller') or user.get('is_owner')):
            return redirect('/')

        if request.method == 'POST':
            image_path = ""
            file = request.files.get('image')
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                image_path = f"/static/uploads/{filename}"

            # 💡 ফিক্স করা হয়েছে: id এবং discord_id দুটোই চেক করবে
            seller_discord_id = user.get('discord_id') or user.get('id')

            Database.add_product(
                name=request.form.get('name'),
                desc=request.form.get('desc'),
                price=request.form.get('price'),
                image=image_path,
                is_owner=user.get('is_owner', False),
                seller_id=seller_discord_id  # <--- এই আইডিটি ডাটাবেসে পাঠানো হচ্ছে
            )
            return redirect('/seller')

        products = Database.get_all_products()
        return render_template('seller_dashboard.html', products=products, user=user)
    
    except Exception as e:
        return f"<div style='padding:20px; font-family:sans-serif;'><h2 style='color:#cc0000;'>⚠️ Dashboard Error</h2><p><b>Error:</b> {str(e)}</p><pre style='background:#f4f4f4; padding:15px; border-radius:5px; overflow-x:auto;'>{traceback.format_exc()}</pre></div>"


# ================= OWNER MASTER DASHBOARD =================
@dashboard_bp.route('/owner', methods=['GET', 'POST'])
def owner_dashboard():
    try:
        user = session.get('user')
        if not user or not isinstance(user, dict) or not user.get('is_owner'):
            return redirect('/')

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
                image=image_path,
                is_owner=True 
            )
            return redirect('/owner')

        products = Database.get_all_products()
        all_users = Database.get_all_users()
        
        return render_template('owner_dashboard.html', products=products, all_users=all_users, user=user)

    except Exception as e:
        return f"<div style='padding:20px; font-family:sans-serif;'><h2 style='color:#cc0000;'>⚠️ Dashboard Error</h2><p><b>Error:</b> {str(e)}</p><pre style='background:#f4f4f4; padding:15px; border-radius:5px; overflow-x:auto;'>{traceback.format_exc()}</pre></div>"


# ================= PRODUCT MANAGEMENT =================
@dashboard_bp.route('/approve_product/<product_id>', methods=['POST'])
def approve_product(product_id):
    user = session.get('user')
    if not user or not isinstance(user, dict) or not user.get('is_owner'):
        return "Access Denied", 403
    
    Database.approve_product(product_id)
    return redirect('/owner')


@dashboard_bp.route('/delete_product/<product_id>', methods=['POST'])
def delete_product(product_id):
    user = session.get('user')
    if not user or not isinstance(user, dict) or not (user.get('is_seller') or user.get('is_owner')):
        return "Access Denied", 403
        
    Database.delete_product(product_id)
    return redirect(request.referrer or '/owner')


# ================= ROLE MANAGEMENT =================
@dashboard_bp.route('/toggle_seller/<discord_id>', methods=['POST'])
def toggle_seller(discord_id):
    user = session.get('user')
    if not user or not isinstance(user, dict) or not user.get('is_owner'):
        return "Access Denied", 403
    Database.toggle_user_seller_access(discord_id)
    return redirect('/owner')
    
