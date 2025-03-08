from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from datetime import datetime
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

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {'credits': 10, 'last_reset': str(datetime.now())}
        save_user_data()
    await update.message.reply_text(f'Hello! You have {user_data[user_id]["credits"]} credits. Send me a message!')

# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    user_name = update.message.from_user.full_name
    username = update.message.from_user.username
    user_message = update.message.text

    # Check if user is banned
    if user_id in user_data and user_data[user_id].get('banned', False):
        await update.message.reply_text('You are banned from using this bot.')
        return

    # Check if user has credits
    if not has_credits(user_id):
        await update.message.reply_text('You have no credits left. Please wait or purchase more.')
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
        await update.message.reply_text(ai_response)
    else:
        await update.message.reply_text('Sorry, I could not process your request.')

    # Log user activity to private channel
    log_message = f'User: {user_name} (@{username}, ID: {user_id})\nQuestion: {user_message}'
    log_to_channel(log_message)

def main() -> None:
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))  # Use filters.TEXT and filters.COMMAND

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()