import os
import google.generativeai as genai
from flask import Blueprint, render_template, request, session, jsonify, redirect
from database import Database

support_bp = Blueprint('support', __name__)

# Configure Gemini AI
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
    except:
        model = None
else:
    model = None

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
    if not user: return jsonify({"reply": "Session expired.", "options": []})

    data = request.json
    message = data.get('message', '').strip()
    order_id = data.get('order_id', '')

    # 1. Magic Command
    if message.lower().startswith('/setnumber '):
        if user.get('is_owner'):
            number = message[11:].strip()
            try:
                col = Database.get_collection("config")
                col.update_one({"_id": "main_config"}, {"$set": {"support_number": number}}, upsert=True)
                return jsonify({"reply": f"✅ Number updated to: {number}", "options": []})
            except Exception as e:
                return jsonify({"reply": f"Database Error: {str(e)}", "options": []})
        return jsonify({"reply": "🚫 Access Denied.", "options": []})

    # 2. AI Logic (Error Protected)
    if not model:
        return jsonify({"reply": "AI not configured properly.", "options": []})

    support_number = "Contact Admin"
    try:
        col = Database.get_collection("config")
        config_data = col.find_one({"_id": "main_config"})
        if config_data:
            support_number = config_data.get("support_number", "Not set")
    except:
        pass # Database problem ignored

    system_prompt = f"""
    You are an AI assistant for 'inwear'.
    - If asked about becoming a seller: Suggest checking the seller portal.
    - If asked for human support: Give them this number: {support_number}.
    - Keep answers short and friendly with emojis.
    - User is asking about: {order_id}.
    - Message: {message}
    """

    try:
        response = model.generate_content(system_prompt)
        reply_text = response.text.replace('\n', '<br>')
        return jsonify({
            "reply": reply_text, 
            "options": ["How to become a seller?", "Check Order Status", "Return Policy", "Refund Inquiry"]
        })
    except Exception as e:
        return jsonify({"reply": f"AI Error: {str(e)[:50]}", "options": []})
        
