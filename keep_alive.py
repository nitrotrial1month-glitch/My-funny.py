import os
from flask import Flask, render_template
from threading import Thread
from database import Database  # Importing the database

app = Flask(__name__)

@app.route('/')
def home():
    # 1. Add dummy products if the database is empty (only runs once)
    Database.add_dummy_products()
    
    # 2. Fetch all products from MongoDB
    products = Database.get_all_products()
    
    # 3. Send the products to the HTML page
    return render_template('index.html', products=products)

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    server = Thread(target=run)
    server.start()
    
