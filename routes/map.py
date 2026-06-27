from flask import Blueprint, render_template, jsonify
from database import Database

# ১. ম্যাপের জন্য Blueprint তৈরি করা হলো
map_bp = Blueprint('map', __name__)

# ২. ইউজার যখন ওয়েবসাইটের /map লিংকে যাবে, তখন এই ফাংশনটি কাজ করবে
@map_bp.route('/map')
def show_map():
    return render_template('map.html')

# ৩. ডাটাবেস থেকে লোকেশন ডেটা ফ্রন্টএন্ডে (ম্যাপে) পাঠানোর জন্য API
@map_bp.route('/api/locations', methods=['GET'])
def get_locations():
    col = Database.get_collection("locations")
    if col is not None:
        # ডাটাবেস থেকে সব লোকেশন আনা হচ্ছে (ObjectId বাদ দিয়ে)
        locations = list(col.find({}, {"_id": 0})) 
        return jsonify(locations)
    return jsonify([]) # ডাটাবেস কানেক্ট না থাকলে খালি লিস্ট পাঠাবে
  
