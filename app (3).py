# (Paste the exact same app.py code from the previous response here)
import os
import json
import logging
from flask import Flask, render_template, request, jsonify, abort
from threading import Lock
import telegram
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = Flask(__name__, template_folder='.')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-super-secret-key-for-local-testing')

ADMIN_USER = os.environ.get('ADMIN_USER', 'diwas')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '@diwazzbro')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

DB_FILE = 'database.json'
db_lock = Lock()

bot = None
if TELEGRAM_BOT_TOKEN:
    try:
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        bot_info = bot.get_me()
        logging.info(f"Telegram Bot '{bot_info.first_name}' initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize Telegram Bot: {e}")
        bot = None

def send_telegram_notification(message):
    if not bot or not TELEGRAM_CHAT_ID:
        logging.warning("Telegram Bot not configured. Skipping notification.")
        return
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode='Markdown')
        logging.info(f"Sent Telegram notification to {TELEGRAM_CHAT_ID}")
    except Exception as e:
        logging.error(f"Primary method failed: {e}. Trying fallback...")
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                logging.info("Sent notification via fallback HTTPS method.")
            else:
                logging.error(f"Fallback method also failed. Status: {response.status_code}, Response: {response.text}")
        except Exception as fallback_e:
            logging.error(f"Fallback method critical failure: {fallback_e}")

def read_db():
    with db_lock:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

def write_db(data):
    with db_lock:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

@app.route('/')
def index(): return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    db = read_db()
    if data and data.get('code') == db['settings']['access_code']:
        db['stats']['logins'] = db['stats'].get('logins', 0) + 1
        write_db(db)
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent', 'Unknown')
        send_telegram_notification(f"✅ *New User Login!*\n\n*Code Used*: `{data.get('code')}`\n*IP Address*: `{ip_address}`\n*Device*: `{user_agent}`")
        return jsonify({'message': 'Success'}), 200
    send_telegram_notification(f"❌ *Failed Login Attempt!*\n\n*Code Entered*: `{data.get('code')}`")
    return jsonify({'message': 'Invalid code'}), 401

@app.route('/api/data')
def get_api_data(): return jsonify(read_db())

@app.route('/admin')
def admin_panel(): return render_template('admin.html')

@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    if data and data.get('user') == ADMIN_USER and data.get('pass') == ADMIN_PASSWORD:
        db = read_db()
        db['stats']['admin_logins'] = db['stats'].get('admin_logins', 0) + 1
        write_db(db)
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        send_telegram_notification(f"👑 *ADMIN PANEL ACCESS GRANTED!*\n\n*User*: `{data.get('user')}`\n*IP*: `{ip_address}`")
        return jsonify({'message': 'Admin login successful'}), 200
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    send_telegram_notification(f"🚨 *FAILED ADMIN LOGIN ATTEMPT!*\n\n*User*: `{data.get('user')}`\n*Password*: `{data.get('pass')}`\n*IP*: `{ip_address}`")
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/admin/resource', methods=['POST'])
def add_or_update_resource():
    res_data = request.get_json()
    if not res_data: abort(400)
    db = read_db()
    res_id = res_data.get('id')
    if res_id:
        found = False
        for i, res in enumerate(db['resources']):
            if res['id'] == res_id:
                db['resources'][i] = res_data; found = True; break
        if not found: abort(404)
        message = f"✏️ *Resource Updated:*\n`{res_data['title']}`"
    else:
        new_id = max([r['id'] for r in db['resources']] + [0]) + 1
        res_data['id'] = new_id
        db['resources'].append(res_data)
        message = f"✨ *New Resource Added:*\n`{res_data['title']}`"
    write_db(db)
    send_telegram_notification(message)
    return jsonify(res_data), 200

@app.route('/admin/resource/<int:res_id>', methods=['DELETE'])
def delete_resource(res_id):
    db = read_db()
    res_to_del = next((res for res in db['resources'] if res['id'] == res_id), None)
    if res_to_del:
        db['resources'] = [res for res in db['resources'] if res['id'] != res_id]
        write_db(db)
        send_telegram_notification(f"🗑️ *Resource Deleted:*\n`{res_to_del['title']}`")
        return jsonify({'message': 'Deleted'}), 200
    return jsonify({'message': 'Not Found'}), 404

@app.route('/admin/settings', methods=['POST'])
def update_settings():
    settings_data = request.get_json()
    db = read_db()
    db['settings'].update(settings_data)
    write_db(db)
    pretty_settings = json.dumps(settings_data, indent=2)
    send_telegram_notification(f"⚙️ *Site Settings Updated!*\n```json\n{pretty_settings}\n```")
    return jsonify(db['settings']), 200

if __name__ == '__main__':
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        logging.warning("CRITICAL: Bot credentials missing.")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)