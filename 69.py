import os
import requests
import json
import telebot
import time
from msal import PublicClientApplication
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import pyshorteners
from dotenv import load_dotenv
import pytz
import logging
from functools import wraps
from telegraph import Telegraph
from datetime import timedelta
from telebot.types import Message
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
# ----------------------------#
#       Configuration         #
# ----------------------------#

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detailed logs
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_debug.log"),
        logging.StreamHandler()
    ]
)

# Load environment variables from .env file
load_dotenv()

# Set up credentials from environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GRAPH_CLIENT_ID = os.getenv('GRAPH_CLIENT_ID')
GRAPH_TENANT_ID = os.getenv('GRAPH_TENANT_ID')
TOKEN_FILE = "user_token.txt"  # File to store the access token

# Validate environment variables
if not TELEGRAM_BOT_TOKEN:
    logging.error("TELEGRAM_BOT_TOKEN is not set in the environment variables.")
    exit(1)
if not GRAPH_CLIENT_ID:
    logging.error("GRAPH_CLIENT_ID is not set in the environment variables.")
    exit(1)
if not GRAPH_TENANT_ID:
    logging.error("GRAPH_TENANT_ID is not set in the environment variables.")
    exit(1)

# Authorized users for sensitive commands
AUTHORIZED_USERS = [1585904762, 987654321]  # Replace with actual Telegram user IDs

# Initialize Telegraph
telegraph = Telegraph()
telegraph.create_account(short_name='MyBot')  # Replace 'MyBot' with your preferred short name
start_time = time.time()

# ----------------------------#
#      Initialize Bot         #
# ----------------------------#

# Set up Telegram bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# MSAL public client for device code flow
msal_app = PublicClientApplication(
    GRAPH_CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{GRAPH_TENANT_ID}"
)

# In-memory user sessions
user_sessions = {}

# ----------------------------#
#     Access Restriction      #
# ----------------------------#


TARGET_GROUP_CHAT_ID = -1001983462200
admin_id = ["1585904762"]
USER_FILE = "users.txt"
ADMINS = [1585904762, 987654321]  # Add your Telegram user IDs here

def is_admin(user_id):
    """ Check if the user is an admin. """
    return user_id in ADMINS

def save_user_id(user_id):
    if not os.path.exists('users.txt'):
        with open('users.txt', 'w') as f:
            f.write('')  # Create an empty file

    with open('users.txt', 'r') as f:
        users = f.read().splitlines()

    if str(user_id) not in users:
        with open('users.txt', 'a') as f:
            f.write(f"{user_id}\n")

@bot.message_handler(commands=['users'])
def send_users_file(message):
    user_id = message.chat.id
    if not is_admin(user_id):
        bot.send_message(user_id, "Access denied: Admins only.")
        return

    if os.path.exists('users.txt'):
        with open('users.txt', 'rb') as f:
            bot.send_document(user_id, f)
    else:
        bot.send_message(user_id, "No users found.")

@bot.message_handler(commands=['telegraph_users'])
def send_users_telegraph_link(message):
    user_id = message.chat.id
    if not is_admin(user_id):
        bot.send_message(user_id, "Access denied: Admins only.")
        return

    if os.path.exists('users.txt'):
        with open('users.txt', 'r') as f:
            users = f.read()

        # Upload users to Telegraph
        response = telegraph.create_page(
            title='List of Users',
            html_content=f"<pre>{users}</pre>"
        )
        # Send the Telegraph link to the admin
        telegraph_url = f"https://telegra.ph/{response['path']}"
        bot.send_message(user_id, f"List of users uploaded to Telegraph: {telegraph_url}")
    else:
        bot.send_message(user_id, "No users found.")

def save_user_id(user_id):
    # Check if the users.txt file exists, if not create one
    if not os.path.exists('users.txt'):
        with open('users.txt', 'w') as f:
            f.write('')  # Create an empty file

    # Read existing user IDs
    with open('users.txt', 'r') as f:
        users = f.read().splitlines()

    # Check if the user ID is already in the file
    if str(user_id) not in users:
        # If not, append the user ID to the file
        with open('users.txt', 'a') as f:
            f.write(f"{user_id}\n")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    username = message.from_user.username or message.from_user.first_name

    # Save the user ID (no duplicates)
    save_user_id(user_id)

    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

    my_files_btn = KeyboardButton('/myfiles')
    tutorial_btn = KeyboardButton('/tutorial')  
    about_btn = KeyboardButton('/about')
    help_btn = KeyboardButton('/help')

    markup.add(my_files_btn, tutorial_btn, about_btn, help_btn)

    bot.send_message(user_id, f"@{username} Welcome! Use the buttons below to interact with me:", reply_markup=markup)

@bot.message_handler(commands=['tutorial'])
def handle_tutorial(message):
    user_id = message.chat.id

    guide_message = """
*You can use the same method on any OS, including Android, Android TV, Windows, iOS, Apple TV, Mac, and Linux. The links also support downloads—simply paste them into Chrome (Chrome browser is recommended)

VLC for Android: ([click me](https://play.google.com/store/apps/details?id=org.videolan.vlc)) 
VLC's Official Site: ([click me](https://www.videolan.org/vlc/)) 
"""

    video_chat_id = -1001983462200  
    video_message_id = 312  

    bot.forward_message(user_id, video_chat_id, video_message_id)
    bot.send_message(user_id, guide_message, parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def send_help(message: Message):
    try:

        bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=TARGET_GROUP_CHAT_ID,
            message_id=340
        )
    except Exception as e:
        bot.reply_to(message, f"Error copying help message: {str(e)}")

@bot.message_handler(commands=['about'])
def handle_about(message):
    about_message = """Welcome to the Bot
Created by @RCMARIO, this bot is designed to provide free links to web series, movies, and anime for download and streaming. Whether you're looking for the latest releases or classic content, this bot has you covered.

To get started, simply type /helo to view a commands on how to access and use the bot’s features.

VERSION:- 13

THIS BOT IS CURRENTLY IN BETA, AND IT'S NOT THE FINAL VERSION. WE ARE CONTINUOUSLY IMPROVING AND WILL BE RELEASING THE FINAL VERSION SOON."
"""

    bot.send_message(message.chat.id, about_message) 
    
@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        command = message.text.split(maxsplit=1)
        if len(command) > 1:
            message_to_broadcast = "Message To All Users By Admin:\n\n" + command[1]
            with open(USER_FILE, "r") as file:
                user_ids = file.read().splitlines()
                for user_id in user_ids:
                    try:
                        bot.send_message(user_id, message_to_broadcast)
                    except Exception as e:
                        print(f"Failed to send broadcast message to user {user_id}: {str(e)}")
            response = "Broadcast Message Sent Successfully To All Users."
        else:
            response = "Please Provide A Message To Broadcast."
    else:
        response = "Access denied: Admins only."

    bot.reply_to(message, response)

@bot.message_handler(commands=['uptime'])
def handle_uptime(message):
    current_time = time.time()
    uptime_seconds = int(current_time - start_time)
    uptime_str = str(timedelta(seconds=uptime_seconds))

    bot.send_message(message.chat.id, f"Bot uptime: {uptime_str}")

@bot.message_handler(commands=['users'])
def send_users_file(message):
    user_id = message.chat.id
    if not is_admin(user_id):
        bot.send_message(user_id, "Access denied: Admins only.")
        return

    if os.path.exists('users.txt'):
        with open('users.txt', 'rb') as f:
            bot.send_document(user_id, f)
    else:
        bot.send_message(user_id, "No users found.")

@bot.message_handler(commands=['telegraph_users'])
def send_users_telegraph_link(message):
    user_id = message.chat.id
    if not is_admin(user_id):
        bot.send_message(user_id, "Access denied: Admins only.")
        return

    if os.path.exists('users.txt'):
        with open('users.txt', 'r') as f:
            users = f.read()

        # Upload users to Telegraph
        response = telegraph.create_page(
            title='List of Users',
            html_content=f"<pre>{users}</pre>"
        )
        # Send the Telegraph link to the admin
        telegraph_url = f"https://telegra.ph/{response['path']}"
        bot.send_message(user_id, f"List of users uploaded to Telegraph: {telegraph_url}")
    else:
        bot.send_message(user_id, "No users found.")

def save_user_id(user_id):
    # Check if the users.txt file exists, if not create one
    if not os.path.exists('users.txt'):
        with open('users.txt', 'w') as f:
            f.write('')  # Create an empty file

    # Read existing user IDs
    with open('users.txt', 'r') as f:
        users = f.read().splitlines()

    # Check if the user ID is already in the file
    if str(user_id) not in users:
        # If not, append the user ID to the file
        with open('users.txt', 'a') as f:
            f.write(f"{user_id}\n")

def restricted(func):
    """
    Decorator to restrict access to certain bot commands to authorized users only.
    """
    @wraps(func)
    def wrapped(message, *args, **kwargs):
        user_id = message.from_user.id
        if user_id not in AUTHORIZED_USERS:
            bot.reply_to(message, "Access denied: Admins only.")
            logging.warning(f"Unauthorized access attempt by user {user_id}.")
            return
        return func(message, *args, **kwargs)
    return wrapped

# ----------------------------#
#        Helper Functions     #
# ----------------------------#

def save_token_to_file(token_data):
    """
    Saves token data to a file with an expiry timestamp.
    """
    token_data['expires_at'] = (datetime.now() + timedelta(seconds=token_data['expires_in'])).timestamp()
    try:
        with open(TOKEN_FILE, "w") as token_file:
            json.dump(token_data, token_file)
        logging.info("Token saved successfully.")
    except Exception as e:
        logging.error(f"Error saving token to file: {e}")

def load_token_from_file():
    """
    Loads token data from a file if it's still valid. Attempts to refresh if expired.
    """
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as token_file:
                token_data = json.load(token_file)
                if datetime.now().timestamp() < token_data['expires_at']:
                    logging.info("Loaded valid token from file.")
                    return token_data
                elif 'refresh_token' in token_data:
                    # Token expired, use the refresh token to get a new access token
                    logging.info("Token expired. Attempting to refresh token.")
                    new_token_response = msal_app.acquire_token_by_refresh_token(
                        token_data['refresh_token'],
                        scopes=["Files.ReadWrite.All"]
                    )
                    if "access_token" in new_token_response:
                        save_token_to_file(new_token_response)
                        logging.info("Token refreshed successfully.")
                        return new_token_response
                    else:
                        logging.warning("Failed to refresh token.")
        except Exception as e:
            logging.error(f"Error loading token from file: {e}")
    else:
        logging.info("No token file found.")
    return None

def authenticate_user(user_id):
    """
    Authenticates the user using Microsoft Graph device code flow.
    """
    try:
        # Include the offline_access scope to allow for token refresh
        flow = msal_app.initiate_device_flow(scopes=["Files.ReadWrite.All"])

        if 'user_code' not in flow:
            logging.error("Failed to create device flow. Check app permissions.")
            bot.send_message(user_id, "Authentication error. Please contact the administrator.")
            return

        verification_message = f"Go to {flow['verification_uri']} and enter the code: {flow['user_code']}"
        bot.send_message(user_id, verification_message)
        logging.info(f"Sent authentication message to user {user_id}.")

        token_response = msal_app.acquire_token_by_device_flow(flow)

        if "access_token" in token_response:
            save_token_to_file(token_response)
            bot.send_message(user_id, "You have been successfully authenticated!")
            logging.info(f"User {user_id} authenticated successfully.")
        else:
            bot.send_message(user_id, "Authentication failed, please try again.")
            logging.warning(f"Authentication failed for user {user_id}.")
    except Exception as e:
        logging.error(f"Exception during authentication for user {user_id}: {e}")
        bot.send_message(user_id, "An error occurred during authentication. Please try again later.")

def get_files(access_token, folder_id=None):
    """
    Fetches files from OneDrive using Microsoft Graph API.
    """
    try:
        if folder_id:
            url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}/children"
        else:
            url = "https://graph.microsoft.com/v1.0/me/drive/root/children"

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            logging.info(f"Fetched files from folder ID: {folder_id if folder_id else 'root'}.")
            return response.json().get('value', [])
        else:
            logging.error(f"Error fetching files: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logging.error(f"Exception in get_files: {e}")
        return None

def find_folder_id_by_name(files, folder_name):
    """
    Finds the folder ID by its name from a list of files/folders.
    """
    for file in files:
        if file.get('folder', None) and file['name'].lower() == folder_name.lower():
            logging.info(f"Found folder '{folder_name}' with ID: {file['id']}")
            return file['id']
    logging.warning(f"Folder '{folder_name}' not found.")
    return None

def generate_navigation_buttons(folder_id, page, access_token):
    """
    Generates inline keyboard buttons for file navigation.
    """
    try:
        files = get_files(access_token, folder_id)
        if not files:
            return None

        markup = InlineKeyboardMarkup()

        page_size = 10
        start = page * page_size
        end = start + page_size

        for file in files[start:end]:
            if file.get('folder', None):
                markup.add(InlineKeyboardButton(text=f"📁 {file['name']}", callback_data=f"folder:{file['id']}:0"))
            else:
                markup.add(InlineKeyboardButton(text=f"💾 {file['name']}", callback_data=f"file:{file['id']}:0"))

        # Create navigation buttons
        navigation_buttons = []
        if page > 0:
            navigation_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"navigate:{folder_id}:{page-1}"))
        if end < len(files):
            navigation_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"navigate:{folder_id}:{page+1}"))

        # Create home and all links buttons
        home_button = InlineKeyboardButton("🏠 Home", callback_data=f"home:{folder_id}:0")
        all_links_button = InlineKeyboardButton("Generate All Links 🔗", callback_data=f"getalllinks:{folder_id}:0")

        # Add navigation, home, and all links buttons in a single row
        if navigation_buttons:
            markup.row(*navigation_buttons)
        markup.row(all_links_button, home_button)

        return markup
    except Exception as e:
        logging.error(f"Exception in generate_navigation_buttons: {e}")
        return None

def parse_callback_data(callback_data):
    """
    Parses callback data into action, item_id, and page.
    """
    parts = callback_data.split(":")
    if len(parts) == 3:
        action, item_id, page = parts[0], parts[1], int(parts[2])
        return action, item_id, page
    else:
        logging.warning(f"Invalid callback data format: {callback_data}")
        return None, None, 0

def create_share_link(file_id, access_token):
    """
    Creates a shareable link for a specific file.
    """
    try:
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/permissions"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            permissions = response.json().get('value', [])
            for permission in permissions:
                link = permission.get('link', {}).get('webUrl')
                if link and ':v:' in link:
                    clean_link = link.split('?')[0] + "?download=1"
                    return shorten_url(clean_link)

        # If no existing link, create a new one
        create_link_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/createLink"
        body = {
            'type': 'view',
            'scope': 'anonymous'
        }

        create_link_response = requests.post(create_link_url, headers=headers, json=body)

        if create_link_response.status_code == 201:
            link = create_link_response.json().get('link', {}).get('webUrl', None)
            if link and ':v:' in link:
                clean_link = link.split('?')[0] + "?download=1"
                return shorten_url(clean_link)

    except Exception as e:
        logging.error(f"Exception in create_share_link: {e}")
    return None

def shorten_url(url):
    """
    Shortens a URL using TinyURL.
    """
    try:
        s = pyshorteners.Shortener()
        return s.tinyurl.short(url)
    except Exception as e:
        logging.error(f"Exception in shorten_url: {e}")
        return url  # Return original URL if shortening fails

def generate_file_link(file_id, access_token, user_id, username):
    """
    Generates a shareable link for a specific file and sends it to the user.
    """
    try:
        # Fetch the file metadata (to get the file name)
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            file_metadata = response.json()
            file_name = file_metadata['name']
            link = create_share_link(file_id, access_token)

            if link:
                bot.send_message(user_id, f"File link for {file_name}: {link}")
                log_file_link(user_id, username, file_name)  # Log the file link generation
            else:
                bot.send_message(user_id, "Failed to generate file link.")
        else:
            bot.send_message(user_id, "Error retrieving file details.")
            logging.error(f"Error retrieving file details: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Exception in generate_file_link: {e}")
        bot.send_message(user_id, "An error occurred while generating the file link.")

def generate_all_file_links(folder_id, access_token, user_id, username):
    """
    Generates shareable links for all files in a folder and sends them to the user.
    """
    try:
        files = get_files(access_token, folder_id)
        if files:
            links = []
            for file in files:
                if not file.get('folder', None):  # Skip folders, only get files
                    link = create_share_link(file['id'], access_token)
                    if link:
                        links.append(f"{file['name']}: {link}")
                        log_file_link(user_id, username, file['name'])  # Log the file link generation

            if links:
                # Send links in chunks to avoid exceeding Telegram's message size limits
                message_chunks = [links[i:i + 10] for i in range(0, len(links), 10)]
                for chunk in message_chunks:
                    bot.send_message(user_id, "\n".join(chunk))
                logging.info(f"Sent all file links to user {user_id}.")
            else:
                bot.send_message(user_id, "No links found or failed to generate links.")
        else:
            bot.send_message(user_id, "No files found in the folder.")
    except Exception as e:
        logging.error(f"Exception in generate_all_file_links: {e}")
        bot.send_message(user_id, "An error occurred while generating all file links.")

def log_file_link(user_id, username, file_name):
    """
    Logs the generation of a file link with timestamp in IST.
    """
    try:
        ist = pytz.timezone('Asia/Kolkata')
        current_time_ist = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')

        log_message = f"User: {username} (ID: {user_id}) generated link for file: {file_name} at {current_time_ist} IST\n"
        with open("link_generation_logs.txt", "a") as log_file:
            log_file.write(log_message)
        logging.info(f"Logged file link generation for user {user_id}, file '{file_name}'.")
    except Exception as e:
        logging.error(f"Exception in log_file_link: {e}")

# ----------------------------#
#        Bot Commands         #
# ----------------------------#

@bot.message_handler(commands=['myfiles'])
def list_files_command(message):
    """
    Handles the /myfiles command to list files in "USER MARIO" folder.
    """
    list_files(message, folder_id=None, page=0, edit=False)

@bot.message_handler(commands=['logs'])
@restricted
def send_logs(message):
    """
    Handles the /logs command to send the 'bot_debug.log' file directly via Telegram.
    """
    user_id = message.chat.id
    try:
        with open("link_generation_logs.txt", "rb") as log_file:
            bot.send_document(user_id, log_file, caption="Here are the latest logs.")
            logging.info(f"Sent 'link_generation_logs.txt' to user {user_id}.")
    except FileNotFoundError:
        bot.send_message(user_id, "Log file not found.")
        logging.error("Log file 'bot_debug.log' not found.")
    except Exception as e:
        bot.send_message(user_id, "An error occurred while sending the logs.")
        logging.error(f"Exception in send_logs: {e}")

@bot.message_handler(commands=['debugg'])
@restricted
def send_debugg(message):
    """
    Handles the /debugg command to send the 'debug.log' file directly via Telegram.
    """
    user_id = message.chat.id
    try:
        with open("bot_debug.log", "rb") as debug_file:
            bot.send_document(user_id, debug_file, caption="Here is the debug file.")
            logging.info(f"Sent 'bot_debug.log' to user {user_id}.")
    except FileNotFoundError:
        bot.send_message(user_id, "Debug file not found.")
        logging.error("Debug file 'debug.log' not found.")
    except Exception as e:
        bot.send_message(user_id, "An error occurred while sending the debug file.")
        logging.error(f"Exception in send_debugg: {e}")

@bot.message_handler(commands=['telegraph_logs'])
@restricted
def send_logs_via_telegraph(message):
    """
    Handles the /telegraph_logs command to upload 'bot_debug.log' to Telegraph and send the link.
    """
    user_id = message.chat.id
    try:
        with open("link_generation_logs.txt", "r") as log_file:
            log_content = log_file.read()

        # Limit content to Telegraph's size limits (64 KB)
        if len(log_content) > 60000:
            log_content = log_content[:60000] + "\n... (truncated)"

        # Upload to Telegraph
        response = telegraph.create_page(
            title='Bot Logs',
            html_content=f"<pre>{log_content}</pre>"
        )

        # Send the Telegraph link to the user
        bot.send_message(user_id, f"Here are the latest logs: https://telegra.ph/{response['path']}")
        logging.info(f"Uploaded logs to Telegraph and sent link to user {user_id}.")
    except FileNotFoundError:
        bot.send_message(user_id, "Log file not found.")
        logging.error("Log file 'bot_debug.log' not found.")
    except Exception as e:
        bot.send_message(user_id, "An error occurred while uploading the logs.")
        logging.error(f"Exception in send_logs_via_telegraph: {e}")

@bot.message_handler(commands=['telegraph_debugg'])
@restricted
def send_debugg_via_telegraph(message):
    """
    Handles the /telegraph_debugg command to upload 'debug.log' to Telegraph and send the link.
    """
    user_id = message.chat.id
    try:
        with open("bot_debug.log", "r") as debug_file:
            debug_content = debug_file.read()

        # Limit content to Telegraph's size limits (64 KB)
        if len(debug_content) > 60000:
            debug_content = debug_content[:60000] + "\n... (truncated)"

        # Upload to Telegraph
        response = telegraph.create_page(
            title='Bot Debug Logs',
            html_content=f"<pre>{debug_content}</pre>"
        )

        # Send the Telegraph link to the user
        bot.send_message(user_id, f"Here are the latest debug logs: https://telegra.ph/{response['path']}")
        logging.info(f"Uploaded debug logs to Telegraph and sent link to user {user_id}.")
    except FileNotFoundError:
        bot.send_message(user_id, "Debug file not found.")
        logging.error("Debug file 'debug.log' not found.")
    except Exception as e:
        bot.send_message(user_id, "An error occurred while uploading the debug logs.")
        logging.error(f"Exception in send_debugg_via_telegraph: {e}")

# ----------------------------#
#       Core Functionality    #
# ----------------------------#

def list_files(message, folder_id=None, page=0, edit=False):
    """
    Lists files in the specified folder. If no folder_id is provided, navigates to "USER MARIO" folder.
    """
    user_id = message.chat.id
    try:
        token_data = load_token_from_file()

        if not token_data or 'access_token' not in token_data:
            bot.send_message(user_id, "You need to authenticate first. Initiating device login...")
            authenticate_user(user_id)
            return

        access_token = token_data['access_token']

        if not folder_id:
            root_files = get_files(access_token)
            if not root_files:
                bot.send_message(user_id, "Failed to retrieve root files.")
                return

            folder_69_id = find_folder_id_by_name(root_files, "69")
            if not folder_69_id:
                bot.send_message(user_id, "'69' folder not found.")
                return

            files_in_69 = get_files(access_token, folder_69_id)
            if not files_in_69:
                bot.send_message(user_id, "Failed to retrieve files in '69' folder.")
                return

            user_mario_folder_id = find_folder_id_by_name(files_in_69, "USER MARIO")
            if not user_mario_folder_id:
                bot.send_message(user_id, "'USER MARIO' folder not found.")
                return

            folder_id = user_mario_folder_id
            user_sessions[user_id] = folder_id  # Update current folder
            logging.info(f"User {user_id} is now in 'USER MARIO' folder.")
        else:
            user_sessions[user_id] = folder_id  # Update current folder
            logging.info(f"User {user_id} navigated to folder ID: {folder_id}")

        files = get_files(access_token, folder_id)

        if files is not None:
            markup = generate_navigation_buttons(folder_id, page, access_token)

            if markup is None:
                bot.send_message(user_id, "No files to display.")
                return

            if edit:
                try:
                    bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id,
                                          text="Your files are listed below:", reply_markup=markup)
                except Exception as e:
                    logging.error(f"Exception in editing message: {e}")
            else:
                bot.send_message(user_id, "Your files are listed below:", reply_markup=markup)
        else:
            bot.send_message(user_id, "Failed to retrieve files or folder is empty.")
    except Exception as e:
        logging.error(f"Exception in list_files for user {user_id}: {e}")
        bot.send_message(user_id, "An error occurred while listing your files.")

# ----------------------------#
#     Callback Query Handler  #
# ----------------------------#

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.message.chat.id
    message_id = call.message.message_id
    try:
        action, item_id, page = parse_callback_data(call.data)

        token_data = load_token_from_file()

        if not token_data or 'access_token' not in token_data:
            bot.send_message(user_id, "Authentication is required. Please login using /myfiles.")
            return

        access_token = token_data['access_token']

        if action == "folder":
            bot.answer_callback_query(call.id, "Fetching folder contents...")
            list_files(call.message, folder_id=item_id, page=0, edit=True)
        elif action == "file":
            bot.answer_callback_query(call.id, "Generating file link...")
            username = call.from_user.username or "unknown_user"
            generate_file_link(item_id, access_token, user_id, username)
        elif action == "navigate":
            bot.answer_callback_query(call.id, "Navigating...")
            markup = generate_navigation_buttons(item_id, int(page), access_token)
            bot.edit_message_reply_markup(chat_id=user_id, message_id=message_id, reply_markup=markup)
        elif action == "getalllinks":
            bot.answer_callback_query(call.id, "Generating all file links...")
            username = call.from_user.username or "unknown_user"
            generate_all_file_links(item_id, access_token, user_id, username)
        elif action == "home":
            bot.answer_callback_query(call.id, "Processing Home action...")
            handle_home_action(call, user_id, access_token)
        else:
            bot.answer_callback_query(call.id, "Unknown action.")
            logging.warning(f"Unknown action received: {action}")
    except Exception as e:
        logging.error(f"Exception in callback_query for user {user_id}: {e}")
        bot.send_message(user_id, "An unexpected error occurred while processing your request.")

def handle_home_action(call, user_id, access_token):
    try:
        # Retrieve the user's current folder
        current_folder_id = user_sessions.get(user_id)

        # Function to get USER MARIO folder ID
        def get_user_mario_folder_id(access_token):
            root_files = get_files(access_token)
            if not root_files:
                return None

            folder_69_id = find_folder_id_by_name(root_files, "69")
            if not folder_69_id:
                return None

            files_in_69 = get_files(access_token, folder_69_id)
            if not files_in_69:
                return None

            user_mario_folder_id = find_folder_id_by_name(files_in_69, "USER MARIO")
            return user_mario_folder_id

        user_mario_folder_id = get_user_mario_folder_id(access_token)

        if not user_mario_folder_id:
            bot.send_message(user_id, "USER MARIO folder not found.")
            logging.warning(f"USER MARIO folder not found for user {user_id}.")
            return

        if current_folder_id == user_mario_folder_id:
            # User is already in USER MARIO folder
            bot.send_message(user_id, "You are already in USER MARIO folder.")
            logging.info(f"User {user_id} clicked 'Home' while already in 'USER MARIO' folder.")
        else:
            # Navigate to USER MARIO folder
            list_files(call.message, folder_id=None, edit=True)
            logging.info(f"User {user_id} navigated back to 'USER MARIO' folder.")
    except Exception as e:
        logging.error(f"Exception in handle_home_action for user {user_id}: {e}")
        bot.send_message(user_id, "An error occurred while processing the Home action.")

# ----------------------------------#
#       Debug and Log Commands      #
# ----------------------------------#

# Restrict access to certain commands
def restricted(func):
    @wraps(func)
    def wrapped(message, *args, **kwargs):
        admin_id = 1585904762  # Replace with your actual Telegram user ID
        if message.from_user.id != admin_id:
            bot.send_message(message.chat.id, "Unauthorized access!")
            return
        return func(message, *args, **kwargs)
    return wrapped

# /logs command to retrieve bot logs
@bot.message_handler(commands=['logs'])
@restricted
def send_logs(message):
    try:
        with open("link_generation_logs.txt", "r") as log_file:
            bot.send_document(message.chat.id, log_file)
    except Exception as e:
        bot.send_message(message.chat.id, "Failed to retrieve logs.")
        logging.error(f"Error sending logs: {e}")

# /debugg command to download logs as a file
@bot.message_handler(commands=['debugg'])
@restricted
def send_debug_file(message):
    try:
        bot.send_document(message.chat.id, open("bot_debug.log", "rb"))
    except Exception as e:
        bot.send_message(message.chat.id, "Failed to send debug file.")
        logging.error(f"Error sending debug file: {e}")

# ----------------------------------#
#       Start the bot               #
# ----------------------------------#

if __name__ == "__main__":
    try:
        bot.infinity_polling()
    except Exception as e:
        logging.critical(f"Bot polling failed: {e}")
