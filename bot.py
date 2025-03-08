from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackContext
import requests
from datetime import datetime, timedelta
import json

# Replace with your Telegram bot token
TELEGRAM_BOT_TOKEN = '7946006638:AAEL5aQ_lz7oBjq2ER2LPHnKMD_AnQc0FRM'
# Replace with your Together.ai API key
TOGETHER_API_KEY = '1b23a2f4631f9f35380f61132b67e0b26954ef4546491293d11e706f241d2055'
# Replace with your private channel ID
PRIVATE_CHANNEL_ID = '-1002426409041'
# Sudo user ID
SUDO_USER_ID = 2114237158

# User data storage
user_data = {}

# Load user data from file (if exists)
try:
    with open('user_data.json', 'r') as f:
        user_data = json.load(f)
except FileNotFoundError:
    pass

# Save user data to file
def save_user_data():
    with open('user_data.json', 'w') as f:
        json.dump(user_data, f)

# Check if user has enough credits
def has_credits(user_id):
    if user_id not in user_data:
        return False
    if user_data[user_id]['credits'] <= 0:
        return False
    return True

# Deduct credits from user
def deduct_credits(user_id):
    if user_id in user_data:
        user_data[user_id]['credits'] -= 1
        save_user_data()

# Add credits to user
def add_credits(user_id, credits):
    if user_id in user_data:
        user_data[user_id]['credits'] += credits
        save_user_data()

# Reset credits every 24 hours
def reset_credits():
    for user_id in user_data:
        user_data[user_id]['credits'] = 10
    save_user_data()

# Send message to private channel
def log_to_channel(message):
    requests.post(
        f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage',
        json={'chat_id': PRIVATE_CHANNEL_ID, 'text': message}
    )

# Start command
def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {'credits': 10, 'last_reset': str(datetime.now())}
        save_user_data()
    update.message.reply_text(f'Hello! You have {user_data[user_id]["credits"]} credits. Send me a message!')

# Handle messages
def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user_name = update.message.from_user.full_name
    username = update.message.from_user.username
    user_message = update.message.text

    # Check if user is banned
    if user_id in user_data and user_data[user_id].get('banned', False):
        update.message.reply_text('You are banned from using this bot.')
        return

    # Check if user has credits
    if not has_credits(user_id):
        update.message.reply_text('You have no credits left. Please wait or purchase more.')
        return

    # Deduct credits
    deduct_credits(user_id)

    # Call Together.ai API
    headers = {
        'Authorization': f'Bearer {TOGETHER_API_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        'prompt': user_message,
        'max_tokens': 100  # Adjust as needed
    }
    response = requests.post('https://api.together.xyz/v1/completions', headers=headers, json=data)
    if response.status_code == 200:
        ai_response = response.json().get('choices', [{}])[0].get('text', 'No response from AI.')
        update.message.reply_text(ai_response)
    else:
        update.message.reply_text('Sorry, I could not process your request.')

    # Log user activity to private channel
    log_message = f'User: {user_name} (@{username}, ID: {user_id})\nQuestion: {user_message}'
    log_to_channel(log_message)

# Ban user command (sudo only)
def ban_user(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id != SUDO_USER_ID:
        update.message.reply_text('You are not authorized to use this command.')
        return

    target_user_id = int(context.args[0])
    if target_user_id in user_data:
        user_data[target_user_id]['banned'] = True
        save_user_data()
        update.message.reply_text(f'User {target_user_id} has been banned.')
    else:
        update.message.reply_text(f'User {target_user_id} not found.')

# Unban user command (sudo only)
def unban_user(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id != SUDO_USER_ID:
        update.message.reply_text('You are not authorized to use this command.')
        return

    target_user_id = int(context.args[0])
    if target_user_id in user_data:
        user_data[target_user_id]['banned'] = False
        save_user_data()
        update.message.reply_text(f'User {target_user_id} has been unbanned.')
    else:
        update.message.reply_text(f'User {target_user_id} not found.')

# Gift credits command (sudo only)
def gift_credits(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id != SUDO_USER_ID:
        update.message.reply_text('You are not authorized to use this command.')
        return

    target_user_id = int(context.args[0])
    credits = int(context.args[1])
    add_credits(target_user_id, credits)
    update.message.reply_text(f'Gifted {credits} credits to user {target_user_id}.')

# Buy credits command
def buy_credits(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    update.message.reply_text(
        'To buy credits, send stars to this bot. 1 star = 1 credit.\n'
        'After sending stars, your credits will be automatically added.'
    )

# Handle successful star payments
def handle_star_payment(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    stars_received = update.message.successful_payment.total_amount // 100  # Convert to stars
    add_credits(user_id, stars_received)
    update.message.reply_text(f'Thank you! {stars_received} credits have been added to your account.')

def main() -> None:
    updater = Updater(TELEGRAM_BOT_TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("ban", ban_user))
    dispatcher.add_handler(CommandHandler("unban", unban_user))
    dispatcher.add_handler(CommandHandler("gift", gift_credits))
    dispatcher.add_handler(CommandHandler("buy", buy_credits))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dispatcher.add_handler(MessageHandler(Filters.successful_payment, handle_star_payment))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
