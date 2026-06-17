import os
from flask import Flask
from threading import Thread

app = Flask(__name__)

# This route serves your website's home page
@app.route('/')
def home():
    # You can later replace this text with your actual HTML template
    return "Nova E-commerce Website and Discord Bot are running perfectly!"

def run():
    # Render assigns a dynamic port, so we fetch it from the environment variables
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    """Starts the web server on a separate thread to keep the bot alive"""
    server = Thread(target=run)
    server.start()
    
