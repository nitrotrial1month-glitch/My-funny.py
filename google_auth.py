
from flask import Blueprint

google_bp = Blueprint('google', __name__)

@google_bp.route('/login/google')
def login_google():
    return "🌐 Google Login API Setup will be done here soon."
  
