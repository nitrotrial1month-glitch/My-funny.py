import os
from flask import Blueprint, render_template, request, session, jsonify, redirect
from database import Database

# 🔴 নতুন লাইব্রেরি ইমপোর্ট করা হলো
from google import genai

support_bp = Blueprint('support', __name__)

# Configure NEW Gemini AI (google-genai)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    try:
        # নতুন নিয়মে ক্লায়েন্ট তৈরি
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Client Init Error: {e}")
        client = None
else:
    client = None

# Routes
@support_bp.route('/chat_support/<order_id>')
def chat_support(order_id):
    user = session.get('user')
    if not user: return redirect('/account')
    return render_template('chat_support.html', order_id=order_id, user=user, is_owner=user.get('is_owner', False))

@support_bp.route('/help')
def general_help():
    user = session.get('user')
    if not user: return redirect('/account')
    return render_template('chat_support.html', order_id="General Inquiry", user=user, is_owner=user.get('is_owner', False))

@support_bp.route('/api/chat', methods=['POST'])
def api_chat():
    user = session.get('user')
    if not user: return jsonify({"reply": "Session expired. Please login again.", "options": []})

    data = request.json
    message = data.get('message', '').strip()
    order_id = data.get('order_id', '')

    # Magic Command
    if message.lower().startswith('/setnumber '):
        if user.get('is_owner'):
            number = message[11:].strip()
            try:
                col = Database.get_collection("config")
                if col is not None:
                    col.update_one({"_id": "main_config"}, {"$set": {"support_number": number}}, upsert=True)
                return jsonify({"reply": f"✅ **Success!** Support number updated to: **{number}**", "options": []})
            except Exception as e:
                return jsonify({"reply": f"Database Error: {str(e)}", "options": []})
        return jsonify({"reply": "🚫 **Access Denied!**", "options": []})

    if not client:
        return jsonify({"reply": "AI is currently sleeping... please contact admin.", "options": []})

    # Fetch Config Safely
    support_number = "Not set yet."
    try:
        col = Database.get_collection("config")
        if col is not None:
            config_data = col.find_one({"_id": "main_config"}) or {}
            support_number = config_data.get("support_number", "Not set yet.")
    except:
        pass

    order_display = f"#{order_id[:8].upper()}" if order_id != "General Inquiry" else "General Inquiry"

    system_prompt = f"""
    You are a polite assistant for 'inwear'.
    - If they ask to become a seller: Explain that they need to contact support or check the seller portal.
    - If they ask for human support: Give them this number: {support_number}.
    - Customer is asking about: {order_display}.
    - Customer message: {message}
    """

    try:
        # 🔴 নতুন লাইব্রেরি অনুযায়ী এআই কল করা হলো
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=system_prompt
        )
        reply_text = response.text.replace('\n', '<br>')
        suggestions = ["How to become a seller?", "Check Order Status", "Return Policy", "Refund Inquiry"]
        return jsonify({"reply": reply_text, "options": suggestions})
    except Exception as e:
        print(f"DEBUG ERROR: {e}")
        return jsonify({"reply": f"⚠️ API Error: {str(e)[:50]}", "options": []})
        
