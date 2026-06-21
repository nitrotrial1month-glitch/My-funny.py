import os
import requests
from flask import Blueprint, render_template, redirect, session, request
from bson import ObjectId
from database import Database

# ১. Blueprint তৈরি করা হলো
checkout_bp = Blueprint('checkout', __name__)

# ==========================================================
# 🔴 সেলারকে DM পাঠানোর ফাংশন (শুধুমাত্র এই ফাইলের জন্য)
# ==========================================================
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")

def notify_sellers_via_dm(order_id, name, phone, address, items, payment_method):
    if not DISCORD_TOKEN: 
        print("Error: DISCORD_TOKEN is missing for DM!")
        return
    
    headers = {"Authorization": f"Bot {DISCORD_TOKEN}", "Content-Type": "application/json"}
    seller_items = {}
    
    for item in items:
        seller_id = item.get('seller_id')
        if seller_id:
            if seller_id not in seller_items: seller_items[seller_id] = []
            seller_items[seller_id].append(item)

    for seller_id, s_items in seller_items.items():
        dm_payload = {"recipient_id": int(seller_id)}
        dm_req = requests.post("https://discord.com/api/v10/users/@me/channels", json=dm_payload, headers=headers)
        
        if dm_req.status_code == 200:
            channel_id = dm_req.json().get("id")
            
            item_details = ""
            for i in s_items:
                size_info = f" (Size: {i.get('selected_size')})" if i.get('selected_size') else ""
                item_details += f"• **{i.get('name', 'Product')}**{size_info} - ₹{i.get('price', 0)}\n"

            msg_content = (
                f"🎉 **New Order Received!**\n\n"
                f"**Order ID:** #{str(order_id).upper()[:8]}\n"
                f"**Payment Method:** {payment_method}\n\n"
                f"🛒 **Items Ordered from You:**\n{item_details}\n"
                f"👤 **Customer Details:**\n"
                f"**Name:** {name}\n"
                f"**Phone:** {phone}\n"
                f"**Address:** {address}\n\n"
                f"⚡ *Please prepare this order for delivery.*"
            )
            
            requests.post(f"https://discord.com/api/v10/channels/{channel_id}/messages", json={"content": msg_content}, headers=headers)

# ==========================================================
# 🛒 চেকআউট এবং অর্ডারের রাউটগুলো
# ==========================================================

# ৩. কার্ট থেকে চেকআউট পেজ
@checkout_bp.route('/checkout')
def checkout_cart():
    user = session.get('user')
    if not user: return redirect('/account')
    cart_items = Database.get_user_cart(user['id'])
    if not cart_items: return redirect('/cart')
    saved_addresses = Database.get_user_addresses(user['id'])
    total = sum(float(item['price']) for item in cart_items)
    return render_template('checkout.html', items=cart_items, total_price=total, is_direct=False, saved_addresses=saved_addresses)

# ৪. ডাইরেক্ট চেকআউট (Buy Now) পেজ
@checkout_bp.route('/checkout/<product_id>')
def checkout_direct(product_id):
    user = session.get('user')
    if not user: return redirect('/account')
    col = Database.get_collection("products")
    product = col.find_one({"_id": ObjectId(product_id)})
    if not product: return "Product not found!", 404
    saved_addresses = Database.get_user_addresses(user['id'])
    total = float(product['price'])
    return render_template('checkout.html', items=[product], total_price=total, is_direct=True, direct_product_id=str(product_id), saved_addresses=saved_addresses)

# ৫. অর্ডার প্রসেস করা (অর্ডার সাবমিট বাটনে ক্লিক করলে)
@checkout_bp.route('/process_checkout', methods=['POST'])
def process_checkout():
    user = session.get('user')
    if not user: return redirect('/account')
    
    name = request.form.get('name')
    address = request.form.get('address')
    phone = request.form.get('phone')
    payment_method = request.form.get('payment_method')
    is_direct = request.form.get('is_direct') == 'True'
    
    if is_direct:
        product_id = request.form.get('product_id')
        col = Database.get_collection("products")
        product = col.find_one({"_id": ObjectId(product_id)})
        items = [product]
        total = float(product['price'])
        clear_cart = False
    else:
        items = Database.get_user_cart(user['id'])
        total = sum(float(item['price']) for item in items)
        clear_cart = True
        
    initial_status = "Confirmed" if payment_method == "COD" else "Pending Payment"
    order_id, expected_date = Database.place_order(user['id'], items, total, name, address, phone, payment_method, clear_cart, status=initial_status)
    
    Database.save_user_address(user['id'], name, phone, address)
    
    # সেলারকে DM পাঠানো হচ্ছে
    notify_sellers_via_dm(order_id, name, phone, address, items, payment_method)
    
    if payment_method == "Online":
        return redirect(f'/pay/{order_id}')
    else:
        return redirect(f'/order_success/{order_id}')

# ৬. অনলাইন পেমেন্ট পেজ
@checkout_bp.route('/pay/<order_id>')
def pay_online(order_id):
    order = Database.get_order_by_id(order_id)
    if not order: return "Order not found", 404
    fampay_upi_id = "9046348427@fam" 
    return render_template('payment.html', order=order, upi_id=fampay_upi_id)

# ৭. পেমেন্ট কনফার্মেশন
@checkout_bp.route('/confirm_payment/<order_id>', methods=['POST'])
def confirm_payment(order_id):
    Database.update_order_status(order_id, "Confirmed")
    return redirect(f'/order_success/{order_id}')

# ৮. অর্ডার সাকসেস পেজ
@checkout_bp.route('/order_success/<order_id>')
def order_success(order_id):
    order = Database.get_order_by_id(order_id)
    if not order: return "Order not found", 404
    return render_template('order_success.html', order=order)

# ৯. সেভ করা অ্যাড্রেস রুট
@checkout_bp.route('/saved_addresses', methods=['GET', 'POST'])
def saved_addresses():
    user = session.get('user')
    if not user: return redirect('/account')
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        if name and phone and address:
            Database.save_user_address(user['id'], name, phone, address)
        return redirect('/saved_addresses')
    addresses = Database.get_user_addresses(user['id'])
    return render_template('saved_addresses.html', addresses=addresses)
