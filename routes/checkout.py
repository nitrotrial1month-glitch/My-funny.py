from flask import Blueprint, render_template, redirect, session, request, jsonify
from bson import ObjectId
from database import Database
import uuid # ইউনিক অ্যাড্রেস আইডি বানানোর জন্য
from datetime import datetime, timedelta # তারিখ হিসাবের জন্য

# ১. Blueprint তৈরি করা হলো
checkout_bp = Blueprint('checkout', __name__)

# ==========================================================
# 🚚 SMART DELIVERY CALCULATION LOGIC
# ==========================================================
def get_delivery_charge(pincode, seller_id=None):
    if not pincode or len(str(pincode)) != 6:
        return 50 # ভুল পিনকোড হলে ডিফল্ট ৫০ টাকা
    
    pincode_str = str(pincode)
    
    # 🔴 ডেমো লজিক: যদি পিনকোড '713' (বর্ধমান/गुসকরা এলাকা) দিয়ে শুরু হয়, তবে ফ্রি!
    if pincode_str.startswith('713'):
        return 0
    # কলকাতা বা অন্যান্য এলাকার জন্য 
    elif pincode_str.startswith('700'):
        return 40
    else:
        return 80 # দূরের জেলার জন্য

@checkout_bp.route('/calculate_delivery', methods=['POST'])
def calculate_delivery():
    data = request.get_json()
    pincode = data.get('pincode', '')
    charge = get_delivery_charge(pincode)
    return jsonify({"charge": charge})


# ==========================================================
# 🛒 চেকআউট এবং অর্ডারের রাউটগুলো
# ==========================================================

# ২. কার্ট থেকে চেকআউট পেজ
@checkout_bp.route('/checkout')
def checkout_cart():
    user = session.get('user')
    if not user: return redirect('/account')
    
    cart_items = Database.get_user_cart(user['id'])
    if not cart_items: return redirect('/cart')
    
    db_users = Database.get_collection("users")
    user_data = db_users.find_one({"discord_id": str(user['id'])}) if db_users is not None else {}
    saved_addresses = user_data.get('addresses', [])
    
    default_pincode = ""
    for add in saved_addresses:
        if add.get('is_default'):
            default_pincode = add.get('pincode', '')
            break
            
    total = sum(float(item['price']) for item in cart_items)
    
    return render_template('checkout.html', items=cart_items, total_price=total, is_direct=False, saved_addresses=saved_addresses, user_default_pincode=default_pincode)

# ৩. ডাইরেক্ট চেকআউট (Buy Now) পেজ
@checkout_bp.route('/checkout/<product_id>')
def checkout_direct(product_id):
    user = session.get('user')
    if not user: return redirect('/account')
    
    col = Database.get_collection("products")
    product = col.find_one({"_id": ObjectId(product_id)}) if col is not None else None
    if not product: return "Product not found!", 404
    
    # 🔴 URL থেকে সাইজটি নেওয়া হচ্ছে
    selected_size = request.args.get('size', '')
    if selected_size:
        product['selected_size'] = selected_size
    
    db_users = Database.get_collection("users")
    user_data = db_users.find_one({"discord_id": str(user['id'])}) if db_users is not None else {}
    saved_addresses = user_data.get('addresses', [])
    
    default_pincode = ""
    for add in saved_addresses:
        if add.get('is_default'):
            default_pincode = add.get('pincode', '')
            break
            
    total = float(product['price'])
    
    return render_template('checkout.html', items=[product], total_price=total, is_direct=True, direct_product_id=str(product_id), saved_addresses=saved_addresses, user_default_pincode=default_pincode)

# ৪. অর্ডার প্রসেস করা (অর্ডার সাবমিট বাটনে ক্লিক করলে)
@checkout_bp.route('/process_checkout', methods=['POST'])
def process_checkout():
    user = session.get('user')
    if not user: return redirect('/account')
    
    payment_method = request.form.get('payment_method')
    is_direct = request.form.get('is_direct') == 'True'
    address_selection = request.form.get('address_selection')
    
    # 🔴 UPDATE: ফর্ম অথবা ইউআরএল কুয়েরি উভয় জায়গা থেকেই সাইজ খোঁজার সেফ লজিক
    size = request.form.get('size') or request.args.get('size') or 'Regular'
    
    db_users = Database.get_collection("users")
    user_data = db_users.find_one({"discord_id": str(user['id'])}) if db_users is not None else {}
    saved_addresses = user_data.get('addresses', [])
    
    final_name, final_phone, final_address, final_pincode = "", "", "", ""
    
    if address_selection == 'new':
        final_name = request.form.get('name')
        final_phone = request.form.get('phone')
        final_address = request.form.get('address')
        final_pincode = request.form.get('new_pincode')
        
        for add in saved_addresses:
            add['is_default'] = False
            
        new_address_obj = {
            "id": str(uuid.uuid4()),
            "name": final_name,
            "phone": final_phone,
            "address": final_address,
            "pincode": final_pincode,
            "is_default": True
        }
        saved_addresses.append(new_address_obj)
        if db_users is not None:
            db_users.update_one({"discord_id": str(user['id'])}, {"$set": {"addresses": saved_addresses}})
    else:
        try:
            sel_idx = int(address_selection)
            selected_add = saved_addresses[sel_idx]
            final_name = selected_add.get('name')
            final_phone = selected_add.get('phone')
            final_address = selected_add.get('address')
            final_pincode = selected_add.get('pincode')
        except:
            return "Invalid Address Selection", 400

    delivery_charge = get_delivery_charge(final_pincode)
    col_orders = Database.get_collection("orders")
    
    if is_direct:
        product_id = request.form.get('product_id')
        col = Database.get_collection("products")
        product = col.find_one({"_id": ObjectId(product_id)})
        
        initial_status = "Confirmed" if payment_method == "COD" else "Pending Payment"
        final_total = float(product['price']) + delivery_charge
        
        # 🔴 UPDATE: Added 'product_image' for easy rendering in dashboard
        new_order = {
            "user_id": str(user['id']),
            "seller_id": str(product.get('seller_id', 'Unknown')),
            "store_name": product.get('store_name', 'My Store'),
            "product_name": product.get('name', 'Item'),
            "product_image": product.get('image', ''),
            "size": size,
            "name": final_name,
            "address": f"{final_address}, PIN: {final_pincode}",
            "phone": final_phone,
            "total_price": final_total,
            "payment_method": payment_method,
            "status": initial_status,
            "date": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
            "items": [product]
        }
        
        result = col_orders.insert_one(new_order)
        order_id = str(result.inserted_id)
        
    else:
        items = Database.get_user_cart(user['id'])
        items_total = sum(float(item['price']) for item in items)
        final_total = items_total + delivery_charge
        initial_status = "Confirmed" if payment_method == "COD" else "Pending Payment"
        
        first_seller_id = items[0].get('seller_id', 'Unknown') if items else 'Unknown'
        first_product_name = items[0].get('name', 'Multiple Items') if items else 'Items'
        first_product_image = items[0].get('image', '') if items else ''
        
        new_order = {
            "user_id": str(user['id']),
            "seller_id": first_seller_id,
            "product_name": f"{first_product_name} & more",
            "product_image": first_product_image,
            "size": size,
            "name": final_name,
            "address": f"{final_address}, PIN: {final_pincode}",
            "phone": final_phone,
            "total_price": final_total,
            "payment_method": payment_method,
            "status": initial_status,
            "date": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
            "items": items
        }
        result = col_orders.insert_one(new_order)
        order_id = str(result.inserted_id)
        Database.clear_user_cart(user['id']) # কার্ট ক্লিয়ার
        
    if payment_method == "Online":
        return redirect(f'/pay/{order_id}')
    else:
        return redirect(f'/order_success/{order_id}')


# ==========================================================
# 📍 অ্যাড্রেস ম্যানেজমেন্ট রাউটস
# ==========================================================

# ৫. সেভ করা অ্যাড্রেস পেজ
@checkout_bp.route('/saved_addresses', methods=['GET', 'POST'])
def saved_addresses():
    user = session.get('user')
    if not user: return redirect('/account')
    
    db_users = Database.get_collection("users")
    user_data = db_users.find_one({"discord_id": str(user['id'])}) if db_users is not None else {}
    addresses = user_data.get('addresses', [])
    
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        pincode = request.form.get('pincode')
        is_default = request.form.get('is_default') == 'on'
        
        if name and phone and address and pincode:
            if is_default:
                for add in addresses:
                    add['is_default'] = False
                    
            new_add = {
                "id": str(uuid.uuid4()),
                "name": name,
                "phone": phone,
                "address": address,
                "pincode": pincode,
                "is_default": is_default or len(addresses) == 0
            }
            addresses.append(new_add)
            if db_users is not None:
                db_users.update_one({"discord_id": str(user['id'])}, {"$set": {"addresses": addresses}})
        return redirect('/saved_addresses')
        
    return render_template('saved_addresses.html', addresses=addresses)

# ৬. ডিফল্ট অ্যাড্রেস সেট করার রাউট
@checkout_bp.route('/set_default_address/<int:index>', methods=['POST'])
def set_default_address(index):
    user = session.get('user')
    if not user: return redirect('/account')
    
    db_users = Database.get_collection("users")
    user_data = db_users.find_one({"discord_id": str(user['id'])}) if db_users is not None else {}
    addresses = user_data.get('addresses', [])
    
    if 0 <= index < len(addresses):
        for i, add in enumerate(addresses):
            add['is_default'] = (i == index)
            
        if db_users is not None:
            db_users.update_one({"discord_id": str(user['id'])}, {"$set": {"addresses": addresses}})
            
    return redirect('/saved_addresses')


# ==========================================================
# 💳 পেমেন্ট রাউটস
# ==========================================================

# ৭. অনলাইন পেমেন্ট পেজ
@checkout_bp.route('/pay/<order_id>')
def pay_online(order_id):
    order = Database.get_order_by_id(order_id)
    if not order: return "Order not found", 404
    fampay_upi_id = "9046348427@fam" 
    return render_template('payment.html', order=order, upi_id=fampay_upi_id)

# ৮. পেমেন্ট কনফার্মেশন
@checkout_bp.route('/confirm_payment/<order_id>', methods=['POST'])
def confirm_payment(order_id):
    Database.update_order_status(order_id, "Confirmed")
    return redirect(f'/order_success/{order_id}')

# ৯. অর্ডার সাকসেস পেজ
@checkout_bp.route('/order_success/<order_id>')
def order_success(order_id):
    order = Database.get_order_by_id(order_id)
    if not order: return "Order not found", 404
    return render_template('order_success.html', order=order)
