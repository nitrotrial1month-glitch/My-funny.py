
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "<h1>Funny Bot is Online!</h1>"

def run():
    # Render পোর্ট 8080 বা এনভায়রনমেন্ট পোর্ট ব্যবহার করে
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
  
