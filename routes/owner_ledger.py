from flask import Blueprint, request, render_template, redirect, flash
from database import Database

# auth.py থেকে role_required ইমপোর্ট করা হলো যাতে সিকিউরিটি ঠিক থাকে
from auth import role_required 

# এই ফাইলের জন্য নতুন Blueprint তৈরি করা হলো
owner_ledger_bp = Blueprint('owner_ledger', __name__)

@owner_ledger_bp.route('/owner/seller-ledger')
@role_required('owner')
def seller_ledger():
    # সার্চ বক্স থেকে সেলারের ইমেইল বা আইডি রিসিভ করা
    query = request.args.get('seller_query', '').strip()
    if not query:
        flash("Please enter a Seller ID or Email to search.")
        return redirect('/owner-dashboard')

    col_users = Database.get_collection("users")
    col_orders = Database.get_collection("orders")
    
    # ডেটাবেস থেকে আইডি বা ইমেইল দিয়ে সেলারকে খোঁজা
    seller = col_users.find_one({
        "$or": [
            {"email": query},
            {"discord_id": query},
            {"inwear_id": query}
        ],
        "role": "seller"
    })

    # যদি ওই নামে কোনো সেলার না থাকে
    if not seller:
        flash("Seller not found or they are not an active seller.")
        return redirect('/owner-dashboard')

    seller_id = seller.get('discord_id')
    
    # ওই নির্দিষ্ট সেলারের সব অর্ডারগুলো বের করা
    seller_orders = list(col_orders.find({"seller_id": str(seller_id)}))
    
    # সেলারের মোট ইনকাম, ইনওয়্যারের ১০% ফি এবং সেলারের পাওনা হিসাব করা
    total_sales = 0
    for o in seller_orders:
        if o.get('status') != 'Cancelled':
            total_sales += float(o.get('total_price', 0))
            
    total_commission = total_sales * 0.10
    total_payable = total_sales - total_commission

    # seller_ledger.html পেজে ডেটাগুলো পাঠিয়ে দেওয়া
    return render_template('seller_ledger.html', 
                           seller=seller, 
                           orders=seller_orders, 
                           total_sales=total_sales,
                           total_commission=total_commission,
                           total_payable=total_payable)
  
