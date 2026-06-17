
from flask import Blueprint

apple_bp = Blueprint('apple', __name__)

@apple_bp.route('/login/apple')
def login_apple():
    return "🍏 Apple iOS Login API Setup will be done here soon."
  
