import re
from flask import request, abort, session

# ========================================================
# 1. NoSQL Injection ও XSS প্রতিরোধ ফিল্টার
# ========================================================
def sanitize_input(data):
    """
    মঙ্গোডিবি-তে NoSQL Injection ($ অপারেটর) এবং 
    ফ্রন্টএন্ডে ক্ষতিকর স্ক্রিপ্ট (XSS) ইনজেকশন প্রতিরোধ করার ফাংশন।
    """
    if isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items() if not str(k).startswith('$')}
    elif isinstance(data, list):
        return [sanitize_input(v) for v in data]
    elif isinstance(data, str):
        # যদি কোনো ইনপুট মঙ্গো অপারেটর (যেমন: $ne, $gt) দিয়ে শুরু হয়, তা ব্লক বা ক্লিন করা
        if data.strip().startswith('$'):
            return ""
        # HTML ট্যাগ ফিল্টার করা (XSS প্রতিরোধ)
        clean_text = re.sub(r'<[^>]*?>', '', data)
        return clean_text
    return data


# ========================================================
# 2. ক্ষতিকর বা সন্দেহভাজন ইউআরএল রিকোয়েস্ট ফিল্টার
# ========================================================
def init_request_filter(app):
    @app.before_request
    def block_malicious_requests():
        # কাস্টম সেফটি চেক: কুয়েরি স্ট্রিং বা ইউআরএল চেক করা
        query_string = request.query_string.decode('utf-8').lower()
        
        # হ্যাকারদের ব্যবহৃত কমন প্যাটার্ন (যেমন: মঙ্গো অপারেটর, স্ক্রিপ্ট ট্যাগ)
        danger_patterns = [
            r"\{\s*\"\$", 
            r"\<script", 
            r"javascript:", 
            r"\$ne", 
            r"\$gt", 
            r"\$exists"
        ]
        
        for pattern in danger_patterns:
            if re.search(pattern, query_string):
                abort(403, description="Malicious activity detected and blocked by Wear By Me Security!")


# ========================================================
# 3. ব্রাউজার লেভেল সিকিউরিটি হেডার্স (Clickjacking & XSS Protection)
# ========================================================
def init_security_headers(app):
    @app.after_request
    def add_security_headers(response):
        # Clickjacking প্রতিরোধ (অন্য কেউ আপনার সাইটকে আইফ্রেমে লোড করে ডেটা চুরি করতে পারবে না)
        response.headers['X-Frame-Options'] = 'DENY'
        
        # XSS Protection ব্রাউজারে এনাবল করা
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # MIME Type Sniffing প্রতিরোধ
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Content Security Policy (CSP) - শুধুমাত্র অনুমোদিত সোর্স থেকে স্ক্রিপ্ট/ইমেজ লোড হবে
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://api.qrserver.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "img-src 'self' data: https://res.cloudinary.com https://cdn.discordapp.com https://img.icons8.com https://fonts.gstatic.com;"
        )
        
        # Strict Transport Security (HSTS - সাইটকে সবসময় HTTPS-এ চলতে বাধ্য করবে)
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response
      
