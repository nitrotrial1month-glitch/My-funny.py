from flask import Blueprint, render_template, session, redirect, abort
from database import Database
from functools import wraps

delivery_bp = Blueprint('delivery', __name__)

# Security: ডেলিভারি পার্টনার ছাড়া কেউ ঢুকতে পারবে না
def delivery_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        # এখানে আপনার ডেটাবেস থেকে চেক করুন ইউজারের রোল 'delivery' কি না
        if not user or user.get('role') != 'delivery':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@delivery_bp.route('/delivery-dashboard')
@delivery_required
def delivery_dashboard():
    user = session.get('user')
    # ডাটাবেস থেকে শুধুমাত্র এই ডেলিভারি বয়-এর জন্য অ্যাসাইন করা অর্ডারগুলো নিয়ে আসুন
    col = Database.get_collection("orders")
    assigned_orders = list(col.find({"delivery_partner_id": user.get('id'), "status": "Ready for Pickup"}))
    
    return render_template('delivery-dashboard.html', orders=assigned_orders)
  
