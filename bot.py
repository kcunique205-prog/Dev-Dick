# bot.py (Updated version)

import os
import json
import random
import string
import logging
from datetime import datetime
from threading import Lock
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Database Lock ---
db_lock = Lock()
DB_FILE = 'database.json'

# --- Database Helpers ---
def read_db():
    try:
        with db_lock:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except FileNotFoundError:
        logging.error(f"{DB_FILE} not found! Please create it.")
        # Create a default structure if it doesn't exist
        default_db = {"settings": {}, "resources": [], "users": {}, "live_drop_pool": []}
        write_db(default_db)
        return default_db
    except Exception as e:
        logging.error(f"Error reading database: {e}")
        return None

def write_db(data):
    try:
        with db_lock:
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Error writing to database: {e}")

# --- Telegram Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    logging.info(f"====== BOT: /start command received from user_id: {user_id}, username: {user.username} ======")
    
    try:
        db = read_db()
        if db is None:
            await update.message.reply_text("Sorry, there is a server-side database issue. Please try again later.")
            return

        if user_id not in db['users']:
            logging.info(f"BOT: New user found. Registering {user_id}.")
            access_code = ''.join(random.choices(string.digits, k=6))
            new_user = {
                "username": user.username or f"user_{user_id}",
                "access_code": access_code,
                "credits": 50,
                "is_premium": False,
                "last_login": None,
                "is_admin": False
            }
            db['users'][user_id] = new_user
            write_db(db)
            logging.info(f"BOT: User {user_id} saved to database. Sending access code.")
            
            await update.message.reply_text(
                f"🚀 Welcome to Dev-Deck, {user.first_name}!\n\n"
                f"You have been successfully registered.\n\n"
                f"Your personal access code is:\n\n`{access_code}`\n\n"
                f"Use this code to log in on the website.",
                parse_mode='Markdown'
            )
            logging.info(f"BOT: Access code sent successfully to {user_id}.")
        else:
            logging.info(f"BOT: Existing user {user_id} found. Sending existing code.")
            access_code = db['users'][user_id]['access_code']
            await update.message.reply_text(
                f"👋 Welcome back, {user.first_name}!\n\n"
                f"Your personal access code is still:\n\n`{access_code}`\n\n"
                f"Use this to log in.",
                parse_mode='Markdown'
            )
            logging.info(f"BOT: Existing code sent successfully to {user_id}.")
            
    except Exception as e:
        logging.error(f"====== BOT: CRITICAL ERROR in start function for user {user_id}: {e} ======")
        await update.message.reply_text("An unexpected error occurred. The admin has been notified.")


# --- Main Bot Runner ---
def run_bot():
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        logging.error("FATAL: TELEGRAM_BOT_TOKEN not found. Bot cannot start.")
        return
        
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    
    logging.info("====== BOT: Starting Telegram Bot Polling... ======")
    application.run_polling()
