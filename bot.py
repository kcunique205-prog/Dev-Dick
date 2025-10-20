import os
import json
import random
import string
import logging
from datetime import datetime
from threading import Lock
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Database Lock (Shared with app.py) ---
db_lock = Lock()
DB_FILE = 'database.json'

# --- Database Helpers ---
def read_db():
    with db_lock:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

def write_db(data):
    with db_lock:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

# --- Telegram Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    logging.info(f"Bot command /start received from user_id: {user_id}")
    
    db = read_db()
    
    if user_id not in db['users']:
        # New user registration
        access_code = ''.join(random.choices(string.digits, k=6))
        new_user = {
            "username": user.username or f"user_{user_id}",
            "access_code": access_code,
            "credits": 50, # Welcome credits
            "is_premium": False,
            "last_login": None,
            "is_admin": False # Only admin can change this
        }
        db['users'][user_id] = new_user
        write_db(db)
        
        await update.message.reply_text(
            f"🚀 Welcome to Dev-Deck, {user.first_name}!\n\n"
            f"You have been successfully registered.\n\n"
            f"Your personal access code is:\n\n`{access_code}`\n\n"
            f"Use this code to log in on the website. Do not share it.",
            parse_mode='Markdown'
        )
    else:
        # Existing user
        access_code = db['users'][user_id]['access_code']
        await update.message.reply_text(
            f"👋 Welcome back, {user.first_name}!\n\n"
            f"Your personal access code is still:\n\n`{access_code}`\n\n"
            f"Use this to log in on the website.",
            parse_mode='Markdown'
        )

# --- Main Bot Runner ---
def run_bot():
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        logging.error("TELEGRAM_BOT_TOKEN not found in environment. Bot cannot start.")
        return
        
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    
    logging.info("Starting Telegram Bot Polling...")
    application.run_polling()
