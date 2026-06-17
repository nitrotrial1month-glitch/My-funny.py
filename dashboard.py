from flask import Blueprint, render_template, request, redirect, url_for, session
from database import Database

# নতুন ব্লুপ্রিন্ট তৈরি করা হলো
dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/seller', methods=['GET', 'POST'])
def seller_dashboard():
    user = session.get('user')
    if not user or not user.get('is_seller'):
        return redirect(url_for('home'))

    if request.method == 'POST':
        Database.add_product(
            request.form['name'],
            request.form['desc'],
            request.form['price'],
            request.form['image']
        )
        return redirect(url_for('dashboard.seller_dashboard'))

    products = Database.get_all_products()
    return render_template('seller_dashboard.html', products=products)

@dashboard_bp.route('/owner', methods=['GET', 'POST'])
def owner_dashboard():
    user = session.get('user')
    if not user or not user.get('is_owner'):
        return redirect(url_for('home'))

    if request.method == 'POST':
        # বটের কনফিগারেশন লজিক
        new_config = {
            "prefix": request.form.get('prefix'),
            "status": request.form.get('status')
        }
        Database.save_config(new_config)
    
    current_config = Database.get_config()
    return render_template('owner_dashboard.html', config=current_config)
  
