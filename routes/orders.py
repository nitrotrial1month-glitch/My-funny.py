# ==========================================
# 🔍 ৪. Order Details Route (অর্ডারের বিস্তারিত তথ্য)
# ==========================================
@orders_bp.route('/order_details/<order_id>')
def order_details(order_id):
    user = session.get('user')
    if not user: return redirect('/account')
    
    col = Database.get_collection("orders")
    order = None
    
    if col is not None:
        try:
            order = col.find_one({"_id": ObjectId(order_id), "username": user.get('username')})
        except Exception as e:
            print(f"Fetch Details Database Error: {e}")
            
    if not order:
        return "<h1>Order not found!</h1><br><a href='/orders'>Go Back</a>", 404
        
    # নতুন সুন্দর টেমপ্লেটটি লোড করা হচ্ছে
    return render_template('order_details.html', order=order, user=user)

