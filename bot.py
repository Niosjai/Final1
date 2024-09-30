import os
import requests
import json
import telebot
from msal import PublicClientApplication
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import pyshorteners
from dotenv import load_dotenv
import pytz
import logging  # Added for logging

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

# Set up Telegram bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# MSAL public client for device code flow
msal_app = PublicClientApplication(
    GRAPH_CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{GRAPH_TENANT_ID}"
)

# In-memory user sessions
user_sessions = {}

# Save and load token functions
def save_token_to_file(token_data):
    token_data['expires_at'] = (datetime.now() + timedelta(seconds=token_data['expires_in'])).timestamp()
    try:
        with open(TOKEN_FILE, "w") as token_file:
            json.dump(token_data, token_file)
        logging.info("Token saved successfully.")
    except Exception as e:
        logging.error(f"Error saving token to file: {e}")

def load_token_from_file():
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

# Authenticate the user with Microsoft Graph using device code flow
def authenticate_user(user_id):
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

# Fetch files from OneDrive
def get_files(access_token, folder_id=None):
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

# Find a folder by name in a list of files
def find_folder_id_by_name(files, folder_name):
    for file in files:
        if file.get('folder', None) and file['name'].lower() == folder_name.lower():
            logging.info(f"Found folder '{folder_name}' with ID: {file['id']}")
            return file['id']
    logging.warning(f"Folder '{folder_name}' not found.")
    return None

# List files in the "USER MARIO" folder
@bot.message_handler(commands=['myfiles'])
def list_files_command(message):
    list_files(message, folder_id=None, page=0, edit=False)

def list_files(message, folder_id=None, page=0, edit=False):
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

            if edit:
                bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id,
                                      text="Your files are listed below:", reply_markup=markup)
            else:
                bot.send_message(user_id, "Your files are listed below:", reply_markup=markup)
        else:
            bot.send_message(user_id, "Failed to retrieve files or folder is empty.")
    except Exception as e:
        logging.error(f"Exception in list_files for user {user_id}: {e}")
        bot.send_message(user_id, "An unexpected error occurred while listing files.")

# Callback handler for inline button presses
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

# Generate shareable links for all files in a folder
def generate_all_file_links(folder_id, access_token, user_id, username):
    try:
        files = get_files(access_token, folder_id)
        if files:
            links = []
            for file in files:
                if not file.get('folder', None):  # Skip folders, only get files
                    link = create_share_link(file['id'], access_token, file['name'])
                    if link:
                        links.append(f"{file['name']}: {link}")
                        log_file_link(user_id, username, file['name'])  # Log the file link generation

            if links:
                # Telegram has a limit of 4096 characters per message
                message_chunks = split_message("\n".join(links), 4000)
                for chunk in message_chunks:
                    bot.send_message(user_id, chunk)
                logging.info(f"Generated all file links for user {user_id}.")
            else:
                bot.send_message(user_id, "No links found or failed to generate links.")
                logging.warning(f"No links generated for user {user_id}.")
        else:
            bot.send_message(user_id, "No files found in the folder.")
            logging.warning(f"No files found in folder ID {folder_id} for user {user_id}.")
    except Exception as e:
        logging.error(f"Exception in generate_all_file_links for user {user_id}: {e}")
        bot.send_message(user_id, "An error occurred while generating all file links.")

# Create a shareable link for a specific file
def create_share_link(file_id, access_token, file_name):
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

        # If no suitable link found, create one
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

        logging.warning(f"Failed to create share link for file ID {file_id}.")
    except Exception as e:
        logging.error(f"Exception in create_share_link for file ID {file_id}: {e}")
    return None

# Shorten a URL using TinyURL
def shorten_url(url):
    try:
        s = pyshorteners.Shortener()
        short_url = s.tinyurl.short(url)
        logging.info(f"Shortened URL: {url} to {short_url}")
        return short_url
    except Exception as e:
        logging.error(f"Exception in shorten_url: {e}")
        return url  # Return original URL if shortening fails

# Generate a shareable link for a specific file
def generate_file_link(file_id, access_token, user_id, username):
    """Generate a shareable link for a specific file."""
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
            link = create_share_link(file_id, access_token, file_name)

            if link:
                bot.send_message(user_id, f"File link for {file_name}: {link}")
                log_file_link(user_id, username, file_name)  # Log the file link generation
                logging.info(f"Generated link for file '{file_name}' for user {user_id}.")
            else:
                bot.send_message(user_id, "Failed to generate file link.")
                logging.warning(f"Failed to generate link for file '{file_name}' for user {user_id}.")
        else:
            bot.send_message(user_id, "Error retrieving file details.")
            logging.error(f"Error retrieving file details for file ID {file_id}: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Exception in generate_file_link for user {user_id}: {e}")
        bot.send_message(user_id, "An error occurred while generating the file link.")

# Generate navigation buttons for pagination and actions
def generate_navigation_buttons(folder_id, page, access_token):
    try:
        files = get_files(access_token, folder_id)
        markup = InlineKeyboardMarkup()

        if not files:
            logging.warning(f"No files to generate buttons for folder ID {folder_id}.")
            return markup  # Return empty markup

        page_size = 10
        start = page * page_size
        end = start + page_size

        for file in files[start:end]:
            if file.get('folder', None):
                markup.add(InlineKeyboardButton(text=f"📁 {file['name']}", callback_data=f"folder:{file['id']}:0"))
            else:
                markup.add(InlineKeyboardButton(text=f"🗃️ {file['name']}", callback_data=f"file:{file['id']}:0"))

        # Create navigation buttons
        navigation_buttons = []
        if page > 0:
            navigation_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"navigate:{folder_id}:{page-1}"))
        if end < len(files):
            navigation_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"navigate:{folder_id}:{page+1}"))

        # Create home and all links buttons
        getalllinks_button = InlineKeyboardButton("Generate All Links 🔗", callback_data=f"getalllinks:{folder_id}:0")
        home_button = InlineKeyboardButton("🏠 Home", callback_data=f"home:{folder_id}:0")
        # Add navigation, home, and all links buttons in rows
        if navigation_buttons:
            markup.row(*navigation_buttons)
        markup.row(getalllinks_button,home_button)

        logging.info(f"Generated navigation buttons for folder ID {folder_id}, page {page}.")
        return markup
    except Exception as e:
        logging.error(f"Exception in generate_navigation_buttons for folder ID {folder_id}: {e}")
        return InlineKeyboardMarkup()  # Return empty markup on error

# Parse callback data for actions
def parse_callback_data(callback_data):
    """Parse callback data into action, item_id, and page."""
    parts = callback_data.split(":")
    if len(parts) == 3:
        action, item_id, page = parts
        try:
            page = int(page)
        except ValueError:
            page = 0
        return action, item_id, page
    else:
        logging.warning(f"Invalid callback data format: {callback_data}")
        return "unknown", "unknown", 0

# Log the generated file link with Indian Standard Time
def log_file_link(user_id, username, file_name):
    try:
        ist = pytz.timezone('Asia/Kolkata')
        current_time_ist = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')

        log_message = f"User: {username} (ID: {user_id}) generated link for file: {file_name} at {current_time_ist} IST\n"
        with open("link_generation_logs.txt", "a") as log_file:
            log_file.write(log_message)
        logging.info(f"Logged file link generation for user {user_id}, file '{file_name}'.")
    except Exception as e:
        logging.error(f"Exception in log_file_link for user {user_id}: {e}")

# Split a long message into chunks to comply with Telegram's message size limit
def split_message(message, max_length):
    lines = message.split('\n')
    chunks = []
    current_chunk = ""
    for line in lines:
        if len(current_chunk) + len(line) + 1 > max_length:
            chunks.append(current_chunk)
            current_chunk = line
        else:
            if current_chunk:
                current_chunk += "\n" + line
            else:
                current_chunk = line
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

# Start the bot
if __name__ == "__main__":
    try:
        logging.info("Starting the Telegram bot.")
        bot.polling(none_stop=True)
    except Exception as e:
        logging.critical(f"Bot stopped unexpectedly: {e}")