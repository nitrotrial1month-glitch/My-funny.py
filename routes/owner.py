from flask import Blueprint, render_template, redirect, session, flash, abort
from database import Database
from functools import wraps

owner_bp = Blueprint('owner', __name__)

# ==========================================
# 🛡️ Owner Security Decorator
# ==========================================
def owner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user.get('role') != 'owner':
            abort(403, description="Access Denied: Only Owner can access this page.")
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# 👑 Owner Dashboard
# ==========================================
@owner_bp.route('/owner-dashboard')
@owner_required
def owner_dashboard():
    user = session.get('user')
    
    db_users = Database.get_collection("users")
    db_orders = Database.get_collection("orders")
    db_products = Database.get_collection("products")
    
    total_users = db_users.count_documents({}) if db_users is not None else 0
    total_orders = db_orders.count_documents({}) if db_orders is not None else 0
    total_products = db_products.count_documents({}) if db_products is not None else 0
    
    pending_products = list(db_products.find({"status": "Pending"})) if db_products is not None else []
    insure_requests = list(db_products.find({"inwear_insure": "Pending Approval"})) if db_products is not None else []
    latest_orders = list(db_orders.find({}).sort("_id", -1).limit(20)) if db_orders is not None else []
    
    pending_sellers = list(db_users.find({"role": "pending_seller"})) if db_users is not None else []
    pending_deliveries = list(db_users.find({"role": "pending_delivery"})) if db_users is not None else []

    return render_template('owner_dashboard.html', 
                           current_user=user,
                           total_users=total_users, 
                           total_orders=total_orders,
                           total_products=total_products,
                           pending_products=pending_products,
                           insure_requests=insure_requests, 
                           orders=latest_orders,
                           pending_sellers=pending_sellers,
                           pending_deliveries=pending_deliveries)

# ==========================================
# ✅ Approve / Reject Applications
# ==========================================
@owner_bp.route('/admin/approve/<WBM_U_ID>')
@owner_required
def approve_user(WBM_U_ID):
    col = Database.get_collection("users")
    if col is not None:
        user = col.find_one({"WBM_U_ID": WBM_U_ID})
        if user:
            new_role = "seller" if user.get('role') == "pending_seller" else "delivery"
            col.update_one({"WBM_U_ID": WBM_U_ID}, {"$set": {"role": new_role}})
            flash(f"User {WBM_U_ID} approved as {new_role} successfully!")
            
    return redirect('/owner-dashboard')

@owner_bp.route('/admin/reject/<WBM_U_ID>')
@owner_required
def reject_user(WBM_U_ID):
    col = Database.get_collection("users")
    if col is not None:
        col.update_one({"WBM_U_ID": WBM_U_ID}, {
            "$set": {"role": "user"},
            "$unset": {"application_data": ""}
        })
        flash(f"Application for {WBM_U_ID} Rejected and data cleared.")
        
    return redirect('/owner-dashboard')
  
