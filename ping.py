import telebot
import os
import requests
import time

# Load the bot token from environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Initialize the bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Function to ping a server using HTTP request
def http_ping(server):
    try:
        start_time = time.time()
        response = requests.get(f'http://{server}', timeout=5)
        end_time = time.time()

        # If the request is successful, return the response time
        if response.status_code == 200:
            return f"HTTP Ping to {server}: {round((end_time - start_time) * 1000, 2)} ms"
        else:
            return f"Failed to reach {server}, status code: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

# Define the /ping command to check server latency
@bot.message_handler(commands=['ping'])
def check_ping(message):
    try:
        # Extract the target server from the message (after the command)
        target = message.text.split()[1] if len(message.text.split()) > 1 else 'google.com'
        
        # Get the HTTP ping response
        response = http_ping(target)
        bot.reply_to(message, response)
    except IndexError:
        bot.reply_to(message, "Please specify a server, e.g., /ping example.com")
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

# Start the bot
bot.polling()
