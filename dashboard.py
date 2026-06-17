from flask import Blueprint, render_template, request, redirect, url_for, session
from database import Database # আপনার ডাটাবেস ফাইলটি এখানে ইমপোর্ট করুন

dashboard_bp = Blueprint('dashboard', __name__)

# সেলার ড্যাশবোর্ড
@dashboard_bp.route('/seller', methods=['GET', 'POST'])
def seller_dashboard():
    user = session.get('user')
    if not user or not user.get('is_seller'):
        return redirect(url_for('home')) # সেলার না হলে হোমে ফেরত পাঠাবে

    if request.method == 'POST':
        # এখানে প্রোডাক্ট অ্যাড করার ডাটাবেস ফাংশনটি কল হবে
        Database.add_product(
            name=request.form.get('name'),
            desc=request.form.get('desc'),
            price=request.form.get('price'),
            image=request.form.get('image')
        )
        return redirect(url_for('dashboard.seller_dashboard'))

    products = Database.get_all_products()
    return render_template('seller_dashboard.html', products=products)

# ওনার ড্যাশবোর্ড
@dashboard_bp.route('/owner', methods=['GET', 'POST'])
def owner_dashboard():
    user = session.get('user')
    if not user or not user.get('is_owner'):
        return redirect(url_for('home')) # ওনার না হলে হোমে ফেরত পাঠাবে

    if request.method == 'POST':
        # বটের কনফিগারেশন আপডেট
        new_config = {
            "prefix": request.form.get('prefix'),
            "status": request.form.get('status')
        }
        Database.save_config(new_config)
    
    current_config = Database.get_config()
    return render_template('owner_dashboard.html', config=current_config)
    
