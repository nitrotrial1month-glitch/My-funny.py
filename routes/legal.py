from flask import Blueprint, render_template

# নতুন ব্লুপ্রিন্ট তৈরি করা হলো
legal_bp = Blueprint('legal', __name__)

# ==========================================
# 📄 Legal & Terms Pages Routes
# ==========================================

@legal_bp.route('/privacy-policy')
def privacy_policy():
    return render_template('legal/privacy_policy.html')

@legal_bp.route('/terms/seller')
def seller_terms():
    return render_template('legal/seller_terms.html')

@legal_bp.route('/terms/delivery')
def delivery_terms():
    return render_template('legal/delivery_terms.html')
  
