import os
import json
import logging
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, abort
from threading import Thread
from bot import run_bot, read_db, write_db, db_lock

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__, template_folder='.')

# --- API Endpoints ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    code = data.get('code')
    
    with db_lock:
        db = read_db()
        user_id = None
        for uid, user_data in db['users'].items():
            if user_data.get('access_code') == code:
                user_id = uid
                break

        if not user_id:
            return jsonify({"error": "Invalid access code"}), 401
        
        # Check for daily login credits
        now = datetime.utcnow()
        last_login_str = db['users'][user_id]['last_login']
        if last_login_str:
            last_login = datetime.fromisoformat(last_login_str.replace('Z', ''))
            if now - last_login > timedelta(days=1):
                db['users'][user_id]['credits'] += 25 # Daily bonus
        
        db['users'][user_id]['last_login'] = now.isoformat() + 'Z'
        write_db(db)

        # Return user data for session
        user_session_data = {
            "userId": user_id,
            "username": db['users'][user_id]['username'],
            "credits": db['users'][user_id]['credits'],
            "isPremium": db['users'][user_id]['is_premium'],
            "isAdmin": db['users'][user_id]['is_admin']
        }
        return jsonify(user_session_data), 200

@app.route('/api/data')
def get_data():
    return jsonify(read_db())

@app.route('/api/live-drop')
def live_drop():
    db = read_db()
    return jsonify({"cc": random.choice(db['live_drop_pool'])})

# --- Admin Endpoints (Simplified, needs token auth in real app) ---
@app.route('/api/admin/resource', methods=['POST'])
def manage_resource():
    data = request.get_json()
    db = read_db()
    # Logic for add/edit resource
    write_db(db)
    return jsonify({"status": "success"}), 200

# Add more admin endpoints for settings, users, etc.

# --- Main Execution ---
if __name__ == '__main__':
    # Run Telegram bot in a separate thread
    bot_thread = Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Run Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
