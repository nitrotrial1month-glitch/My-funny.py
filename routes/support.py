import os
import google.generativeai as genai
from flask import Blueprint, render_template, request, session, jsonify, redirect
from database import Database

support_bp = Blueprint('support', __name__)

# Configure Advanced AI (Google Gemini)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

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

    # Magic Command for Owner
    if message.lower().startswith('/setnumber '):
        if user.get('is_owner'):
            number = message[11:].strip()
            col = Database.get_collection("config")
            if col is not None:
                col.update_one({"_id": "main_config"}, {"$set": {"support_number": number}}, upsert=True)
            return jsonify({"reply": f"✅ **Success!** Customer support number updated to: **{number}**", "options": []})
        else:
            return jsonify({"reply": "🚫 **Access Denied!**", "options": []})

    if not model:
        return jsonify({"reply": "AI is currently unavailable.", "options": []})

    # Fetch Config Safely (Fixing the NotImplementedError)
    col = Database.get_collection("config")
    config_data = {}
    if col is not None:
        config_data = col.find_one({"_id": "main_config"}) or {}
    
    support_number = config_data.get("support_number", "Not set yet.")

    order_display = f"#{order_id[:8].upper()}" if order_id != "General Inquiry" else "General Inquiry"

    system_prompt = f"""
    You are a polite assistant for 'inwear'.
    - If they ask to become a seller: Explain that they need to contact support or check the seller portal.
    - If they ask for human support: Give them this number: {support_number}.
    - Customer is asking about: {order_display}.
    - Customer message: {message}
    """

    try:
        response = model.generate_content(system_prompt)
        reply_text = response.text.replace('\n', '<br>')
        suggestions = ["How to become a seller?", "Check Order Status", "Return Policy", "Refund Inquiry"]
        return jsonify({"reply": reply_text, "options": suggestions})
    except Exception as e:
        print(f"Error: {e}") # লগে এররটি দেখা যাবে
        return jsonify({"reply": "Network error, please try again.", "options": []})
        
