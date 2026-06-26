from flask import Blueprint, render_template, redirect, session, request, jsonify
from bson import ObjectId
from database import Database
import uuid
from datetime import datetime
import random
import math
import pgeocode

checkout_bp = Blueprint('checkout', __name__)

# ==========================================================
# 🚚 DYNAMIC DISTANCE-BASED DELIVERY CALCULATION
# ==========================================================
def get_delivery_charge(user_pincode, seller_pincode):
    if not user_pincode or len(str(user_pincode)) != 6:
        return 50 
    
    if not seller_pincode or len(str(seller_pincode)) != 6:
        seller_pincode = "713128" 

    if str(user_pincode) == str(seller_pincode):
        return 0

    try:
        dist_calculator = pgeocode.GeoDistance('IN')
        distance_km = dist_calculator.query_postal_code(str(user_pincode), str(seller_pincode))
        
        if math.isnan(distance_km):
            return 60
            
        distance_km = float(distance_km)
        
        if distance_km <= 15: return 0    
        elif distance_km <= 100: return 40   
        elif distance_km <= 500: return 70   
        else: return 100  
            
    except Exception as e:
        print("Delivery Calc Error:", e)
        return 50 

@checkout_bp.route('/calculate_delivery', methods=['POST'])
def calculate_delivery():
    data = request.get_json()
    pincode = data.get('pincode', '')
    seller_pincode = data.get('seller_pincode', '713128')
    
    charge = get_delivery_charge(pincode, seller_pincode)
    return jsonify({"charge": charge})


# ==========================================================
# 🛒 চেকআউট এবং অর্ডারের রাউটগুলো
# ==========================================================

@checkout_bp.route('/checkout')
def checkout_cart():
    user = session.get('user')
    if not user: return redirect('/account')
    
    cart_items = Database.get_user_cart(user['id'])
    if not cart_items: return redirect('/cart')
    
    db_users = Database.get_collection("users")
    user_data = db_users.find_one({"WBM_U_ID": str(user['id'])}) if db_users is not None else {}
    saved_addresses = user_data.get('addresses', [])
    
    default_pincode = ""
    for add in saved_addresses:
        if add.get('is_default'):
            default_pincode = add.get('pincode', '')
            break
            
    # 🔴 FIX: seller_id এর বদলে WBM_U_ID ব্যবহার করা হচ্ছে
    for item in cart_items:
        seller_id = str(item.get('WBM_U_ID', item.get('seller_id', ''))) 
        seller_info = db_users.find_one({"WBM_U_ID": seller_id}) if seller_id else None
        if seller_info and seller_info.get('pincode'):
            item['seller_pincode'] = seller_info.get('pincode')
        else:
            item['seller_pincode'] = "713128"
            
    total = sum(float(item['price']) for item in cart_items)
    
    return render_template('checkout.html', items=cart_items, total_price=total, is_direct=False, saved_addresses=saved_addresses, user_default_pincode=default_pincode)


@checkout_bp.route('/checkout/<WBM_P_ID>')
def checkout_direct(WBM_P_ID):
    user = session.get('user')
    if not user: return redirect('/account')
    
    col = Database.get_collection("products")
    product = None
    
    if len(WBM_P_ID) == 24:
        try: product = col.find_one({"_id": ObjectId(WBM_P_ID)})
        except: pass
    
    if not product:
        product = col.find_one({"WBM_P_ID": WBM_P_ID})
        
    if not product: return "Product not found!", 404
    
    selected_size = request.args.get('size', '')
    if selected_size:
        product['selected_size'] = selected_size
    
    db_users = Database.get_collection("users")
    user_data = db_users.find_one({"WBM_U_ID": str(user['id'])}) if db_users is not None else {}
    saved_addresses = user_data.get('addresses', [])
    
    default_pincode = ""
    for add in saved_addresses:
        if add.get('is_default'):
            default_pincode = add.get('pincode', '')
            break
            
    # 🔴 FIX: seller_id এর বদলে WBM_U_ID ব্যবহার করা হচ্ছে
    seller_id = str(product.get('WBM_U_ID', product.get('seller_id', '')))
    seller_info = db_users.find_one({"WBM_U_ID": seller_id}) if seller_id else None
    if seller_info and seller_info.get('pincode'):
        product['seller_pincode'] = seller_info.get('pincode')
    else:
        product['seller_pincode'] = "713128"
            
    total = float(product['price'])
    
    return render_template('checkout.html', items=[product], total_price=total, is_direct=True, direct_product_id=str(WBM_P_ID), saved_addresses=saved_addresses, user_default_pincode=default_pincode)


@checkout_bp.route('/process_checkout', methods=['POST'])
def process_checkout():
    user = session.get('user')
    if not user: return redirect('/account')
    
    payment_method = request.form.get('payment_method')
    utr_number = request.form.get('utr_number', '') 
    is_direct = request.form.get('is_direct') == 'True'
    address_selection = request.form.get('address_selection')
    size = request.form.get('size') or request.args.get('size') or 'Regular'
    
    frontend_total_str = request.form.get('frontend_total', '0')
    try:
        frontend_total = float(frontend_total_str)
    except ValueError:
        frontend_total = 0

    db_users = Database.get_collection("users")
    user_data = db_users.find_one({"WBM_U_ID": str(user['id'])}) if db_users is not None else {}
    saved_addresses = user_data.get('addresses', [])
    
    final_name, final_phone, final_address, final_pincode = "", "", "", ""
    
    if address_selection == 'new':
        final_name = request.form.get('name')
        final_phone = request.form.get('phone')
        final_address = request.form.get('address')
        final_pincode = request.form.get('new_pincode')
        
        for add in saved_addresses: add['is_default'] = False
            
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
            db_users.update_one({"WBM_U_ID": str(user['id'])}, {"$set": {"addresses": saved_addresses}})
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

    col_orders = Database.get_collection("orders")
    wbm_order_id = f"WBM-{datetime.now().strftime('%y%m%d')}-{random.randint(1000, 9999)}"
    
    if payment_method == "Online" and utr_number:
        initial_status = "Pending Verification" 
    elif payment_method == "COD":
        initial_status = "Confirmed"
    else:
        initial_status = "Pending Payment"
    
    # ডাইরেক্ট চেকআউট সেভ
    if is_direct:
        WBM_P_ID = request.form.get('WBM_P_ID') or request.form.get('product_id')
        col = Database.get_collection("products")
        product = None
        
        if len(str(WBM_P_ID)) == 24:
            try: product = col.find_one({"_id": ObjectId(WBM_P_ID)})
            except: pass
                
        if not product:
            product = col.find_one({"WBM_P_ID": WBM_P_ID})
            
        # 🔴 FIX: seller_id এর বদলে WBM_U_ID ব্যবহার করা হচ্ছে
        seller_id = str(product.get('WBM_U_ID', product.get('seller_id', '')))
        
        qty_str = request.form.get('item_qty_0', '1')
        try:
            qty = int(qty_str)
        except ValueError:
            qty = 1

        if frontend_total > 0:
            final_total = frontend_total
        else:
            seller_info = db_users.find_one({"WBM_U_ID": seller_id}) if seller_id else None
            seller_pincode = seller_info.get('pincode', '713128') if seller_info else '713128'
            delivery_charge = get_delivery_charge(final_pincode, seller_pincode)
            final_total = (float(product['price']) * qty) + 9 + delivery_charge

        product['ordered_qty'] = qty 

        new_order = {
            "WBM_O_ID": wbm_order_id,
            "user_id": str(user['id']),
            "seller_id": seller_id, # ডাটাবেসে সেলার আইডিতে WBM_U_ID সেভ হচ্ছে
            "store_name": product.get('store_name', 'Wear By Me'),
            "product_name": product.get('name', 'Item'),
            "product_image": product.get('image', ''),
            "size": size,
            "quantity": qty, 
            "name": final_name,
            "address": f"{final_address}, PIN: {final_pincode}",
            "phone": final_phone,
            "total_price": final_total,
            "payment_method": payment_method,
            "utr_number": utr_number, 
            "status": initial_status,
            "date": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
            "items": [product]
        }
        
        col_orders.insert_one(new_order)
        
    # কার্ট চেকআউট সেভ
    else:
        items = Database.get_user_cart(user['id'])
        # 🔴 FIX: seller_id এর বদলে WBM_U_ID ব্যবহার করা হচ্ছে
        first_seller_id = str(items[0].get('WBM_U_ID', items[0].get('seller_id', ''))) if items else ''
        
        total_items_qty = 0
        for i, item in enumerate(items):
            qty_str = request.form.get(f'item_qty_{i}', '1')
            try:
                qty = int(qty_str)
            except ValueError:
                qty = 1
            item['ordered_qty'] = qty
            total_items_qty += qty

        if frontend_total > 0:
            final_total = frontend_total
        else:
            first_seller_info = db_users.find_one({"WBM_U_ID": first_seller_id}) if first_seller_id else None
            first_seller_pincode = first_seller_info.get('pincode', '713128') if first_seller_info else '713128'
            delivery_charge = get_delivery_charge(final_pincode, first_seller_pincode)
            items_total = sum(float(item['price']) * item['ordered_qty'] for item in items)
            final_total = items_total + 9 + delivery_charge 
        
        first_product_name = items[0].get('name', 'Multiple Items') if items else 'Items'
        first_product_image = items[0].get('image', '') if items else ''
        
        new_order = {
            "WBM_O_ID": wbm_order_id,
            "user_id": str(user['id']),
            "seller_id": first_seller_id, # ডাটাবেসে সেলার আইডিতে WBM_U_ID সেভ হচ্ছে
            "product_name": f"{first_product_name} & more",
            "product_image": first_product_image,
            "size": size,
            "quantity": total_items_qty, 
            "name": final_name,
            "address": f"{final_address}, PIN: {final_pincode}",
            "phone": final_phone,
            "total_price": final_total,
            "payment_method": payment_method,
            "utr_number": utr_number, 
            "status": initial_status,
            "date": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
            "items": items
        }
        
        col_orders.insert_one(new_order)
        Database.clear_user_cart(user['id'])
        
    return redirect(f'/order_success/{wbm_order_id}')


# ==========================================================
# 📍 অ্যাড্রেস ম্যানেজমেন্ট রাউটস
# ==========================================================

@checkout_bp.route('/saved_addresses', methods=['GET', 'POST'])
def saved_addresses():
    user = session.get('user')
    if not user: return redirect('/account')
    
    db_users = Database.get_collection("users")
    user_data = db_users.find_one({"WBM_U_ID": str(user['id'])}) if db_users is not None else {}
    addresses = user_data.get('addresses', [])
    
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        pincode = request.form.get('pincode')
        is_default = request.form.get('is_default') == 'on'
        
        if name and phone and address and pincode:
            if is_default:
                for add in addresses: add['is_default'] = False
                    
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
                db_users.update_one({"WBM_U_ID": str(user['id'])}, {"$set": {"addresses": addresses}})
        return redirect('/saved_addresses')
        
    return render_template('saved_addresses.html', addresses=addresses)


@checkout_bp.route('/set_default_address/<int:index>', methods=['POST'])
def set_default_address(index):
    user = session.get('user')
    if not user: return redirect('/account')
    
    db_users = Database.get_collection("users")
    user_data = db_users.find_one({"WBM_U_ID": str(user['id'])}) if db_users is not None else {}
    addresses = user_data.get('addresses', [])
    
    if 0 <= index < len(addresses):
        for i, add in enumerate(addresses):
            add['is_default'] = (i == index)
            
        if db_users is not None:
            db_users.update_one({"WBM_U_ID": str(user['id'])}, {"$set": {"addresses": addresses}})
            
    return redirect('/saved_addresses')


# ==========================================================
# 💳 অর্ডার সাকসেস রাউট
# ==========================================================

@checkout_bp.route('/order_success/<wbm_order_id>')
def order_success(wbm_order_id):
    col_orders = Database.get_collection("orders")
    order = col_orders.find_one({"WBM_O_ID": wbm_order_id})
    if not order: return "Order not found", 404
    return render_template('order_success.html', order=order, order_id=wbm_order_id)
            
