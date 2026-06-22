from flask import Blueprint, render_template, session, redirect, abort, url_for
from database import Database
from bson import ObjectId
from functools import wraps

delivery_bp = Blueprint('delivery', __name__)

# Security: ডেলিভারি পার্টনার ছাড়া কেউ এই পেজ দেখতে পারবে না
def delivery_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user.get('role') != 'delivery':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@delivery_bp.route('/delivery-dashboard')
@delivery_required
def delivery_dashboard():
    user = session.get('user')
    col = Database.get_collection("orders")
    # সব রেডি অর্ডার অথবা আউট ফর ডেলিভারি অর্ডারগুলো দেখাবে
    assigned_orders = list(col.find({
        "delivery_partner_id": user.get('id'), 
        "status": {"$in": ["Ready for Pickup", "Out for Delivery"]}
    }).sort("_id", -1))
    
    return render_template('delivery-dashboard.html', orders=assigned_orders, user=user)

@delivery_bp.route('/delivery/pickup/<order_id>')
@delivery_required
def pickup_order(order_id):
    Database.update_order_status(order_id, "Out for Delivery")
    return redirect(url_for('delivery.delivery_dashboard'))

@delivery_bp.route('/delivery/complete/<order_id>')
@delivery_required
def complete_delivery(order_id):
    Database.update_order_status(order_id, "Delivered")
    return redirect(url_for('delivery.delivery_dashboard'))
    
