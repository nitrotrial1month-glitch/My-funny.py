import os
import requests
import random
from flask import Blueprint, render_template, redirect, session, request
from werkzeug.utils import secure_filename
from bson import ObjectId
from database import Database

# ১. Blueprint তৈরি করা হলো
products_bp = Blueprint('products', __name__)

# ==========================================================
# 🔴 ডিসকর্ডে ভেরিফিকেশন মেসেজ পাঠানোর ফাংশন
# ==========================================================
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
VERIFICATION_CHANNEL_ID = os.environ.get("VERIFICATION_CHANNEL_ID")

def send_verification_to_discord(product_data, WBM_P_ID):
    if not DISCORD_TOKEN or not VERIFICATION_CHANNEL_ID: 
        print("Error: DISCORD_TOKEN or VERIFICATION_CHANNEL_ID is missing!")
        return
    
    headers = {"Authorization": f"Bot {DISCORD_TOKEN}", "Content-Type": "application/json"}
    
    embed = {
        "title": "🆕 New Product for Verification",
        "color": 16753920, # Orange
        "fields": [
            {"name": "Product Name", "value": product_data.get('name', 'N/A'), "inline": True},
            {"name": "Price", "value": f"₹{product_data.get('price', '0')}", "inline": True},
            {"name": "Seller ID", "value": f"{product_data.get('seller_id', '')}", "inline": False}
        ],
        "footer": {"text": f"ID: {WBM_P_ID}"}
    }
    
    try:
        res = requests.post(f"https://discord.com/api/v10/channels/{VERIFICATION_CHANNEL_ID}/messages", json={"embeds": [embed]}, headers=headers)
        if res.status_code == 200:
            msg_id = res.json()['id']
            requests.put(f"https://discord.com/api/v10/channels/{VERIFICATION_CHANNEL_ID}/messages/{msg_id}/reactions/%E2%9C%85/@me", headers=headers)
            requests.put(f"https://discord.com/api/v10/channels/{VERIFICATION_CHANNEL_ID}/messages/{msg_id}/reactions/%E2%9D%8C/@me", headers=headers)
    except Exception as e:
        print("Discord Error:", e)

# ==========================================================
# 👕 প্রোডাক্ট পেজ এবং সেলার আপলোড/এডিট রাউট
# ==========================================================

# ২. প্রোডাক্টের ডিটেইলস পেজ (🔴 UPDATED: সেলার পিনকোড পাঠানো হচ্ছে ডেলিভারি ক্যালকুলেশনের জন্য)
@products_bp.route('/product/<WBM_P_ID>')
def product_details(WBM_P_ID):
    col = Database.get_collection("products")
    db_users = Database.get_collection("users")
    
    # 🔴 SMART LOGIC for fetching
    query = {"_id": ObjectId(WBM_P_ID)} if len(WBM_P_ID) == 24 else {"WBM_P_ID": WBM_P_ID}
    product = col.find_one(query) if col is not None else None
    
    if not product: return "Product not found!", 404
    
    # 🔴 সেলারের পিনকোড খোঁজা হচ্ছে (প্রোডাক্ট পেজে ডেলিভারি চার্জ দেখানোর জন্য)
    seller_id = str(product.get('seller_id', ''))
    seller_info = db_users.find_one({"WBM_U_ID": seller_id}) if seller_id and db_users else None
    
    if seller_info and seller_info.get('pincode'):
        product['seller_pincode'] = seller_info.get('pincode')
    elif seller_info and seller_info.get('application_data') and seller_info['application_data'].get('pincode'):
        product['seller_pincode'] = seller_info['application_data'].get('pincode')
    else:
        product['seller_pincode'] = "713128" # ফলব্যাক পিনকোড
    
    seller_products = []
    if 'seller_id' in product:
        seller_products = Database.get_products_by_seller(product['seller_id'])
        
    return render_template('product.html', product=product, seller_products=seller_products)
    

# ৩. সেলার প্রোডাক্ট আপলোড
@products_bp.route('/seller/upload', methods=['POST'])
def upload_product():
    user = session.get('user')
    if not user: return redirect('/account')
    
    name = request.form.get('name', 'Unknown')
    description = request.form.get('description', '')
    details = request.form.get('details', '')
    raw_tags = request.form.get('tags', '')
    seller_upi = request.form.get('seller_upi', '').strip()
    
    tags_list = []
    if raw_tags:
        for tag in raw_tags.replace(',', ' ').split():
            clean_tag = tag.strip()
            if clean_tag:
                if not clean_tag.startswith('#'):
                    clean_tag = '#' + clean_tag
                tags_list.append(clean_tag)

    if seller_upi:
        db_users = Database.get_collection("users")
        if db_users is not None:
            db_users.update_one({"WBM_U_ID": str(user.get('id'))}, {"$set": {"upi_id": seller_upi}})

    raw_orig = request.form.get('original_price', '0')
    raw_final = request.form.get('final_price', '') 
    original = float(raw_orig) if raw_orig and raw_orig.strip() != "" else 0.0
    final = float(raw_final) if raw_final and raw_final.strip() != "" else original
    discount_percent = ((original - final) / original) * 100 if original > 0 and final < original else 0
    
    can_return = request.form.get('can_return') == 'on'
    can_replace = request.form.get('can_replace') == 'on'
    gender = request.form.get('gender', 'Unisex')
    
    upload_dir = os.path.join('static', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    
    image_paths = []
    for img_key in ['image1', 'image2', 'image3']:
        file = request.files.get(img_key)
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(upload_dir, filename))
            image_paths.append('static/uploads/' + filename)
            
    video_path = ""
    video_file = request.files.get('video')
    if video_file and video_file.filename:
        v_filename = secure_filename(video_file.filename)
        video_file.save(os.path.join(upload_dir, v_filename))
        video_path = 'static/uploads/' + v_filename

    main_image = image_paths[0] if len(image_paths) > 0 else ""

    # 🔴 NEW: Generate Product ID
    new_wbm_pid = f"{random.randint(100000, 999999)}WBM{random.randint(1000, 9999)}"

    product_data = {
        "WBM_P_ID": new_wbm_pid,          # 🔴 Add to DB
        "name": name,
        "description": description,
        "full_details": details,
        "tags": tags_list,
        "sizes": [s.strip() for s in request.form.get('sizes', '').split(',')] if request.form.get('sizes') else [],
        "original_price": original,
        "price": final,
        "discount_percent": round(discount_percent),
        "image": main_image,             
        "extra_images": image_paths,     
        "video": video_path,
        "gender": gender,
        "policies": {
            "return_eligible": can_return,
            "replace_eligible": can_replace
        },
        "status": "Pending",
        "seller_id": str(user.get('id'))  # This matches WBM_U_ID
    }
    
    inserted_id = Database.add_product_from_dict(product_data)
    
    if inserted_id:
        send_verification_to_discord(product_data, new_wbm_pid) # 🔴 Pass new ID
        
    return redirect('/seller-dashboard')


# ৪. সেলার প্রোডাক্ট এডিট
@products_bp.route('/seller/edit/<WBM_P_ID>', methods=['GET', 'POST'])
def edit_product(WBM_P_ID):
    user = session.get('user')
    if not user: return redirect('/account')
    
    col = Database.get_collection("products")
    query = {"_id": ObjectId(WBM_P_ID)} if len(WBM_P_ID) == 24 else {"WBM_P_ID": WBM_P_ID}
    product = col.find_one(query) if col is not None else None
    
    if not product or product.get('seller_id') != str(user['id']): 
        return "Unauthorized! You can only edit your own products.", 403

    if request.method == 'POST':
        original = float(request.form.get('original_price', 0))
        raw_final = request.form.get('final_price', '')
        final = float(raw_final) if raw_final and raw_final.strip() != "" else original
        discount_percent = ((original - final) / original) * 100 if original > 0 and final < original else 0
        sizes_input = request.form.get('sizes', '')
        
        raw_tags = request.form.get('tags', '')
        tags_list = []
        if raw_tags:
            for tag in raw_tags.replace(',', ' ').split():
                clean_tag = tag.strip()
                if clean_tag:
                    if not clean_tag.startswith('#'):
                        clean_tag = '#' + clean_tag
                    tags_list.append(clean_tag)

        updated_data = {
            "name": request.form.get('name'),
            "description": request.form.get('description'),
            "full_details": request.form.get('details'),
            "tags": tags_list,
            "sizes": [s.strip() for s in sizes_input.split(',')] if sizes_input else [],
            "original_price": original,
            "price": final,
            "discount_percent": round(discount_percent)
        }
        
        col.update_one(query, {"$set": updated_data})
        return redirect('/seller-dashboard')
        
    return render_template('edit_product.html', product=product)

# ৫. সেলারের নিজস্ব প্রোডাক্ট ডিলিট করার রাউট
@products_bp.route('/seller/delete/<WBM_P_ID>', methods=['POST'])
def delete_seller_product(WBM_P_ID):
    user = session.get('user')
    if not user: 
        return redirect('/account')
    
    col = Database.get_collection("products")
    query = {"_id": ObjectId(WBM_P_ID)} if len(WBM_P_ID) == 24 else {"WBM_P_ID": WBM_P_ID}
    product = col.find_one(query) if col is not None else None
    
    if not product or product.get('seller_id') != str(user['id']): 
        return "Unauthorized! You can only delete your own products.", 403

    col.delete_one(query)
    
    return redirect('/seller-dashboard')
    
