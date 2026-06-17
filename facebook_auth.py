
from flask import Blueprint

facebook_bp = Blueprint('facebook', __name__)

@facebook_bp.route('/login/facebook')
def login_facebook():
    return "📘 Facebook Login API Setup will be done here soon."
  
