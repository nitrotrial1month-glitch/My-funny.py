import os
import google.generativeai as genai
from flask import Blueprint, render_template, request, session, jsonify, redirect
from database import Database

support_bp = Blueprint('support', __name__)

# Configure Advanced AI (Google Gemini)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Using gemini-1.5-flash for super fast chat responses
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None


# =======================================================
# 🛒 ১. Order Specific Help Route (অর্ডারের জন্য হেল্প)
# =======================================================
@support_bp.route('/chat_support/<order_id>')
def chat_support(order_id):
    user = session.get('user')
    if not user: return redirect('/account')
    
    is_owner = user.get('is_owner', False)
    return render_template('chat_support.html', order_id=order_id, user=user, is_owner=is_owner)


# =======================================================
# 🌐 ২. General Help Route (সাধারণ হেল্প পেজ)
# =======================================================
@support_bp.route('/help')
def general_help():
    user = session.get('user')
    if not user: return redirect('/account')
    
    is_owner = user.get('is_owner', False)
    # AI চ্যাট পেজটিই ওপেন হবে, শুধু অর্ডারের জায়গায় General Inquiry লেখা থাকবে
    return render_template('chat_support.html', order_id="General Inquiry", user=user, is_owner=is_owner)


# =======================================================
# 🤖 ৩. AI Chat Backend Logic (এআই চ্যাটিং এপিআই)
# =======================================================
@support_bp.route('/api/chat', methods=['POST'])
def api_chat():
    user = session.get('user')
    if not user: return jsonify({"reply": "Session expired. Please login again."})

    data = request.json
    message = data.get('message', '').strip()
    order_id = data.get('order_id', '')

    # 🔴 MAGIC COMMAND: For Owners to set Support Number
    if message.lower().startswith('/setnumber '):
        if user.get('is_owner'):
            number = message[11:].strip()
            col = Database.get_collection("config")
            if col is not None:
                col.update_one({"_id": "main_config"}, {"$set": {"support_number": number}}, upsert=True)
            return jsonify({"reply": f"✅ **Success!** Customer support number has been updated to: **{number}**"})
        else:
            return jsonify({"reply": "🚫 **Access Denied!** You don't have Owner permission to use this command."})

    # 🤖 ADVANCED AI LOGIC (Google Gemini)
    if not model:
        return jsonify({"reply": "AI is currently sleeping because the API Key is missing. Please contact human support! 😴"})

    # Fetch the current support number from the database to feed to the AI
    col = Database.get_collection("config")
    config_data = col.find_one({"_id": "main_config"}) if col else {}
    support_number = config_data.get("support_number", "Not available yet. Please try later.")

    order_display = f"#{order_id[:8].upper()}" if order_id != "General Inquiry" else "General Inquiry"

    # Giving instructions to the AI on how to behave
    system_prompt = f"""
    You are a highly polite, helpful, and friendly customer support AI assistant for an e-commerce website named 'inwear'.
    The customer's name is {user.get('username')} and they are asking about: {order_display}.
    
    Strict Rules to follow:
    1. Keep your answers short, crisp, and use emojis naturally.
    2. If they ask to cancel: tell them to use the red 'Cancel Order' button on the 'My Orders' page.
    3. If they ask for returns or replacements: tell them to use the 'Return / Replace' button (valid for 7 days after delivery).
    4. If they ask about refunds: assure them it takes 3-5 business days to their original payment method.
    5. If they ask for human support, customer care, agent, or phone number, OR if you cannot solve their problem: You MUST give them this exact contact number: {support_number}.
    
    Customer message: {message}
    """

    try:
        # Generate intelligent response
        response = model.generate_content(system_prompt)
        # Convert newlines to HTML breaks so it looks good in the chatbox
        reply_text = response.text.replace('\n', '<br>')
        return jsonify({"reply": reply_text})
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return jsonify({"reply": "Sorry, my brain is taking a little rest right now due to a network glitch. Please try again in a minute! 🤖💤"})

