# keep_alive.py
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and running!"

def run():
    # রেন্ডার যেকোনো পোর্ট অ্যাসাইন করতে পারে, তবে ডিফল্ট হিসেবে ৮০৮০ রাখা হলো
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
  
