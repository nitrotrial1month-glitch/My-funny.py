import os
import requests
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

def send_verification_to_discord(product_data, product_id):
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
            {"name": "Seller", "value": f"<@{product_data.get('seller_id', '')}>", "inline": False}
        ],
        "footer": {"text": f"ID: {product_id}"}
    }
    
    res = requests.post(f"https://discord.com/api/v10/channels/{VERIFICATION_CHANNEL_ID}/messages", json={"embeds": [embed]}, headers=headers)
    
    if res.status_code == 200:
        msg_id = res.json()['id']
        requests.put(f"https://discord.com/api/v10/channels/{VERIFICATION_CHANNEL_ID}/messages/{msg_id}/reactions/%E2%9C%85/@me", headers=headers)
        requests.put(f"https://discord.com/api/v10/channels/{VERIFICATION_CHANNEL_ID}/messages/{msg_id}/reactions/%E2%9D%8C/@me", headers=headers)

# ==========================================================
# 👕 প্রোডাক্ট পেজ এবং সেলার আপলোড/এডিট রাউট
# ==========================================================

# ২. প্রোডাক্টের ডিটেইলস পেজ
@products_bp.route('/product/<product_id>')
def product_details(product_id):
    col = Database.get_collection("products")
    product = col.find_one({"_id": ObjectId(product_id)}) if col is not None else None
    if not product: return "Product not found!", 404
    
    seller_products = []
    if 'seller_id' in product:
        seller_products = Database.get_products_by_seller(product['seller_id'])
        
    return render_template('product.html', product=product, seller_products=seller_products)
    

# ৩. সেলার প্রোডাক্ট আপলোড (নতুন ডেসক্রিপশন, ট্যাগ, ভিডিও এবং UPI সহ)
@products_bp.route('/seller/upload', methods=['POST'])
def upload_product():
    user = session.get('user')
    if not user: return redirect('/account')
    
    # 🔴 ফর্ম থেকে নতুন ডেটাগুলো নেওয়া হচ্ছে
    name = request.form.get('name', 'Unknown')
    description = request.form.get('description', '')
    details = request.form.get('details', '')
    raw_tags = request.form.get('tags', '')
    seller_upi = request.form.get('seller_upi', '').strip()
    
    # 🔴 ট্যাগ প্রসেসিং (কমা বা স্পেস সরাতে এবং # বসাতে)
    tags_list = []
    if raw_tags:
        for tag in raw_tags.replace(',', ' ').split():
            clean_tag = tag.strip()
            if clean_tag:
                # যদি ট্যাগের আগে # না থাকে, তবে বসিয়ে দেওয়া
                if not clean_tag.startswith('#'):
                    clean_tag = '#' + clean_tag
                tags_list.append(clean_tag)

    # সেলারের UPI আইডি ডেটাবেসে আপডেট করা (পেমেন্টের জন্য)
    if seller_upi:
        db_users = Database.get_collection("users")
        if db_users is not None:
            db_users.update_one({"discord_id": str(user.get('id'))}, {"$set": {"upi_id": seller_upi}})

    # প্রাইস ক্যালকুলেশন
    raw_orig = request.form.get('original_price', '0')
    raw_final = request.form.get('final_price', '') 
    original = float(raw_orig) if raw_orig and raw_orig.strip() != "" else 0.0
    final = float(raw_final) if raw_final and raw_final.strip() != "" else original
    discount_percent = ((original - final) / original) * 100 if original > 0 and final < original else 0
    
    # পলিসি
    can_return = request.form.get('can_return') == 'on'
    can_replace = request.form.get('can_replace') == 'on'
    gender = request.form.get('gender', 'Unisex')
    
    # ফাইল আপলোড (ছবি এবং ভিডিও)
    upload_dir = os.path.join('static', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    
    image_paths = []
    for img_key in ['image1', 'image2', 'image3']:
        file = request.files.get(img_key)
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(upload_dir, filename))
            image_paths.append('static/uploads/' + filename)
            
    # ভিডিও আপলোড প্রসেসিং
    video_path = ""
    video_file = request.files.get('video')
    if video_file and video_file.filename:
        v_filename = secure_filename(video_file.filename)
        video_file.save(os.path.join(upload_dir, v_filename))
        video_path = 'static/uploads/' + v_filename

    main_image = image_paths[0] if len(image_paths) > 0 else ""

    # ডেটাবেসে সেভ করার জন্য পুরো ডেটা স্ট্রাকচার
    product_data = {
        "name": name,
        "description": description,       # নতুন ডেসক্রিপশন
        "full_details": details,          # নতুন ডিটেইলস
        "tags": tags_list,                # সার্চ করার জন্য ট্যাগ
        "sizes": [s.strip() for s in request.form.get('sizes', '').split(',')] if request.form.get('sizes') else [],
        "original_price": original,
        "price": final,
        "discount_percent": round(discount_percent),
        "image": main_image,             
        "extra_images": image_paths,     
        "video": video_path,              # ভিডিও ফাইল
        "gender": gender,
        "policies": {
            "return_eligible": can_return,
            "replace_eligible": can_replace
        },
        "status": "Pending",
        "seller_id": str(user.get('id'))
    }
    
    inserted_id = Database.add_product_from_dict(product_data)
    
    if inserted_id:
        send_verification_to_discord(product_data, str(inserted_id))
        
    # 🔴 Fixed URL
    return redirect('/seller-dashboard')


# ৪. সেলার প্রোডাক্ট এডিট
@products_bp.route('/seller/edit/<product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    user = session.get('user')
    if not user: return redirect('/account')
    
    col = Database.get_collection("products")
    product = col.find_one({"_id": ObjectId(product_id)}) if col is not None else None
    
    # 🔴 সিকিউরিটি চেক: শুধু মালিকই এডিট করতে পারবে!
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
        
        col.update_one({"_id": ObjectId(product_id)}, {"$set": updated_data})
        # 🔴 Fixed URL
        return redirect('/seller-dashboard')
        
    return render_template('edit_product.html', product=product)
    
