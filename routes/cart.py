from flask import Blueprint, render_template, redirect, session
from database import Database

# ১. Blueprint তৈরি করা হলো
cart_bp = Blueprint('cart', __name__)

# ২. মেইন কার্ট পেজ
@cart_bp.route('/cart')
def cart():
    user = session.get('user')
    if not user: 
        return redirect('/account')
    
    WBM_U_ID = user['id'] # সেশন থেকে WBM_U_ID নেওয়া হলো
    cart_items = Database.get_user_cart(WBM_U_ID) 
    
    total = sum(float(item['price']) for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total_price=total)

# ৩. কার্টে প্রোডাক্ট অ্যাড করা
@cart_bp.route('/add_to_cart/<WBM_P_ID>')
def add_to_cart(WBM_P_ID):
    user = session.get('user')
    if user: 
        WBM_U_ID = user['id']
        Database.add_to_cart(WBM_U_ID, WBM_P_ID)
    return redirect('/cart')

# ৪. কার্ট থেকে প্রোডাক্ট রিমুভ করা
@cart_bp.route('/remove_from_cart/<WBM_P_ID>')
def remove_from_cart(WBM_P_ID):
    user = session.get('user')
    if user: 
        WBM_U_ID = user['id']
        Database.remove_from_cart(WBM_U_ID, WBM_P_ID)
    return redirect('/cart')

# ৫. উইশলিস্ট রুট
@cart_bp.route('/wishlist')
def wishlist():
    return """
    <div style="text-align: center; padding: 50px; font-family: sans-serif;">
        <h1 style="font-size: 50px; margin: 0;">❤️</h1>
        <h2>Wishlist feature is coming soon!</h2>
        <a href="/" style="color: #cc0000; text-decoration: none; font-weight: bold;">← Go back to Home</a>
    </div>
    """
    
