from flask import Blueprint, render_template, request, redirect, session, flash
from database import Database
from datetime import datetime

# (আপনার ফাইলে যদি ব্লুপ্রিন্ট আগে থেকেই থাকে, তবে নিচের লাইনটা লাগবে না)
# seller_bp = Blueprint('seller', __name__)

# ১. সেলারের ওয়ালেট পেজ দেখানো
@seller_bp.route('/seller/wallet')
def seller_wallet():
    user = session.get('user')
    if not user:
        return redirect('/login')

    col = Database.get_collection("users")
    seller_data = col.find_one({"discord_id": str(user['id'])})
    
    # উইথড্র হিস্ট্রি বের করা
    withdraw_col = Database.get_collection("withdrawals")
    history = list(withdraw_col.find({"seller_id": str(user['id'])}).sort("_id", -1))

    return render_template('seller_wallet.html', seller=seller_data, withdrawals=history)


# ২. নতুন UPI ID অ্যাড করা
@seller_bp.route('/seller/add_upi', methods=['POST'])
def add_upi():
    user = session.get('user')
    if not user:
        return redirect('/login')

    new_upi = request.form.get('new_upi')
    if new_upi:
        col = Database.get_collection("users")
        seller = col.find_one({"discord_id": str(user['id'])})
        
        upi_list = seller.get('upi_list', [])
        
        # যদি এটি প্রথম ইউপিআই হয়, তবে এটিকে ডিফল্ট করে দাও
        is_first = len(upi_list) == 0
        upi_list.append({"upi_id": new_upi, "is_default": is_first})
        
        col.update_one({"discord_id": str(user['id'])}, {"$set": {"upi_list": upi_list}})
        flash("UPI ID Added Successfully!")

    return redirect('/seller/wallet')


# ৩. নির্দিষ্ট UPI কে ডিফল্ট (Default) হিসেবে সেট করা
@seller_bp.route('/seller/set_default_upi/<int:index>', methods=['POST'])
def set_default_upi(index):
    user = session.get('user')
    if not user:
        return redirect('/login')

    col = Database.get_collection("users")
    seller = col.find_one({"discord_id": str(user['id'])})
    upi_list = seller.get('upi_list', [])

    if 0 <= index < len(upi_list):
        # সব ইউপিআই থেকে ডিফল্ট সরিয়ে দাও
        for upi in upi_list:
            upi['is_default'] = False
        # শুধু সিলেক্ট করাটা ডিফল্ট করো
        upi_list[index]['is_default'] = True
        
        col.update_one({"discord_id": str(user['id'])}, {"$set": {"upi_list": upi_list}})

    return redirect('/seller/wallet')


# ৪. উইথড্র রিকোয়েস্ট (Payout) পাঠানো
@seller_bp.route('/seller/withdraw', methods=['POST'])
def request_withdrawal():
    user = session.get('user')
    if not user:
        return redirect('/login')

    amount = float(request.form.get('amount', 0))
    upi_id = request.form.get('upi_id')

    col = Database.get_collection("users")
    seller = col.find_one({"discord_id": str(user['id'])})
    current_balance = float(seller.get('wallet_balance', 0.0))

    # চেক করা হচ্ছে ইউজারের কাছে পর্যাপ্ত ব্যালেন্স আছে কি না
    if amount >= 100 and amount <= current_balance:
        # ব্যালেন্স কাটা হচ্ছে
        new_balance = current_balance - amount
        col.update_one({"discord_id": str(user['id'])}, {"$set": {"wallet_balance": new_balance}})

        # রিকোয়েস্ট ডেটাবেসে সেভ করা হচ্ছে
        withdraw_col = Database.get_collection("withdrawals")
        withdraw_col.insert_one({
            "seller_id": str(user['id']),
            "seller_name": seller.get("name", "Unknown"),
            "amount": amount,
            "upi_id": upi_id,
            "status": "Pending",
            "date": datetime.now().strftime("%Y-%m-%d %I:%M %p")
        })
        flash(f"Withdrawal request of ₹{amount} submitted successfully!")
    else:
        flash("Invalid amount or insufficient balance.")

    return redirect('/seller/wallet')
  
